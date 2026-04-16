from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import quote, unquote


def repo_relative_path(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def dir_access_state(
    root: Path,
    *,
    not_directory_blocker: str,
    not_accessible_blocker: str,
) -> tuple[bool, str | None]:
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, not_directory_blocker
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, not_accessible_blocker
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def resolve_internal_output_path(
    output_file: str | Path | None, *, output_root: Path
) -> tuple[Path | None, str | None]:
    if output_file is None:
        return None, "generated_file_not_accessible"

    candidate = Path(output_file)
    if not candidate.is_absolute():
        candidate = output_root / candidate

    resolved_output = candidate.resolve()
    try:
        resolved_output.relative_to(output_root)
    except ValueError:
        return None, "generated_file_not_accessible"
    return resolved_output, None


def is_accessible_output_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError:
        return False
    return True


def path_to_web_path(path: Path, *, root: Path, route_prefix: str) -> str:
    relative = path.relative_to(root)
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{route_prefix}{encoded}"


def identity_transfer_path_to_web_path(
    path: Path, *, role: str, role_root: Path, route_prefix: str
) -> str:
    relative = path.relative_to(role_root)
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{route_prefix}{quote(role)}/{encoded}"


def resolve_request_path(
    request_path: str, *, route_prefix: str, root: Path
) -> Path | None:
    if not request_path.startswith(route_prefix):
        return None

    relative = unquote(request_path.removeprefix(route_prefix))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = root.joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def resolve_multi_reference_request_path(
    request_path: str, *, route_prefix: str, root: Path
) -> Path | None:
    if not request_path.startswith(route_prefix):
        return None

    relative = unquote(request_path.removeprefix(route_prefix))
    if not relative:
        return None

    normalized_parts = PurePosixPath(relative).parts
    if not normalized_parts or any(
        part in {"", ".", ".."} for part in normalized_parts
    ):
        return None

    candidate = (root / Path(*normalized_parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def resolve_identity_transfer_role_request_path(
    request_path: str,
    *,
    route_prefix: str,
    allowed_roles: set[str],
    role_root_builder: Callable[[str], Path],
) -> Path | None:
    if not request_path.startswith(route_prefix):
        return None

    relative = unquote(request_path.removeprefix(route_prefix))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) < 2:
        return None

    role = str(pure_path.parts[0]).strip()
    if role not in allowed_roles:
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts[1:]:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    role_root = role_root_builder(role)
    candidate = role_root.joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(role_root)
    except ValueError:
        return None
    return candidate


def resolve_result_download_request_id(
    request_path: str, *, route_prefix: str
) -> str | None:
    if not request_path.startswith(route_prefix):
        return None

    relative = unquote(request_path.removeprefix(route_prefix)).strip()
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) != 1:
        return None

    result_id = pure_path.parts[0].strip()
    if not result_id or result_id in {".", ".."} or Path(result_id).name != result_id:
        return None
    return result_id


def resolve_multi_reference_slot_reset_index(
    request_path: str,
    *,
    route_prefix: str,
    slot_parser: Callable[[object], int],
) -> int | None:
    if not request_path.startswith(route_prefix):
        return None
    relative = unquote(request_path.removeprefix(route_prefix)).strip()
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) != 1:
        return None
    try:
        return slot_parser(pure_path.parts[0])
    except ValueError:
        return None


def resolve_identity_transfer_role_reset_name(
    request_path: str,
    *,
    route_prefix: str,
    role_parser: Callable[[object], str],
) -> str | None:
    if not request_path.startswith(route_prefix):
        return None
    relative = unquote(request_path.removeprefix(route_prefix)).strip()
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) != 1:
        return None
    try:
        return role_parser(pure_path.parts[0])
    except ValueError:
        return None
