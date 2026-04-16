from __future__ import annotations

import unittest
from http import HTTPStatus

import python.identity_generate_flow as identity_generate_flow


class IdentityGenerateFlowTests(unittest.TestCase):
    def test_coerce_payload_and_prompt_checkpoint_normalization(self) -> None:
        payload, error = identity_generate_flow.coerce_identity_generate_payload(None)
        self.assertIsNone(payload)
        self.assertEqual(error["blocker"], "invalid_json")

        (
            normalized,
            normalize_error,
        ) = identity_generate_flow.normalize_identity_prompt_and_checkpoint(
            {"prompt": "  Test prompt  ", "checkpoint": "  model.safetensors "}
        )
        self.assertIsNone(normalize_error)
        self.assertEqual(normalized["prompt"], "Test prompt")
        self.assertEqual(normalized["checkpoint"], "model.safetensors")

    def test_prepare_identity_reference_request_resolves_reference_and_errors(
        self,
    ) -> None:
        prepared, error = identity_generate_flow.prepare_identity_reference_request(
            {"prompt": "Prompt", "reference_image_id": "ref-1"},
            resolve_reference_image=lambda value: ({"image_id": value}, "C:/ref.png"),
        )
        self.assertIsNone(error)
        self.assertEqual(prepared["prompt"], "Prompt")
        self.assertEqual(prepared["reference_image_payload"], {"image_id": "ref-1"})
        self.assertEqual(prepared["reference_image_path"], "C:/ref.png")

        prepared, error = identity_generate_flow.prepare_identity_reference_request(
            {"prompt": "Prompt", "reference_image_id": "bad"},
            resolve_reference_image=lambda value: (_ for _ in ()).throw(
                ValueError("missing_reference_image")
            ),
        )
        self.assertIsNone(prepared)
        self.assertEqual(error["http_status"], HTTPStatus.BAD_REQUEST)
        self.assertEqual(error["blocker"], "missing_reference_image")

    def test_prepare_identity_research_request_adds_provider_and_negative_prompt(
        self,
    ) -> None:
        prepared, error = identity_generate_flow.prepare_identity_research_request(
            {
                "prompt": "Prompt",
                "provider": "  REPLICATE  ",
                "negative_prompt": " no blur ",
            },
            resolve_reference_image=lambda value: ({"image_id": "ref-1"}, "C:/ref.png"),
            normalize_negative_prompt=lambda value: (str(value).strip(), None),
            default_provider="openai",
        )
        self.assertIsNone(error)
        self.assertEqual(prepared["provider"], "replicate")
        self.assertEqual(prepared["negative_prompt"], "no blur")

    def test_runtime_and_system_preflight_failures_map_consistently(self) -> None:
        runtime_error = identity_generate_flow.build_runtime_preflight_failure(
            {
                "ok": False,
                "error_type": "api_error",
                "blocker": "identity_transfer_unavailable",
            },
            unavailable_blocker="identity_transfer_unavailable",
            status_code_resolver=lambda **kwargs: HTTPStatus.SERVICE_UNAVAILABLE,
        )
        self.assertEqual(runtime_error["http_status"], HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(runtime_error["blocker"], "identity_transfer_unavailable")

        comfy_error = identity_generate_flow.build_system_preflight_failure(
            {"comfyui_reachable": False, "runner_error": None}
        )
        self.assertEqual(comfy_error["http_status"], HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(comfy_error["blocker"], "comfyui_unreachable")

        runner_error = identity_generate_flow.build_system_preflight_failure(
            {"comfyui_reachable": True, "runner_status": "unknown"}
        )
        self.assertEqual(runner_error["blocker"], "runner_state_invalid")

    def test_resolve_multi_reference_adapter_state_prefers_runtime_adapter(
        self,
    ) -> None:
        adapter = identity_generate_flow.resolve_multi_reference_adapter_state(
            {"adapter_state": {"references": [1, 2]}},
            fallback_adapter_state={"references": []},
        )
        self.assertEqual(adapter, {"references": [1, 2]})

        adapter = identity_generate_flow.resolve_multi_reference_adapter_state(
            {"adapter_state": None},
            fallback_adapter_state={"references": []},
        )
        self.assertEqual(adapter, {"references": []})


if __name__ == "__main__":
    unittest.main()
