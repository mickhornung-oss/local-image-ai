from __future__ import annotations

import sys
import types
import unittest
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "python").resolve()))

if "requests" not in sys.modules:
    fake_requests = types.ModuleType("requests")

    class _RequestException(Exception):
        pass

    class _ConnectionError(_RequestException):
        pass

    class _Timeout(_RequestException):
        pass

    def _request(*args, **kwargs):
        raise AssertionError(
            "requests.request should not be used in app_server integration tests"
        )

    fake_requests.RequestException = _RequestException
    fake_requests.ConnectionError = _ConnectionError
    fake_requests.Timeout = _Timeout
    fake_requests.request = _request
    sys.modules["requests"] = fake_requests

import python.app_server as app_server


class DummyServer:
    def __init__(self) -> None:
        self._request_id = "req-000001"

    def next_request_id(self) -> str:
        return self._request_id

    def collect_system_state(self) -> dict:
        return {"status": "ok", "comfyui_reachable": True}

    def try_begin_render(self, request_id: str) -> bool:
        return True

    def finish_render(self) -> None:
        return


class DummyHandler:
    def __init__(
        self,
        *,
        path: str = "/",
        json_body=None,
        body: bytes = b"",
        headers: dict | None = None,
        server=None,
    ) -> None:
        self.path = path
        self._json_body = json_body
        self._body = body
        self.headers = headers or {}
        self.server = server or DummyServer()
        self.sent: list[tuple[HTTPStatus, dict]] = []

    def read_json_body(self):
        return self._json_body

    def read_body_bytes(self) -> bytes:
        return self._body

    def send_json(self, status_code: HTTPStatus, payload: dict) -> None:
        self.sent.append((status_code, payload))

    def serve_index(self) -> None:
        raise AssertionError("serve_index should not be called in this test")


