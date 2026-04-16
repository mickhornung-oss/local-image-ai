from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

import python.image_input_validation as image_input_validation


def _png_bytes(*, size: tuple[int, int] = (4, 4), color=(255, 0, 0, 255)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


class ImageInputValidationTests(unittest.TestCase):
    def test_normalize_optional_negative_prompt_and_source_type(self) -> None:
        self.assertEqual(
            image_input_validation.normalize_optional_negative_prompt(
                " no blur ", max_length=20
            ),
            ("no blur", None),
        )
        self.assertEqual(
            image_input_validation.normalize_optional_negative_prompt(
                123, max_length=20
            ),
            (None, "negative_prompt_not_string"),
        )
        self.assertEqual(
            image_input_validation.normalize_upload_source_type(
                " clipboard ",
                valid_source_types=frozenset({"file", "clipboard", "mask"}),
            ),
            "clipboard",
        )

    def test_parse_multi_reference_slot_and_identity_role(self) -> None:
        self.assertEqual(
            image_input_validation.parse_optional_multi_reference_slot_index(
                "2", max_slots=3
            ),
            2,
        )
        self.assertIsNone(
            image_input_validation.parse_optional_multi_reference_slot_index(
                "auto", max_slots=3
            )
        )
        with self.assertRaises(ValueError):
            image_input_validation.parse_required_multi_reference_slot_index(
                "", max_slots=3
            )
        self.assertEqual(
            image_input_validation.parse_required_identity_transfer_role(
                "identity_head_reference",
                allowed_roles=frozenset(
                    {"identity_head_reference", "target_body_image"}
                ),
            ),
            "identity_head_reference",
        )

    def test_inspect_image_upload_and_mask_normalization(self) -> None:
        payload = _png_bytes()
        info = image_input_validation.inspect_image_upload(
            "sample.png",
            payload,
            valid_extensions=frozenset({".png", ".jpg", ".jpeg", ".webp"}),
            upload_max_bytes=1024 * 1024,
            valid_formats={"PNG": (".png", "image/png")},
        )
        self.assertEqual(info["extension"], ".png")
        self.assertEqual(info["mime_type"], "image/png")
        self.assertEqual(info["width"], 4)

        (
            normalized_payload,
            normalized_info,
        ) = image_input_validation.normalize_mask_upload_payload(
            payload,
            mask_binary_threshold=128,
        )
        self.assertTrue(normalized_payload)
        self.assertEqual(normalized_info["extension"], ".png")
        self.assertEqual(normalized_info["width"], 4)

    def test_validate_browser_mask_payload_checks_dimensions_and_empty_mask(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.png"
            source_path.write_bytes(_png_bytes(size=(4, 4)))

            image_input_validation.validate_browser_mask_payload(
                _png_bytes(size=(4, 4), color=(255, 255, 255, 255)),
                source_path,
                mask_binary_threshold=128,
            )

            with self.assertRaises(
                image_input_validation.UploadRequestError
            ) as mismatch_exc:
                image_input_validation.validate_browser_mask_payload(
                    _png_bytes(size=(8, 8), color=(255, 255, 255, 255)),
                    source_path,
                    mask_binary_threshold=128,
                )
            self.assertEqual(mismatch_exc.exception.blocker, "mask_size_mismatch")

            with self.assertRaises(
                image_input_validation.UploadRequestError
            ) as empty_exc:
                image_input_validation.validate_browser_mask_payload(
                    _png_bytes(size=(4, 4), color=(0, 0, 0, 255)),
                    source_path,
                    mask_binary_threshold=128,
                )
            self.assertEqual(empty_exc.exception.blocker, "empty_mask")

    def test_parse_multipart_helpers_validate_expected_fields(self) -> None:
        boundary = "----boundary"
        multipart = (
            (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="slot_index"\r\n\r\n'
                "2\r\n"
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="file"; filename="image.png"\r\n'
                "Content-Type: image/png\r\n\r\n"
            ).encode("utf-8")
            + _png_bytes()
            + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )
        (
            original_name,
            payload,
            slot_index,
        ) = image_input_validation.parse_multipart_multi_reference_image(
            f"multipart/form-data; boundary={boundary}",
            multipart,
            slot_index_parser=lambda value: image_input_validation.parse_optional_multi_reference_slot_index(
                value, max_slots=3
            ),
        )
        self.assertEqual(original_name, "image.png")
        self.assertEqual(slot_index, 2)
        self.assertTrue(payload)


if __name__ == "__main__":
    unittest.main()
