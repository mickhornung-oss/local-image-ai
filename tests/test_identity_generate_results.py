from __future__ import annotations

import unittest
from http import HTTPStatus

import python.identity_generate_results as identity_generate_results


class IdentityGenerateResultsTests(unittest.TestCase):
    def test_finalize_outcome_maps_success_via_finalize_callback(self) -> None:
        calls: list[dict] = []

        def finalize_result(result: dict, request_id: str, **kwargs):
            calls.append({"result": result, "request_id": request_id, "kwargs": kwargs})
            return HTTPStatus.OK, {"status": "ok", "request_id": request_id}

        status, payload = identity_generate_results.finalize_identity_generate_outcome(
            {"status": "ok", "checkpoint": "resolved.safetensors"},
            request_id="req-000001",
            mode="identity_reference",
            prompt="Prompt",
            checkpoint="fallback.safetensors",
            default_failed_blocker="identity_reference_failed",
            status_code_resolver=lambda **kwargs: HTTPStatus.BAD_REQUEST,
            finalize_result=finalize_result,
            error_response_builder=lambda **kwargs: {"status": "error"},
            extra_metadata={"experimental": True},
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload, {"status": "ok", "request_id": "req-000001"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["kwargs"]["checkpoint"], "resolved.safetensors")
        self.assertEqual(calls[0]["kwargs"]["extra_metadata"], {"experimental": True})

    def test_finalize_outcome_maps_render_error_to_error_response(self) -> None:
        status, payload = identity_generate_results.finalize_identity_generate_outcome(
            {
                "status": "error",
                "error_type": "api_error",
                "blocker": "identity_transfer_unavailable",
                "prompt_id": "p-1",
            },
            request_id="req-000002",
            mode="identity_transfer",
            prompt="Prompt",
            checkpoint=None,
            default_failed_blocker="identity_transfer_failed",
            status_code_resolver=lambda **kwargs: HTTPStatus.SERVICE_UNAVAILABLE,
            finalize_result=lambda *args, **kwargs: (HTTPStatus.OK, {"status": "ok"}),
            error_response_builder=lambda **kwargs: kwargs,
        )

        self.assertEqual(status, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(payload["mode"], "identity_transfer")
        self.assertEqual(payload["error_type"], "api_error")
        self.assertEqual(payload["blocker"], "identity_transfer_unavailable")
        self.assertEqual(payload["prompt_id"], "p-1")

    def test_finalize_outcome_uses_default_failed_blocker_when_missing(self) -> None:
        status, payload = identity_generate_results.finalize_identity_generate_outcome(
            {"status": "error"},
            request_id="req-000003",
            mode="identity_multi_reference",
            prompt="Prompt",
            checkpoint=None,
            default_failed_blocker="identity_multi_reference_failed",
            status_code_resolver=lambda **kwargs: HTTPStatus.INTERNAL_SERVER_ERROR,
            finalize_result=lambda *args, **kwargs: (HTTPStatus.OK, {"status": "ok"}),
            error_response_builder=lambda **kwargs: kwargs,
        )

        self.assertEqual(status, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertEqual(payload["blocker"], "identity_multi_reference_failed")
        self.assertEqual(payload["error_type"], "api_error")

    def test_build_server_error_returns_internal_error_response(self) -> None:
        (
            status,
            payload,
        ) = identity_generate_results.build_identity_generate_server_error(
            mode="identity_research",
            request_id="req-000004",
            error_response_builder=lambda **kwargs: kwargs,
        )

        self.assertEqual(status, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertEqual(payload["mode"], "identity_research")
        self.assertEqual(payload["error_type"], "api_error")
        self.assertEqual(payload["blocker"], "server_error")


if __name__ == "__main__":
    unittest.main()