class AppServerIntegrationTests(unittest.TestCase):
    def test_resolve_default_text_model_profile_id_stays_on_standard(self) -> None:
        with patch.object(
            app_server,
            "build_text_model_profiles_state",
            return_value={
                "current_profile_id": app_server.TEXT_MODEL_PROFILE_STRONG_WRITING
            },
        ):
            self.assertEqual(
                app_server.resolve_default_text_model_profile_id(),
                app_server.TEXT_MODEL_PROFILE_STANDARD,
            )

    def test_do_get_health_returns_system_state(self) -> None:
        handler = DummyHandler(path="/health", server=DummyServer())

        app_server.AppRequestHandler.do_GET(handler)

        self.assertEqual(1, len(handler.sent))
        status, payload = handler.sent[0]
        self.assertEqual(HTTPStatus.OK, status)
        self.assertTrue(payload["comfyui_reachable"])

    def test_handle_text_chat_create_returns_overview_payload(self) -> None:
        handler = DummyHandler(json_body={"title": "Idee"})

        with patch.object(
            app_server.chat_requests,
            "coerce_optional_text_chat_payload",
            return_value=({"title": "Idee"}, None),
        ), patch.object(
            app_server.chat_requests,
            "normalize_create_text_chat_title",
            return_value=("Idee", None),
        ), patch.object(
            app_server,
            "create_text_chat_in_first_empty_slot",
            return_value={"slot_index": 0},
        ), patch.object(
            app_server,
            "build_text_chat_overview_payload",
            return_value={"status": "ok", "slots": []},
        ):
            app_server.AppRequestHandler.handle_text_chat_create(handler)

        self.assertEqual([(HTTPStatus.OK, {"status": "ok", "slots": []})], handler.sent)

    def test_handle_input_image_upload_maps_success_response(self) -> None:
        handler = DummyHandler(
            body=b"payload",
            headers={"Content-Type": "multipart/form-data; boundary=abc"},
        )

        with patch.object(
            app_server.image_input_validation, "validate_multipart_content_type"
        ), patch.object(
            app_server,
            "parse_multipart_image",
            return_value=("input.png", b"payload", "file"),
        ), patch.object(
            app_server,
            "store_uploaded_image",
            return_value={"image_id": "input-1", "source_type": "file"},
        ), patch.object(
            app_server,
            "build_upload_success_response",
            return_value={"status": "ok", "ok": True, "image_id": "input-1"},
        ):
            app_server.AppRequestHandler.handle_input_image_upload(handler)

        self.assertEqual(
            [(HTTPStatus.OK, {"status": "ok", "ok": True, "image_id": "input-1"})],
            handler.sent,
        )

    def test_handle_result_export_maps_store_error(self) -> None:
        handler = DummyHandler(json_body={"result_id": "result-1"})

        with patch.object(
            app_server,
            "create_result_export",
            side_effect=app_server.ResultStoreError(
                status_code=HTTPStatus.NOT_FOUND,
                error_type="invalid_request",
                blocker="result_not_found",
                message="Result could not be found.",
            ),
        ):
            app_server.AppRequestHandler.handle_result_export(handler)

        self.assertEqual(1, len(handler.sent))
        status, payload = handler.sent[0]
        self.assertEqual(HTTPStatus.NOT_FOUND, status)
        self.assertEqual("result_not_found", payload["blocker"])

    def test_handle_result_delete_returns_success_payload(self) -> None:
        handler = DummyHandler(json_body={"result_id": "result-1"})

        with patch.object(
            app_server,
            "delete_stored_result",
            return_value={"result_id": "result-1", "deleted": True},
        ), patch.object(
            app_server.result_output,
            "build_result_delete_success_response",
            return_value={
                "status": "ok",
                "ok": True,
                "result_id": "result-1",
                "deleted": True,
            },
        ):
            app_server.AppRequestHandler.handle_result_delete(handler)

        self.assertEqual(
            [
                (
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "ok": True,
                        "result_id": "result-1",
                        "deleted": True,
                    },
                )
            ],
            handler.sent,
        )

    def test_do_post_generate_routes_through_general_flow_and_endpoint_flow(
        self,
    ) -> None:
        handler = DummyHandler(
            path="/generate", json_body={"prompt": "Prompt"}, server=DummyServer()
        )

        with patch.object(
            app_server.general_generate_flow,
            "prepare_general_generate_request",
            return_value=(
                {
                    "mode": "txt2img",
                    "workflow": "workflow-a",
                    "checkpoint": "model.safetensors",
                    "use_input_image": False,
                    "use_inpainting": False,
                    "use_edit_image": False,
                    "denoise_strength": 0.35,
                    "negative_prompt": None,
                    "input_image_path": None,
                    "mask_image_path": None,
                    "inpaint_tuning": None,
                    "prompt": "Prompt",
                },
                None,
            ),
        ), patch.object(
            app_server.general_generate_flow,
            "build_general_generate_system_failure",
            return_value=None,
        ), patch.object(
            app_server.general_generate_flow,
            "build_general_render_request",
            return_value={
                "prompt_text": "Prompt",
                "render_prompt": "Prompt",
                "cfg_value": 7.0,
                "steps_value": 30,
                "negative_prompt_value": None,
                "grow_mask_by_override": None,
            },
        ), patch.object(
            app_server.generate_endpoint_flow,
            "try_begin_generate_render",
            return_value=None,
        ), patch.object(
            app_server.generate_endpoint_flow,
            "execute_generate_endpoint",
            return_value=(HTTPStatus.OK, {"status": "ok", "result_id": "result-1"}),
        ):
            app_server.AppRequestHandler.do_POST(handler)

        self.assertEqual(
            [(HTTPStatus.OK, {"status": "ok", "result_id": "result-1"})], handler.sent
        )

    def test_do_post_generate_returns_request_error_from_general_flow(self) -> None:
        handler = DummyHandler(path="/generate", json_body=None, server=DummyServer())

        with patch.object(
            app_server.general_generate_flow,
            "prepare_general_generate_request",
            return_value=(
                None,
                {
                    "http_status": HTTPStatus.BAD_REQUEST,
                    "error_type": "invalid_request",
                    "blocker": "invalid_json",
                },
            ),
        ):
            app_server.AppRequestHandler.do_POST(handler)

        self.assertEqual(1, len(handler.sent))
        status, payload = handler.sent[0]
        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        self.assertEqual("invalid_json", payload["blocker"])


if __name__ == "__main__":
    unittest.main()
