from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import unittest

from python import general_generate_flow


class GeneralGenerateFlowTests(unittest.TestCase):
    def test_coerce_general_generate_payload_rejects_non_dict(self) -> None:
        payload, error = general_generate_flow.coerce_general_generate_payload("bad")

        self.assertIsNone(payload)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(HTTPStatus.BAD_REQUEST, error["http_status"])
        self.assertEqual("invalid_json", error["blocker"])

    def test_prepare_general_generate_request_builds_normalized_state(self) -> None:
        prepared, error = general_generate_flow.prepare_general_generate_request(
            {
                "prompt": "  Prompt  ",
                "negative_prompt": "  no blur  ",
                "use_input_image": True,
                "use_inpainting": True,
                "denoise_strength": 0.4,
                "mode": "edit",
                "input_image_id": "input-1",
                "mask_image_id": "mask-1",
            },
            normalize_negative_prompt=lambda value: (str(value).strip(), None),
            parse_boolean_flag=lambda value: bool(value),
            normalize_denoise_strength_value=lambda value, **kwargs: float(value),
            resolve_generation_request=lambda payload, **kwargs: ("inpainting", "workflow-a", "model.safetensors"),
            resolve_requested_input_image=lambda value: ({"image_id": value}, Path("input.png")),
            resolve_requested_mask_image=lambda value: ({"image_id": value}, Path("mask.png")),
            resolve_inpainting_tuning=lambda **kwargs: {"denoise_strength": 0.66, "prompt_suffix": "suffix"},
        )

        self.assertIsNone(error)
        assert prepared is not None
        self.assertEqual("Prompt", prepared["prompt"])
        self.assertEqual("no blur", prepared["negative_prompt"])
        self.assertTrue(prepared["use_input_image"])
        self.assertTrue(prepared["use_inpainting"])
        self.assertFalse(prepared["use_edit_image"])
        self.assertEqual(0.66, prepared["denoise_strength"])
        self.assertEqual("inpainting", prepared["mode"])
        self.assertEqual(Path("input.png"), prepared["input_image_path"])
        self.assertEqual(Path("mask.png"), prepared["mask_image_path"])

    def test_prepare_general_generate_request_maps_input_resolution_error(self) -> None:
        prepared, error = general_generate_flow.prepare_general_generate_request(
            {
                "prompt": "Prompt",
                "use_input_image": True,
            },
            normalize_negative_prompt=lambda value: (None, None),
            parse_boolean_flag=lambda value: bool(value),
            normalize_denoise_strength_value=lambda value, **kwargs: 0.35,
            resolve_generation_request=lambda payload, **kwargs: ("img2img", "workflow-a", None),
            resolve_requested_input_image=lambda value: (_ for _ in ()).throw(ValueError("missing_input_image")),
            resolve_requested_mask_image=lambda value: ({}, Path("mask.png")),
            resolve_inpainting_tuning=lambda **kwargs: {},
        )

        self.assertIsNone(prepared)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual("missing_input_image", error["blocker"])

    def test_build_general_generate_system_failure_maps_runner_and_comfy(self) -> None:
        comfy_error = general_generate_flow.build_general_generate_system_failure(
            {"comfyui_reachable": False, "runner_error": None}
        )
        runner_error = general_generate_flow.build_general_generate_system_failure(
            {"comfyui_reachable": True, "runner_status": "unknown"}
        )

        self.assertEqual("comfyui_unreachable", comfy_error["blocker"])
        self.assertEqual("runner_state_invalid", runner_error["blocker"])

    def test_build_general_render_request_uses_tuning_and_prompt_suffix(self) -> None:
        render_request = general_generate_flow.build_general_render_request(
            {
                "prompt": "Prompt",
                "checkpoint": "model.safetensors",
                "negative_prompt": "bad",
                "use_inpainting": True,
                "use_edit_image": False,
                "inpaint_tuning": {
                    "cfg": 5.5,
                    "steps": 28,
                    "negative_suffix": "extra",
                    "prompt_suffix": "suffix",
                    "grow_mask_by": 4,
                },
            },
            resolve_general_generate_tuning=lambda **kwargs: (kwargs["cfg_override"], kwargs["steps_override"], kwargs["inpaint_negative_suffix"]),
            resolve_render_prompt=lambda prompt, **kwargs: f"{prompt}::{kwargs['inpaint_prompt_suffix']}",
            inpaint_locality_negative_suffix="locality",
        )

        self.assertEqual("Prompt", render_request["prompt_text"])
        self.assertEqual("Prompt::suffix", render_request["render_prompt"])
        self.assertEqual(5.5, render_request["cfg_value"])
        self.assertEqual(28, render_request["steps_value"])
        self.assertEqual("locality, extra", render_request["negative_prompt_value"])
        self.assertEqual(4, render_request["grow_mask_by_override"])


if __name__ == "__main__":
    unittest.main()
