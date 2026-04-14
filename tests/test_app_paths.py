from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from python import app_paths


class AppPathsTests(unittest.TestCase):
    def test_repo_relative_path_prefers_repo_relative(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "data" / "file.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x", encoding="utf-8")

            self.assertEqual("data/file.txt", app_paths.repo_relative_path(target, repo_root=root))

    def test_dir_access_state_creates_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "newdir"
            ok, error = app_paths.dir_access_state(
                root,
                not_directory_blocker="not_dir",
                not_accessible_blocker="not_accessible",
            )

            self.assertTrue(ok)
            self.assertIsNone(error)
            self.assertTrue(root.exists())

    def test_path_to_web_path_and_identity_transfer_path_to_web_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "a file.png"
            path.write_text("x", encoding="utf-8")

            web_path = app_paths.path_to_web_path(path, root=root, route_prefix="/files/")
            identity_path = app_paths.identity_transfer_path_to_web_path(
                path,
                role="face role",
                role_root=root,
                route_prefix="/identity/",
            )

            self.assertEqual("/files/a%20file.png", web_path)
            self.assertEqual("/identity/face%20role/a%20file.png", identity_path)

    def test_resolve_request_path_rejects_escape_and_resolves_valid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid = app_paths.resolve_request_path("/files/a/b.png", route_prefix="/files/", root=root)
            invalid = app_paths.resolve_request_path("/files/../b.png", route_prefix="/files/", root=root)

            self.assertEqual((root / "a" / "b.png").resolve(), valid)
            self.assertIsNone(invalid)

    def test_resolve_identity_transfer_role_request_path_and_reset_helpers(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            role_root_builder = lambda role: root / role

            path = app_paths.resolve_identity_transfer_role_request_path(
                "/identity/face/image.png",
                route_prefix="/identity/",
                allowed_roles={"face"},
                role_root_builder=role_root_builder,
            )
            role = app_paths.resolve_identity_transfer_role_reset_name(
                "/reset/face",
                route_prefix="/reset/",
                role_parser=lambda value: str(value) if str(value) == "face" else (_ for _ in ()).throw(ValueError()),
            )

            self.assertEqual((root / "face" / "image.png").resolve(), path)
            self.assertEqual("face", role)

    def test_resolve_result_download_request_id_and_slot_reset_index(self) -> None:
        result_id = app_paths.resolve_result_download_request_id(
            "/download/result-1",
            route_prefix="/download/",
        )
        slot_index = app_paths.resolve_multi_reference_slot_reset_index(
            "/slot/2",
            route_prefix="/slot/",
            slot_parser=lambda value: int(value),
        )

        self.assertEqual("result-1", result_id)
        self.assertEqual(2, slot_index)


if __name__ == "__main__":
    unittest.main()
