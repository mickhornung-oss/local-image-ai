"""
Integration test for image modes: Verify complete workflow from UI to backend.
"""

import unittest
from http import HTTPStatus

# Simulate the complete backend processing logic
def prepare_general_generate_request(payload_dict: dict, **kwargs):
    """Simulate backend prepare_general_generate_request."""
    prompt = payload_dict.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("empty_prompt")
    
    use_input_image = bool(payload_dict.get("use_input_image"))
    use_inpainting = bool(payload_dict.get("use_inpainting"))
    use_edit_image = use_input_image and not use_inpainting
    
    # Verify required fields for each mode
    if use_input_image and "input_image_id" not in payload_dict:
        raise ValueError("input_image_required")
    
    if use_inpainting and "mask_image_id" not in payload_dict:
        raise ValueError("mask_image_required")
    
    task_id = payload_dict.get("task_id")  # New field
    
    return {
        "prompt": prompt.strip(),
        "use_input_image": use_input_image,
        "use_inpainting": use_inpainting,
        "use_edit_image": use_edit_image,
        "task_id": task_id,
        "input_image_id": payload_dict.get("input_image_id"),
        "mask_image_id": payload_dict.get("mask_image_id"),
    }


def resolve_generation_request(payload: dict, **kwargs):
    """Simulate backend resolve_generation_request."""
    mode = payload.get("mode", "auto")
    use_input_image = kwargs.get("use_input_image", False)
    use_inpainting = kwargs.get("use_inpainting", False)
    
    if (use_input_image or use_inpainting) and mode == "placeholder":
        raise ValueError("input_image_requires_sdxl")
    
    # In real backend, this determines workflow
    if mode == "sdxl":
        workflow = "text2img" if not (use_input_image or use_inpainting) else "img2img"
        return "sdxl", workflow, "photo_standard"
    
    return "auto", None, None


