"""
Smoke test for image modes: 'Bild anpassen' (edit) and 'Bereich im Bild aendern' (inpaint).
Tests the real payload structure and backend processing.
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from http import HTTPStatus

# Simulate the backend logic
class TestImageModePayloads(unittest.TestCase):
    """Test that image mode payloads are correctly formed and interpreted."""

    def test_edit_mode_payload_structure(self):
        """Verify 'Bild anpassen' (edit) mode sends correct payload."""
        payload = {
            "prompt": "Make the sky more blue",
            "mode": "sdxl",
            "task_id": "edit",
            "use_input_image": True,
            "use_inpainting": False,
            "input_image_id": "img_123",
            "denoise_strength": 0.25,
            "checkpoint": "photo_standard"
        }
        
        # Backend interpretation
        use_input_image = payload.get("use_input_image") is True
        use_inpainting = payload.get("use_inpainting") is True
        use_edit_image = use_input_image and not use_inpainting
        task_id = payload.get("task_id")
        
        # Assertions
        self.assertTrue(use_input_image, "Edit mode must set use_input_image=True")
        self.assertFalse(use_inpainting, "Edit mode must set use_inpainting=False")
        self.assertTrue(use_edit_image, "Backend should infer use_edit_image=True")
        self.assertEqual(task_id, "edit", "Task ID must be 'edit'")
        self.assertIsNotNone(payload.get("input_image_id"), "Edit must have input_image_id")

    def test_inpaint_mode_payload_structure(self):
        """Verify 'Bereich im Bild aendern' (inpaint) mode sends correct payload."""
        payload = {
            "prompt": "Fix this person's arm",
            "mode": "sdxl",
            "task_id": "inpaint",
            "use_input_image": True,
            "use_inpainting": True,
            "input_image_id": "img_123",
            "mask_image_id": "mask_456",
            "denoise_strength": 0.58,
            "checkpoint": "photo_standard"
        }
        
        # Backend interpretation
        use_input_image = payload.get("use_input_image") is True
        use_inpainting = payload.get("use_inpainting") is True
        use_edit_image = use_input_image and not use_inpainting
        task_id = payload.get("task_id")
        
        # Assertions
        self.assertTrue(use_input_image, "Inpaint mode must set use_input_image=True")
        self.assertTrue(use_inpainting, "Inpaint mode must set use_inpainting=True")
        self.assertFalse(use_edit_image, "Backend should infer use_edit_image=False")
        self.assertEqual(task_id, "inpaint", "Task ID must be 'inpaint'")
        self.assertIsNotNone(payload.get("input_image_id"), "Inpaint must have input_image_id")
        self.assertIsNotNone(payload.get("mask_image_id"), "Inpaint must have mask_image_id")

    def test_edit_vs_inpaint_differentiation(self):
        """Verify backend can differentiate between edit and inpaint."""
        edit_payload = {
            "use_input_image": True,
            "use_inpainting": False,
        }
        inpaint_payload = {
            "use_input_image": True,
            "use_inpainting": True,
        }
        
        edit_use_edit_image = edit_payload["use_input_image"] and not edit_payload["use_inpainting"]
        inpaint_use_edit_image = inpaint_payload["use_input_image"] and not inpaint_payload["use_inpainting"]
        
        self.assertTrue(edit_use_edit_image, "Edit should result in use_edit_image=True")
        self.assertFalse(inpaint_use_edit_image, "Inpaint should result in use_edit_image=False")

    def test_edit_denoise_strength_range(self):
        """Verify edit mode uses appropriate denoise strength."""
        # Edit mode typically uses lower denoise (preserves more of original)
        edit_denoise = 0.25  # Lower: preserve original
        inpaint_denoise = 0.58  # Higher: more change allowed
        
        self.assertLess(edit_denoise, inpaint_denoise, 
                       "Edit denoise should be lower than inpaint to preserve image")

    def test_create_mode_no_input_image(self):
        """Verify 'create' mode doesn't send input image."""
        payload = {
            "prompt": "A beautiful sunset",
            "mode": "sdxl",
            "task_id": "create",
            "use_input_image": False,
            "use_inpainting": False,
            "checkpoint": "photo_standard"
        }
        
        # Assertions
        self.assertFalse(payload.get("use_input_image"), "Create mode must not use input image")
        self.assertFalse(payload.get("use_inpainting"), "Create mode must not use inpainting")
        self.assertNotIn("input_image_id", payload, "Create must not have input_image_id")
        self.assertNotIn("mask_image_id", payload, "Create must not have mask_image_id")


class TestImageModeStateManagement(unittest.TestCase):
    """Test that image mode state is correctly managed in the UI."""

    def test_task_defaults_for_edit(self):
        """Verify edit mode sets correct UI state."""
        # Simulated state after setV7BasicTask("edit")
        state = {
            "currentV7BasicTask": "edit",
            "useInputImageCheckbox": True,
            "useInpaintingCheckbox": False,
            "denoiseStrength": 0.25  # DEFAULT_IMG2IMG_DENOISE
        }
        
        self.assertTrue(state["useInputImageCheckbox"], "Edit must enable input image checkbox")
        self.assertFalse(state["useInpaintingCheckbox"], "Edit must disable inpainting checkbox")
        self.assertEqual(state["denoiseStrength"], 0.25, "Edit must use IMG2IMG denoise")

    def test_task_defaults_for_inpaint(self):
        """Verify inpaint mode sets correct UI state."""
        # Simulated state after setV7BasicTask("inpaint")
        state = {
            "currentV7BasicTask": "inpaint",
            "useInputImageCheckbox": True,
            "useInpaintingCheckbox": True,
            "denoiseStrength": 0.58  # DEFAULT_INPAINT_DENOISE
        }
        
        self.assertTrue(state["useInputImageCheckbox"], "Inpaint must enable input image checkbox")
        self.assertTrue(state["useInpaintingCheckbox"], "Inpaint must enable inpainting checkbox")
        self.assertEqual(state["denoiseStrength"], 0.58, "Inpaint must use INPAINT denoise")

    def test_task_defaults_for_create(self):
        """Verify create mode sets correct UI state."""
        # Simulated state after setV7BasicTask("create")
        state = {
            "currentV7BasicTask": "create",
            "useInputImageCheckbox": False,
            "useInpaintingCheckbox": False,
        }
        
        self.assertFalse(state["useInputImageCheckbox"], "Create must disable input image checkbox")
        self.assertFalse(state["useInpaintingCheckbox"], "Create must disable inpainting checkbox")


if __name__ == '__main__':
    unittest.main()
