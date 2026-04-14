from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from python import upload_store
from python.image_input_validation import UploadRequestError


VALID_UPLOAD_EXTENSIONS = frozenset({".png"})
VALID_UPLOAD_FORMATS = {"PNG": ("png", "image/png")}
VALID_UPLOAD_SOURCE_TYPES = frozenset({"file", "clipboard", "mask"})


def make_png_bytes(*, size: tuple[int, int] = (4, 3), color=(255, 0, 0, 255)) -> bytes:
    image = Image.new("RGBA", size, color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class UploadStoreTests(unittest.TestCase):
    def test_build_upload_success_responses_keep_existing_shape(self) -> None:
        payload = {
            "image_id": "input-1",
            "source_type": "file",
            "original_name": "sample.png",
            "stored_name": "input-1.png",
            "mime_type": "image/png",
            "size_bytes": 12,
            "width": 4,
            "height": 3,
            "preview_url": "/preview/input-1.png",
            "slot_index": 2,
            "role": "style",
            "created_at": "2026-04-06T12:00:00Z",
        }

        basic = upload_store.build_upload_success_response(payload)
        multi_reference = upload_store.build_multi_reference_upload_success_response(payload)
        identity_transfer = upload_store.build_identity_transfer_upload_success_response(payload)

        self.assertEqual("ok", basic["status"])
        self.assertTrue(basic["ok"])
        self.assertEqual(2, multi_reference["slot_index"])
        self.assertEqual("2026-04-06T12:00:00Z", multi_reference["created_at"])
        self.assertEqual("style", identity_transfer["role"])
        self.assertEqual("2026-04-06T12:00:00Z", identity_transfer["created_at"])

    def test_metadata_roundtrip_and_input_description(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "input-1.png"
            image_path.write_bytes(make_png_bytes())
            upload_store.write_input_metadata(
                image_path,
                {
                    "original_name": "clipboard.png",
                    "source_type": "clipboard",
                },
            )

            description = upload_store.describe_stored_input_image(
                image_path,
                valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                valid_upload_formats=VALID_UPLOAD_FORMATS,
                valid_upload_source_types=VALID_UPLOAD_SOURCE_TYPES,
                preview_url_builder=lambda path: f"/input/{path.name}",
            )

            self.assertEqual(
                {
                    "original_name": "clipboard.png",
                    "source_type": "clipboard",
                },
                upload_store.read_input_metadata(image_path),
            )
            self.assertIsNotNone(description)
            assert description is not None
            self.assertEqual("clipboard", description["source_type"])
            self.assertEqual("/input/input-1.png", description["preview_url"])
            self.assertEqual("image/png", description["mime_type"])

    def test_list_stored_multi_reference_images_keeps_latest_per_slot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "multi-reference-a.png"
            second = root / "multi-reference-b.png"
            third = root / "multi-reference-c.png"
            for path in (first, second, third):
                path.write_bytes(make_png_bytes())

            upload_store.write_input_metadata(
                first,
                {"original_name": "a.png", "slot_index": 0, "created_at": "2026-04-06T10:00:00Z"},
            )
            upload_store.write_input_metadata(
                second,
                {"original_name": "b.png", "slot_index": 0, "created_at": "2026-04-06T11:00:00Z"},
            )
            upload_store.write_input_metadata(
                third,
                {"original_name": "c.png", "slot_index": 1, "created_at": "2026-04-06T09:00:00Z"},
            )

            items = upload_store.list_stored_multi_reference_images(
                root,
                valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                describe_callback=lambda path: upload_store.describe_stored_multi_reference_image(
                    path,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    preview_url_builder=lambda inner_path: f"/multi/{inner_path.name}",
                    required_slot_index_parser=int,
                ),
            )

            self.assertEqual(2, len(items))
            self.assertEqual("multi-reference-b", items[0]["image_id"])
            self.assertEqual(0, items[0]["slot_index"])
            self.assertEqual("multi-reference-c", items[1]["image_id"])
            self.assertEqual(1, items[1]["slot_index"])

    def test_store_reference_image_persists_file_and_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            stored = upload_store.store_reference_image(
                "portrait.png",
                make_png_bytes(),
                reference_root=lambda: root,
                reference_dir_access_state=lambda: (True, None),
                inspect_image_upload=lambda name, payload: {
                    "original_name": name,
                    "extension": ".png",
                },
                clear_stored_reference_images=lambda: None,
                describe_stored_reference_image=lambda path: upload_store.describe_stored_reference_image(
                    path,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    preview_url_builder=lambda inner_path: f"/reference/{inner_path.name}",
                ),
                is_accessible_output_file=lambda path: path.exists(),
            )

            final_path = root / stored["stored_name"]
            self.assertTrue(final_path.exists())
            self.assertEqual("portrait.png", stored["original_name"])
            self.assertEqual("reference", stored["source_type"])
            self.assertEqual(
                {
                    "original_name": "portrait.png",
                    "source_type": "reference",
                },
                upload_store.read_input_metadata(final_path),
            )

    def test_store_multi_reference_image_returns_slot_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            stored = upload_store.store_multi_reference_image(
                "style.png",
                make_png_bytes(),
                slot_index=None,
                multi_reference_root=lambda: root,
                multi_reference_dir_access_state=lambda: (True, None),
                inspect_image_upload=lambda name, payload: {
                    "original_name": name,
                    "extension": ".png",
                },
                find_first_free_multi_reference_slot=lambda: 3,
                clear_stored_multi_reference_images=lambda **kwargs: None,
                describe_stored_multi_reference_image=lambda path: upload_store.describe_stored_multi_reference_image(
                    path,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    preview_url_builder=lambda inner_path: f"/multi/{inner_path.name}",
                    required_slot_index_parser=int,
                ),
                is_accessible_output_file=lambda path: path.exists(),
                utc_now_iso=lambda: "2026-04-06T12:00:00Z",
            )

            final_path = root / stored["stored_name"]
            self.assertEqual(3, stored["slot_index"])
            self.assertEqual("2026-04-06T12:00:00Z", stored["created_at"])
            self.assertEqual(
                {
                    "original_name": "style.png",
                    "source_type": "multi_reference",
                    "slot_index": 3,
                    "created_at": "2026-04-06T12:00:00Z",
                },
                upload_store.read_input_metadata(final_path),
            )

    def test_store_identity_transfer_role_image_returns_role_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "face").mkdir(parents=True, exist_ok=True)

            stored = upload_store.store_identity_transfer_role_image(
                "face.png",
                make_png_bytes(),
                role="face",
                identity_transfer_role_root=lambda role: root / role,
                identity_transfer_dir_access_state=lambda role: (True, None),
                inspect_image_upload=lambda name, payload: {
                    "original_name": name,
                    "extension": ".png",
                },
                clear_stored_identity_transfer_role_images=lambda role: None,
                describe_stored_identity_transfer_role_image=lambda path, role: upload_store.describe_stored_identity_transfer_role_image(
                    path,
                    role,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    preview_url_builder=lambda inner_path, inner_role: f"/identity/{inner_role}/{inner_path.name}",
                ),
                is_accessible_output_file=lambda path: path.exists(),
                utc_now_iso=lambda: "2026-04-06T12:30:00Z",
            )

            final_path = (root / "face") / stored["stored_name"]
            self.assertTrue(final_path.exists())
            self.assertEqual("face", stored["role"])
            self.assertEqual("2026-04-06T12:30:00Z", stored["created_at"])
            self.assertEqual(
                {
                    "original_name": "face.png",
                    "source_type": "identity_transfer_role",
                    "role": "face",
                    "created_at": "2026-04-06T12:30:00Z",
                },
                upload_store.read_input_metadata(final_path),
            )

    def test_store_uploaded_image_reuses_existing_mask_pipeline(self) -> None:
        with TemporaryDirectory() as temp_dir:
            mask_root = Path(temp_dir) / "mask"
            input_root = Path(temp_dir) / "input"
            mask_root.mkdir(parents=True, exist_ok=True)
            input_root.mkdir(parents=True, exist_ok=True)

            cleared = {"mask": 0, "input": 0}

            stored = upload_store.store_uploaded_image(
                "mask.png",
                b"raw-mask",
                "mask",
                normalize_source_type=lambda value: str(value),
                mask_root=lambda: mask_root,
                input_root=lambda: input_root,
                mask_dir_access_state=lambda: (True, None),
                input_dir_access_state=lambda: (True, None),
                inspect_image_upload=lambda name, payload: {
                    "original_name": name,
                    "extension": ".png",
                },
                normalize_mask_upload_payload=lambda payload: (
                    make_png_bytes(size=(8, 6)),
                    {"width": 8, "height": 6},
                ),
                clear_stored_mask_images=lambda: cleared.__setitem__("mask", cleared["mask"] + 1),
                clear_stored_input_images=lambda: cleared.__setitem__("input", cleared["input"] + 1),
                describe_stored_mask_image=lambda path: upload_store.describe_stored_mask_image(
                    path,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    preview_url_builder=lambda inner_path: f"/mask/{inner_path.name}",
                ),
                describe_stored_input_image=lambda path: upload_store.describe_stored_input_image(
                    path,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    valid_upload_source_types=VALID_UPLOAD_SOURCE_TYPES,
                    preview_url_builder=lambda inner_path: f"/input/{inner_path.name}",
                ),
                is_accessible_output_file=lambda path: path.exists(),
            )

            final_path = mask_root / stored["stored_name"]
            self.assertEqual(1, cleared["mask"])
            self.assertEqual(0, cleared["input"])
            self.assertTrue(final_path.exists())
            self.assertEqual("mask", stored["source_type"])
            self.assertEqual(8, stored["width"])
            self.assertEqual(6, stored["height"])

    def test_store_multi_reference_image_reports_full_slots(self) -> None:
        with self.assertRaises(UploadRequestError) as context:
            upload_store.store_multi_reference_image(
                "style.png",
                make_png_bytes(),
                slot_index=None,
                multi_reference_root=lambda: Path("."),
                multi_reference_dir_access_state=lambda: (True, None),
                inspect_image_upload=lambda name, payload: {
                    "original_name": name,
                    "extension": ".png",
                },
                find_first_free_multi_reference_slot=lambda: None,
                clear_stored_multi_reference_images=lambda **kwargs: None,
                describe_stored_multi_reference_image=lambda path: None,
                is_accessible_output_file=lambda path: False,
                utc_now_iso=lambda: "2026-04-06T12:00:00Z",
            )

        self.assertEqual("multi_reference_slots_full", context.exception.blocker)


if __name__ == "__main__":
    unittest.main()