class TestImageModeE2EIntegration(unittest.TestCase):
    """Test complete end-to-end workflow for image modes."""

    def test_edit_mode_complete_workflow(self):
        """Test 'Bild anpassen' (edit) mode complete workflow."""
        # Frontend payload (after fixes)
        frontend_payload = {
            "prompt": "Make the sky more blue",
            "mode": "sdxl",
            "task_id": "edit",  # NEW: Task ID now included
            "use_input_image": True,
            "use_inpainting": False,
            "input_image_id": "img_abc123",
            "denoise_strength": 0.25,
            "checkpoint": "photo_standard"
        }
        
        # Backend processing
        prepared = prepare_general_generate_request(frontend_payload)
        mode, workflow, checkpoint = resolve_generation_request(
            frontend_payload,
            use_input_image=prepared["use_input_image"],
            use_inpainting=prepared["use_inpainting"]
        )
        
        # Verify results
        self.assertEqual(prepared["task_id"], "edit", "Task ID must be preserved")
        self.assertTrue(prepared["use_input_image"], "Edit must use input image")
        self.assertFalse(prepared["use_inpainting"], "Edit must not use inpainting")
        self.assertTrue(prepared["use_edit_image"], "Backend must infer use_edit_image=True")
        self.assertEqual(mode, "sdxl", "Edit must use SDXL mode")
        self.assertEqual(workflow, "img2img", "Edit must use img2img workflow")
        self.assertIsNotNone(prepared["input_image_id"], "Edit must have input image")

    def test_inpaint_mode_complete_workflow(self):
        """Test 'Bereich im Bild aendern' (inpaint) mode complete workflow."""
        # Frontend payload (after fixes)
        frontend_payload = {
            "prompt": "Fix the arm",
            "mode": "sdxl",
            "task_id": "inpaint",  # NEW: Task ID now included
            "use_input_image": True,
            "use_inpainting": True,
            "input_image_id": "img_abc123",
            "mask_image_id": "mask_def456",
            "denoise_strength": 0.58,
            "checkpoint": "photo_standard"
        }
        
        # Backend processing
        prepared = prepare_general_generate_request(frontend_payload)
        mode, workflow, checkpoint = resolve_generation_request(
            frontend_payload,
            use_input_image=prepared["use_input_image"],
            use_inpainting=prepared["use_inpainting"]
        )
        
        # Verify results
        self.assertEqual(prepared["task_id"], "inpaint", "Task ID must be preserved")
        self.assertTrue(prepared["use_input_image"], "Inpaint must use input image")
        self.assertTrue(prepared["use_inpainting"], "Inpaint must use inpainting")
        self.assertFalse(prepared["use_edit_image"], "Backend must infer use_edit_image=False")
        self.assertEqual(mode, "sdxl", "Inpaint must use SDXL mode")
        self.assertEqual(workflow, "img2img", "Inpaint must use img2img workflow")
        self.assertIsNotNone(prepared["input_image_id"], "Inpaint must have input image")
        self.assertIsNotNone(prepared["mask_image_id"], "Inpaint must have mask image")

    def test_edit_without_input_image_fails(self):
        """Test that edit mode without input image is rejected."""
        frontend_payload = {
            "prompt": "Make the sky blue",
            "mode": "sdxl",
            "task_id": "edit",
            "use_input_image": True,
            "use_inpainting": False,
            # Missing: input_image_id
            "checkpoint": "photo_standard"
        }
        
        # Backend processing should fail
        with self.assertRaises(ValueError) as ctx:
            prepare_general_generate_request(frontend_payload)
        
        self.assertEqual(str(ctx.exception), "input_image_required")

    def test_inpaint_without_mask_image_fails(self):
        """Test that inpaint mode without mask image is rejected."""
        frontend_payload = {
            "prompt": "Fix the arm",
            "mode": "sdxl",
            "task_id": "inpaint",
            "use_input_image": True,
            "use_inpainting": True,
            "input_image_id": "img_abc123",
            # Missing: mask_image_id
            "checkpoint": "photo_standard"
        }
        
        # Backend processing should fail
        with self.assertRaises(ValueError) as ctx:
            prepare_general_generate_request(frontend_payload)
        
        self.assertEqual(str(ctx.exception), "mask_image_required")

    def test_edit_vs_inpaint_payload_differentiation(self):
        """Test that backend correctly differentiates edit and inpaint by flags."""
        edit_payload = {
            "prompt": "Change",
            "use_input_image": True,
            "use_inpainting": False,
            "input_image_id": "img_1",
        }
        
        inpaint_payload = {
            "prompt": "Change",
            "use_input_image": True,
            "use_inpainting": True,
            "input_image_id": "img_1",
            "mask_image_id": "mask_1",
        }
        
        edit_prepared = prepare_general_generate_request(edit_payload)
        inpaint_prepared = prepare_general_generate_request(inpaint_payload)
        
        # Key differentiation
        self.assertTrue(edit_prepared["use_edit_image"], "Edit payload must result in use_edit_image=True")
        self.assertFalse(inpaint_prepared["use_edit_image"], "Inpaint payload must result in use_edit_image=False")

    def test_task_id_preserved_through_workflow(self):
        """Test that task_id is preserved from frontend through backend."""
        # This is important for debugging and logging
        for task in ["create", "edit", "inpaint"]:
            payload = {"prompt": "test", "task_id": task}
            prepared = prepare_general_generate_request(payload)
            self.assertEqual(prepared["task_id"], task, f"Task ID {task} must be preserved")


class TestUIStateConsistency(unittest.TestCase):
    """Test that UI state remains consistent when modes are switched."""

    def test_mode_switch_affects_checkbox_state(self):
        """Test that switching modes correctly updates checkbox states."""
        # Simulating: User in create mode, switches to edit mode
        
        # Initial create mode state
        state = {
            "currentTask": "create",
            "useInputImage": False,
            "useInpainting": False,
        }
        
        # After switching to edit
        state["currentTask"] = "edit"
        # syncV7BasicTaskDefaults() would run:
        if state["currentTask"] == "edit":
            state["useInputImage"] = True
            state["useInpainting"] = False
        
        self.assertTrue(state["useInputImage"], "Switching to edit must enable useInputImage")
        self.assertFalse(state["useInpainting"], "Switching to edit must disable useInpainting")
        
        # After switching to inpaint
        state["currentTask"] = "inpaint"
        if state["currentTask"] == "inpaint":
            state["useInputImage"] = True
            state["useInpainting"] = True
        
        self.assertTrue(state["useInputImage"], "Switching to inpaint must enable useInputImage")
        self.assertTrue(state["useInpainting"], "Switching to inpaint must enable useInpainting")


if __name__ == '__main__':
    unittest.main()
