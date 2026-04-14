from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from python import app_request_utils


class DummyUploadError(Exception):
    def __init__(self, *, status_code, error_type, blocker, message) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.blocker = blocker
        self.message = message


class AppRequestUtilsTests(unittest.TestCase):
    def test_read_json_file_detail_roundtrip_and_invalid_payload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            good = root / "good.json"
            bad = root / "bad.json"
            good.write_text('{"ok": true}', encoding="utf-8")
            bad.write_text('["not", "a", "dict"]', encoding="utf-8")

            self.assertEqual(({"ok": True}, None), app_request_utils.read_json_file_detail(good))
            self.assertEqual((None, "invalid_payload"), app_request_utils.read_json_file_detail(bad))

    def test_parse_results_limit_and_validate_mode(self) -> None:
        self.assertEqual(25, app_request_utils.parse_results_limit("?limit=25", default_limit=20, max_limit=100))
        self.assertEqual("edit", app_request_utils.validate_mode("EDIT", valid_modes={"auto", "edit"}))
        with self.assertRaises(ValueError):
            app_request_utils.parse_results_limit("?limit=0", default_limit=20, max_limit=100)

    def test_parse_boolean_flag(self) -> None:
        self.assertTrue(app_request_utils.parse_boolean_flag("yes"))
        self.assertFalse(app_request_utils.parse_boolean_flag("", default=True))
        with self.assertRaises(ValueError):
            app_request_utils.parse_boolean_flag("maybe")

    def test_decode_data_url_image_accepts_valid_payload_and_rejects_invalid(self) -> None:
        mime_type, payload = app_request_utils.decode_data_url_image(
            "data:image/png;base64,aGVsbG8=",
            valid_upload_mime_types={"image/png"},
            upload_error_cls=DummyUploadError,
        )
        self.assertEqual("image/png", mime_type)
        self.assertEqual(b"hello", payload)

        with self.assertRaises(DummyUploadError) as context:
            app_request_utils.decode_data_url_image(
                "data:text/plain;base64,aGVsbG8=",
                valid_upload_mime_types={"image/png"},
                upload_error_cls=DummyUploadError,
            )
        self.assertEqual("invalid_file_type", context.exception.blocker)


if __name__ == "__main__":
    unittest.main()
