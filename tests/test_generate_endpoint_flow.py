from __future__ import annotations

from http import HTTPStatus
import unittest

from python import generate_endpoint_flow


class GenerateEndpointFlowTests(unittest.TestCase):
    def test_build_generate_endpoint_error_uses_failure_payload(self) -> None:
        status, payload = generate_endpoint_flow.build_generate_endpoint_error(
            mode="identity_reference",
            request_id="req-1",
            failure={
                "http_status": HTTPStatus.BAD_REQUEST,
                "error_type": "invalid_request",
                "blocker": "empty_prompt",
            },
            error_response_builder=lambda **kwargs: kwargs,
            fallback_http_status=HTTPStatus.INTERNAL_SERVER_ERROR,
            fallback_error_type="api_error",
            fallback_blocker="server_error",
        )

        self.assertEqual(HTTPStatus.BAD_REQUEST, status)
        self.assertEqual("identity_reference", payload["mode"])
        self.assertEqual("invalid_request", payload["error_type"])
        self.assertEqual("empty_prompt", payload["blocker"])

    def test_try_begin_generate_render_returns_busy_when_locked(self) -> None:
        result = generate_endpoint_flow.try_begin_generate_render(
            request_id="req-2",
            try_begin_render=lambda request_id: False,
            busy_response_builder=lambda **kwargs: {"status": "busy", **kwargs},
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(HTTPStatus.CONFLICT, result[0])
        self.assertEqual("busy", result[1]["status"])
        self.assertEqual("req-2", result[1]["request_id"])

    def test_execute_generate_endpoint_runs_render_finalize_and_finish(self) -> None:
        calls: list[str] = []

        status, payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: calls.append("render") or {"status": "ok"},
            finalize_callable=lambda result: (calls.append("finalize") or HTTPStatus.OK, {"status": result["status"]}),
            server_error_callable=lambda: (calls.append("server_error") or HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error"}),
            finish_render=lambda: calls.append("finish"),
        )

        self.assertEqual(HTTPStatus.OK, status)
        self.assertEqual({"status": "ok"}, payload)
        self.assertEqual(["render", "finalize", "finish"], calls)

    def test_execute_generate_endpoint_routes_exceptions_to_server_error(self) -> None:
        calls: list[str] = []

        def render_callable():
            calls.append("render")
            raise RuntimeError("boom")

        status, payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=render_callable,
            finalize_callable=lambda result: (calls.append("finalize") or HTTPStatus.OK, {"status": "ok"}),
            server_error_callable=lambda: (calls.append("server_error") or HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error"}),
            finish_render=lambda: calls.append("finish"),
        )

        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, status)
        self.assertEqual({"status": "error"}, payload)
        self.assertEqual(["render", "server_error", "finish"], calls)


if __name__ == "__main__":
    unittest.main()
