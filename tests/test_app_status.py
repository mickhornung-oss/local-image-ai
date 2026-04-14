from __future__ import annotations

import unittest

import python.app_status as app_status


class AppStatusTests(unittest.TestCase):
    def test_build_text_service_state_returns_defaults_when_unconfigured(self) -> None:
        state = app_status.build_text_service_state(
            configured=False,
            config=None,
            config_error="text_service_not_configured",
            model_switch_state=None,
            health_payload=None,
            health_error=None,
            info_payload=None,
            info_error=None,
        )

        self.assertFalse(state["text_service_configured"])
        self.assertFalse(state["text_service_reachable"])
        self.assertEqual(state["text_service_error"], "text_service_not_configured")
        self.assertIsNone(state["text_service"]["service_name"])
        self.assertIsNone(state["text_service"]["model_switch"])

    def test_build_text_service_state_uses_config_fallback_when_health_unreachable(self) -> None:
        state = app_status.build_text_service_state(
            configured=True,
            config={
                "service_name": "local-text-service",
                "runner_type": "llama_cpp_server",
                "model_status": "configured",
                "model_configured": True,
            },
            config_error=None,
            model_switch_state={"phase": "loading"},
            health_payload=None,
            health_error="timeout",
            info_payload=None,
            info_error=None,
        )

        self.assertTrue(state["text_service_configured"])
        self.assertFalse(state["text_service_reachable"])
        self.assertEqual(state["text_service_error"], "unreachable")
        self.assertEqual(state["text_service"]["service_name"], "local-text-service")
        self.assertEqual(state["text_service"]["runner_type"], "llama_cpp_server")
        self.assertEqual(state["text_service"]["model_status"], "configured")
        self.assertEqual(state["text_service"]["model_switch"], {"phase": "loading"})

    def test_build_text_service_state_merges_health_and_info_payloads(self) -> None:
        state = app_status.build_text_service_state(
            configured=True,
            config={
                "service_name": "local-text-service",
                "runner_type": "llama_cpp_server",
                "model_status": "configured",
                "model_configured": True,
            },
            config_error=None,
            model_switch_state={"phase": "idle"},
            health_payload={
                "service": "local-text-service",
                "service_mode": "normal",
                "runner_type": "llama_cpp_server",
                "runner_present": True,
                "runner_reachable": True,
                "runner_startable": True,
                "stub_mode": False,
                "inference_available": True,
                "model_status": "ready",
                "model_configured": True,
                "model_present": True,
            },
            health_error=None,
            info_payload={
                "resolved_model_path": "C:/models/example.gguf",
                "model_status": "ready",
                "runner_reachable": True,
            },
            info_error=None,
        )

        self.assertTrue(state["text_service_reachable"])
        self.assertIsNone(state["text_service_error"])
        self.assertEqual(state["text_service"]["service_name"], "local-text-service")
        self.assertEqual(state["text_service"]["model_status"], "ready")
        self.assertEqual(state["text_service"]["resolved_model_path"], "C:/models/example.gguf")
        self.assertEqual(state["text_service"]["current_model_name"], "example.gguf")

    def test_build_text_service_state_marks_info_unavailable_after_valid_health(self) -> None:
        state = app_status.build_text_service_state(
            configured=True,
            config={
                "service_name": "local-text-service",
                "runner_type": "llama_cpp_server",
                "model_status": "configured",
                "model_configured": True,
            },
            config_error=None,
            model_switch_state=None,
            health_payload={"service": "local-text-service"},
            health_error=None,
            info_payload=None,
            info_error="timeout",
        )

        self.assertTrue(state["text_service_reachable"])
        self.assertEqual(state["text_service_error"], "info_unavailable")

    def test_build_system_state_payload_merges_substates_and_defaults(self) -> None:
        payload = app_status.build_system_state_payload(
            runner_payload={"pid": 123},
            runner_status="running",
            runner_error=None,
            comfyui_reachable=True,
            comfyui_error=None,
            output_dir_accessible=True,
            output_dir_error=None,
            input_dir_accessible=True,
            input_dir_error=None,
            reference_dir_accessible=False,
            reference_dir_error="reference_dir_not_accessible",
            mask_dir_accessible=True,
            mask_dir_error=None,
            results_dir_accessible=True,
            results_dir_error=None,
            input_image={"present": True},
            reference_image={"present": False},
            mask_image=None,
            inventory={"sdxl_count": 1, "selected": "model.safetensors"},
            text_service_state={"text_service_reachable": True},
            render_state={"server_render_status": "idle"},
        )

        self.assertEqual(payload["service"], "local-image-app")
        self.assertEqual(payload["runner_status"], "running")
        self.assertTrue(payload["comfyui_reachable"])
        self.assertTrue(payload["sdxl_available"])
        self.assertEqual(payload["selected_checkpoint"], "model.safetensors")
        self.assertEqual(payload["text_service_reachable"], True)
        self.assertEqual(payload["server_render_status"], "idle")


if __name__ == "__main__":
    unittest.main()
