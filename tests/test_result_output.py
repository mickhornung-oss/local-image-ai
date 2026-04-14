from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import unittest

from PIL import Image

from python import result_output


VALID_UPLOAD_EXTENSIONS = frozenset({".png"})
VALID_UPLOAD_FORMATS = {"PNG": (".png", "image/png")}


def make_png_bytes(*, size: tuple[int, int] = (8, 6)) -> bytes:
    image = Image.new("RGBA", size, (255, 0, 0, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class ResultOutputTests(unittest.TestCase):
    def test_build_result_metadata_item_maps_preview_and_download(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "result-1.png"
            image_path.write_bytes(make_png_bytes())

            item = result_output.build_result_metadata_item(
                {
                    "result_id": "result-1",
                    "created_at": "2026-04-06T12:00:00Z",
                    "file_name": "result-1.png",
                    "mode": "txt2img",
                    "prompt": "Hello",
                    "checkpoint": "model.safetensors",
                    "store_scope": "app_results",
                },
                image_path,
                result_root=root,
                is_accessible_output_file=lambda path: path.exists(),
                inspect_result_image=lambda path: result_output.inspect_result_image(
                    path,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                ),
                retention_limit=10,
                default_retention_limit=50,
                preview_url_builder=lambda path: f"/results/{path.name}",
                download_url_builder=lambda result_id: f"/download/{result_id}",
            )

            self.assertIsNotNone(item)
            assert item is not None
            self.assertEqual("/results/result-1.png", item["preview_url"])
            self.assertEqual("/download/result-1", item["download_url"])
            self.assertEqual(10, item["retention_limit"])

    def test_capture_generated_result_persists_copy_and_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_root = root / "output"
            result_root = root / "results"
            output_root.mkdir()
            result_root.mkdir()
            source = output_root / "generated.png"
            source.write_bytes(make_png_bytes())

            captured = result_output.capture_generated_result(
                str(source),
                render_mode="txt2img",
                prompt="Prompt",
                checkpoint="model.safetensors",
                use_input_image=False,
                use_inpainting=False,
                extra_metadata={"experimental": True},
                results_dir_access_state=lambda: (True, None),
                resolve_internal_output_path=lambda output_file: (Path(str(output_file)).resolve(), None),
                is_accessible_output_file=lambda path: path.exists(),
                inspect_result_image=lambda path: result_output.inspect_result_image(
                    path,
                    valid_upload_formats=VALID_UPLOAD_FORMATS,
                    valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                ),
                result_root=result_root,
                utc_now_iso=lambda: "2026-04-06T12:00:00Z",
                write_result_metadata=result_output.write_result_metadata,
                build_result_metadata_item=lambda payload, path: result_output.build_result_metadata_item(
                    payload,
                    path,
                    result_root=result_root,
                    is_accessible_output_file=lambda candidate: candidate.exists(),
                    inspect_result_image=lambda candidate: result_output.inspect_result_image(
                        candidate,
                        valid_upload_formats=VALID_UPLOAD_FORMATS,
                        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
                    ),
                    retention_limit=25,
                    default_retention_limit=50,
                    preview_url_builder=lambda candidate: f"/results/{candidate.name}",
                    download_url_builder=lambda result_id: f"/download/{result_id}",
                ),
                resolve_result_mode_name=lambda mode, use_input_image, use_inpainting: "txt2img",
                enforce_result_retention=lambda: {"retention_limit": 25},
            )

            stored_path = result_root / captured["file_name"]
            metadata_path = result_root / f"{captured['result_id']}.json"
            self.assertTrue(stored_path.exists())
            self.assertTrue(metadata_path.exists())
            self.assertEqual("/results/" + stored_path.name, captured["preview_url"])

    def test_create_result_export_copies_result_and_builds_payload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results_root = root / "results"
            exports_root = root / "exports"
            results_root.mkdir()
            exports_root.mkdir()
            image_path = results_root / "result-1.png"
            image_path.write_bytes(make_png_bytes())

            payload = result_output.create_result_export(
                "result-1",
                results_dir_access_state=lambda: (True, None),
                exports_dir_access_state=lambda: (True, None),
                resolve_result_download_item=lambda result_id: (
                    {"result_id": result_id, "file_name": "result-1.png", "mode": "txt2img", "checkpoint": "model.safetensors"},
                    image_path,
                ),
                reserve_export_target_path=lambda file_name: exports_root / file_name,
                build_result_export_file_name=lambda result_item: "export-test.png",
                write_result_metadata=result_output.write_result_metadata,
                export_url_builder=lambda path: f"/exports/{path.name}",
                utc_now_iso=lambda: "2026-04-06T12:30:00Z",
            )

            self.assertEqual("result-1", payload["result_id"])
            self.assertEqual("export-test.png", payload["export_file_name"])
            self.assertEqual("/exports/export-test.png", payload["export_url"])
            self.assertTrue((exports_root / "export-test.png").exists())
            self.assertTrue((exports_root / "export-test.json").exists())

    def test_delete_stored_result_removes_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results_root = root / "results"
            results_root.mkdir()
            image_path = results_root / "result-20260406120000-abcd1234.png"
            metadata_path = results_root / "result-20260406120000-abcd1234.json"
            image_path.write_bytes(make_png_bytes())
            metadata_path.write_text("{}", encoding="utf-8")

            payload = result_output.delete_stored_result(
                "result-20260406120000-abcd1234",
                is_managed_result_id=lambda value: bool(re.fullmatch(r"result-\d{14}-[0-9a-f]{8}", str(value))),
                results_dir_access_state=lambda: (True, None),
                resolve_result_download_item=lambda result_id: (
                    {"result_id": result_id, "file_name": image_path.name, "store_scope": "app_results"},
                    image_path,
                ),
                result_root=results_root,
                list_result_store_records=lambda: [],
            )

            self.assertTrue(payload["deleted"])
            self.assertFalse(image_path.exists())
            self.assertFalse(metadata_path.exists())

    def test_finalize_generate_result_maps_success_payload(self) -> None:
        status, payload = result_output.finalize_generate_result(
            {"status": "ok", "mode": "txt2img", "prompt_id": "prompt-1", "output_file": "ignored.png"},
            "req-1",
            prompt="Prompt",
            checkpoint="model.safetensors",
            use_input_image=False,
            use_inpainting=False,
            extra_metadata=None,
            capture_generated_result=lambda *args, **kwargs: {
                "result_id": "result-1",
                "preview_url": "/results/result-1.png",
                "download_url": "/download/result-1",
            },
            build_generate_response=lambda **kwargs: kwargs,
            build_error_response=lambda **kwargs: kwargs,
        )

        self.assertEqual(200, int(status))
        self.assertEqual("/results/result-1.png", payload["output_file"])
        self.assertEqual("result-1", payload["result_id"])
        self.assertEqual("/download/result-1", payload["download_url"])

    def test_storage_summary_and_success_payload_helpers_keep_shape(self) -> None:
        summary = result_output.build_results_storage_summary(
            app_results_count=4,
            cleanup_report={"stale_results_removed": 2},
            retention_limit=50,
            default_retention_limit=50,
            results_dir="data/results",
            exports_dir="data/exports",
            exports_dir_access_state=lambda: (True, None),
            count_export_store_files=lambda: 3,
        )
        export_payload = result_output.build_result_export_success_response({"result_id": "r1"})
        delete_payload = result_output.build_result_delete_success_response({"result_id": "r1"})
        list_payload = result_output.build_results_list_response(
            count=1,
            total_count=2,
            limit=20,
            items=[{"result_id": "r1"}],
            storage=summary,
        )

        self.assertEqual(4, summary["results_count"])
        self.assertEqual(3, summary["exports_count"])
        self.assertTrue(export_payload["ok"])
        self.assertTrue(delete_payload["ok"])
        self.assertEqual(2, list_payload["total_count"])


if __name__ == "__main__":
    unittest.main()
