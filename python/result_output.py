from __future__ import annotations

import json
import mimetypes
import os
import secrets
import shutil
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Callable

from PIL import Image, UnidentifiedImageError


class ResultStoreError(Exception):
    def __init__(
        self,
        *,
        status_code: HTTPStatus,
        error_type: str,
        blocker: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.blocker = blocker
        self.message = message


def inspect_result_image(
    path: Path,
    *,
    valid_upload_formats: dict[str, tuple[str, str]],
    valid_upload_extensions: set[str] | frozenset[str],
) -> dict:
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="output_file_missing",
            blocker="generated_file_not_accessible",
            message="Generated result image is not readable.",
        ) from exc

    format_info = valid_upload_formats.get(format_name)
    extension = path.suffix.lower()
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if format_info is not None:
        extension, mime_type = format_info

    return {
        "extension": extension if extension in valid_upload_extensions else ".png",
        "mime_type": mime_type,
        "width": int(width),
        "height": int(height),
        "size_bytes": path.stat().st_size,
    }


def write_result_metadata(path: Path, metadata: dict) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(json.dumps(metadata, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    temp_path.replace(path)


def get_result_retention_limit(*, raw_value: str | None, default_limit: int) -> int:
    if raw_value is None:
        return default_limit

    normalized_value = raw_value.strip()
    if not normalized_value:
        return default_limit

    try:
        parsed_value = int(normalized_value)
    except ValueError:
        return default_limit

    return parsed_value if parsed_value >= 1 else default_limit


def is_managed_result_id(value: object, *, pattern) -> bool:
    candidate = str(value or "").strip()
    return bool(pattern.fullmatch(candidate))


def resolve_result_mode_name(
    render_mode: object,
    *,
    use_input_image: bool,
    use_inpainting: bool,
    identity_research_mode: str,
    identity_reference_mode: str,
    identity_multi_reference_mode: str,
    identity_transfer_mode: str,
    identity_transfer_mask_hybrid_mode: str,
) -> str:
    normalized_mode = str(render_mode or "").strip().lower()
    if normalized_mode == "placeholder":
        return "placeholder"
    if normalized_mode == identity_research_mode:
        return identity_research_mode
    if normalized_mode == identity_reference_mode:
        return identity_reference_mode
    if normalized_mode == identity_multi_reference_mode:
        return identity_multi_reference_mode
    if normalized_mode == identity_transfer_mode:
        return identity_transfer_mode
    if normalized_mode == identity_transfer_mask_hybrid_mode:
        return identity_transfer_mask_hybrid_mode
    if use_inpainting:
        return "inpainting"
    if use_input_image:
        return "img2img"
    return "txt2img"


def build_result_metadata_item(
    metadata_payload: dict,
    image_path: Path,
    *,
    result_root: Path,
    is_accessible_output_file: Callable[[Path], bool],
    inspect_result_image: Callable[[Path], dict],
    retention_limit: int,
    default_retention_limit: int,
    preview_url_builder: Callable[[Path], str],
    download_url_builder: Callable[[str], str],
) -> dict | None:
    result_id = str(metadata_payload.get("result_id") or "").strip()
    file_name = str(metadata_payload.get("file_name") or "").strip()
    created_at = str(metadata_payload.get("created_at") or "").strip()
    if not result_id or not file_name or not created_at:
        return None

    candidate = (result_root / Path(file_name).name).resolve()
    try:
        candidate.relative_to(result_root)
    except ValueError:
        return None

    if candidate != image_path.resolve():
        return None
    if not is_accessible_output_file(candidate):
        return None

    try:
        image_info = inspect_result_image(candidate)
    except ResultStoreError:
        return None
    effective_limit = retention_limit if retention_limit >= 1 else default_retention_limit
    return {
        "result_id": result_id,
        "created_at": created_at,
        "mode": str(metadata_payload.get("mode") or "txt2img").strip() or "txt2img",
        "prompt": str(metadata_payload.get("prompt") or "").strip(),
        "negative_prompt": str(metadata_payload.get("negative_prompt") or "").strip() or None,
        "checkpoint": str(metadata_payload.get("checkpoint") or "").strip() or None,
        "width": image_info["width"],
        "height": image_info["height"],
        "file_name": candidate.name,
        "mime_type": image_info["mime_type"],
        "size_bytes": image_info["size_bytes"],
        "preview_url": preview_url_builder(candidate),
        "download_url": download_url_builder(result_id),
        "reference_count": metadata_payload.get("reference_count") if isinstance(metadata_payload.get("reference_count"), int) else None,
        "reference_slots": metadata_payload.get("reference_slots") if isinstance(metadata_payload.get("reference_slots"), list) else None,
        "reference_image_ids": metadata_payload.get("reference_image_ids") if isinstance(metadata_payload.get("reference_image_ids"), list) else None,
        "provider": str(metadata_payload.get("provider") or "").strip() or None,
        "identity_research_provider": str(metadata_payload.get("identity_research_provider") or "").strip() or None,
        "identity_research_workflow": str(metadata_payload.get("identity_research_workflow") or "").strip() or None,
        "identity_research_reference_image_id": str(metadata_payload.get("identity_research_reference_image_id") or "").strip() or None,
        "identity_research_reference_file_name": str(metadata_payload.get("identity_research_reference_file_name") or "").strip() or None,
        "experimental": metadata_payload.get("experimental") if isinstance(metadata_payload.get("experimental"), bool) else None,
        "multi_reference_strategy": str(metadata_payload.get("multi_reference_strategy") or "").strip() or None,
        "used_roles": metadata_payload.get("used_roles") if isinstance(metadata_payload.get("used_roles"), list) else None,
        "pose_reference_present": metadata_payload.get("pose_reference_present") if isinstance(metadata_payload.get("pose_reference_present"), bool) else None,
        "pose_reference_used": metadata_payload.get("pose_reference_used") if isinstance(metadata_payload.get("pose_reference_used"), bool) else None,
        "transfer_mask_present": metadata_payload.get("transfer_mask_present") if isinstance(metadata_payload.get("transfer_mask_present"), bool) else None,
        "transfer_mask_used": metadata_payload.get("transfer_mask_used") if isinstance(metadata_payload.get("transfer_mask_used"), bool) else None,
        "identity_head_reference_image_id": str(metadata_payload.get("identity_head_reference_image_id") or "").strip() or None,
        "target_body_image_id": str(metadata_payload.get("target_body_image_id") or "").strip() or None,
        "pose_reference_image_id": str(metadata_payload.get("pose_reference_image_id") or "").strip() or None,
        "transfer_mask_image_id": str(metadata_payload.get("transfer_mask_image_id") or "").strip() or None,
        "identity_transfer_strategy": str(metadata_payload.get("identity_transfer_strategy") or "").strip() or None,
        "store_scope": str(metadata_payload.get("store_scope") or "app_results").strip() or "app_results",
        "cleanup_policy": str(metadata_payload.get("cleanup_policy") or "retention_limit").strip() or "retention_limit",
        "retention_limit": effective_limit,
        "source_output_file": str(metadata_payload.get("source_output_file") or "").strip() or None,
    }


def list_result_store_records(
    *,
    result_root: Path,
    read_json_file_detail: Callable[[Path], tuple[dict | None, str | None]],
    is_accessible_output_file: Callable[[Path], bool],
) -> list[dict]:
    result_root.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for metadata_path in result_root.iterdir():
        if not metadata_path.is_file() or metadata_path.suffix.lower() != ".json":
            continue

        payload, error = read_json_file_detail(metadata_path)
        if payload is None or error is not None:
            continue

        result_id = str(payload.get("result_id") or "").strip()
        file_name = str(payload.get("file_name") or "").strip()
        created_at = str(payload.get("created_at") or "").strip()
        if not result_id or not file_name or not created_at:
            continue

        image_path = (result_root / Path(file_name).name).resolve()
        try:
            image_path.relative_to(result_root)
        except ValueError:
            continue
        if not is_accessible_output_file(image_path):
            continue

        records.append(
            {
                "result_id": result_id,
                "created_at": created_at,
                "metadata_path": metadata_path.resolve(),
                "image_path": image_path,
            }
        )

    records.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("result_id") or ""),
        ),
        reverse=True,
    )
    return records


def cleanup_result_store_housekeeping(
    *,
    result_root: Path,
    valid_upload_extensions: set[str] | frozenset[str],
    is_managed_result_id: Callable[[object], bool],
    managed_result_tmp_pattern,
    valid_result_ids: set[str] | None = None,
    stale_tmp_age_seconds: int = 600,
    error_logger: Callable[[str], None] | None = None,
) -> dict:
    result_root.mkdir(parents=True, exist_ok=True)
    valid_ids = valid_result_ids if isinstance(valid_result_ids, set) else set()

    removed_orphan_metadata = 0
    removed_orphan_images = 0
    removed_stale_temp = 0
    now_timestamp = datetime.now(timezone.utc).timestamp()

    for candidate in result_root.iterdir():
        if not candidate.is_file():
            continue

        suffix = candidate.suffix.lower()
        file_name = candidate.name
        try:
            if suffix == ".json":
                result_id = candidate.stem
                if is_managed_result_id(result_id) and result_id not in valid_ids:
                    candidate.unlink(missing_ok=True)
                    removed_orphan_metadata += 1
                continue

            if suffix in valid_upload_extensions:
                result_id = candidate.stem
                if is_managed_result_id(result_id) and result_id not in valid_ids:
                    candidate.unlink(missing_ok=True)
                    removed_orphan_images += 1
                continue

            if suffix == ".tmp":
                if not managed_result_tmp_pattern.fullmatch(file_name.lower()):
                    continue
                age_seconds = max(0.0, now_timestamp - candidate.stat().st_mtime)
                if age_seconds < max(1, stale_tmp_age_seconds):
                    continue
                candidate.unlink(missing_ok=True)
                removed_stale_temp += 1
        except OSError as exc:
            if error_logger is not None:
                error_logger(f"[result-cleanup] failed to remove {candidate.name}: {exc}")

    return {
        "orphan_metadata_removed": removed_orphan_metadata,
        "orphan_images_removed": removed_orphan_images,
        "stale_temp_removed": removed_stale_temp,
    }


def enforce_result_retention(
    *,
    retain_count: int | None,
    default_retention_limit: int,
    list_result_store_records: Callable[[], list[dict]],
    is_managed_result_id: Callable[[object], bool],
    cleanup_result_store_housekeeping: Callable[[set[str]], dict],
    error_logger: Callable[[str], None] | None = None,
) -> dict:
    effective_limit = retain_count if retain_count is not None else default_retention_limit
    if effective_limit < 1:
        effective_limit = default_retention_limit

    store_records = list_result_store_records()
    stale_records = store_records[effective_limit:]
    removed_stale_results = 0
    for record in stale_records:
        removed_any = False
        for target_path in (record["metadata_path"], record["image_path"]):
            try:
                if target_path.exists():
                    removed_any = True
                target_path.unlink(missing_ok=True)
            except OSError as exc:
                if error_logger is not None:
                    error_logger(f"[result-retention] failed to remove {target_path.name}: {exc}")
        if removed_any:
            removed_stale_results += 1

    valid_result_ids = {
        str(record.get("result_id") or "").strip()
        for record in list_result_store_records()
        if is_managed_result_id(record.get("result_id"))
    }
    housekeeping = cleanup_result_store_housekeeping(valid_result_ids)
    return {
        "retention_limit": effective_limit,
        "stale_results_removed": removed_stale_results,
        "orphan_metadata_removed": housekeeping["orphan_metadata_removed"],
        "orphan_images_removed": housekeeping["orphan_images_removed"],
        "stale_temp_removed": housekeeping["stale_temp_removed"],
    }


def capture_generated_result(
    output_file: str | Path | None,
    *,
    render_mode: object,
    prompt: str,
    checkpoint: str | None,
    use_input_image: bool,
    use_inpainting: bool,
    extra_metadata: dict | None,
    results_dir_access_state: Callable[[], tuple[bool, str | None]],
    resolve_internal_output_path: Callable[[str | Path | None], tuple[Path | None, str | None]],
    is_accessible_output_file: Callable[[Path], bool],
    inspect_result_image: Callable[[Path], dict],
    result_root: Path,
    utc_now_iso: Callable[[], str],
    write_result_metadata: Callable[[Path, dict], None],
    build_result_metadata_item: Callable[[dict, Path], dict | None],
    resolve_result_mode_name: Callable[[object, bool, bool], str],
    enforce_result_retention: Callable[[], dict],
) -> dict:
    results_dir_accessible, results_dir_error = results_dir_access_state()
    if not results_dir_accessible:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker=results_dir_error or "results_dir_not_accessible",
            message="Results directory is not accessible.",
        )

    source_output, output_error = resolve_internal_output_path(output_file)
    if source_output is None or not is_accessible_output_file(source_output):
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="output_file_missing",
            blocker=output_error or "generated_file_not_accessible",
            message="Generated result image is not accessible.",
        )

    image_info = inspect_result_image(source_output)
    result_id = f"result-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    file_name = f"{result_id}{image_info['extension']}"
    final_path = result_root / file_name
    temp_path = result_root / f".{file_name}.tmp"
    metadata_path = result_root / f"{result_id}.json"
    created_at = utc_now_iso()
    metadata_payload = {
        "result_id": result_id,
        "created_at": created_at,
        "mode": resolve_result_mode_name(render_mode, use_input_image, use_inpainting),
        "prompt": prompt,
        "checkpoint": checkpoint or None,
        "width": image_info["width"],
        "height": image_info["height"],
        "file_name": file_name,
        "store_scope": "app_results",
        "cleanup_policy": "retention_limit",
        "source_output_file": str(source_output),
    }
    if isinstance(extra_metadata, dict) and extra_metadata:
        metadata_payload.update(extra_metadata)

    try:
        shutil.copyfile(source_output, temp_path)
        temp_path.replace(final_path)
        write_result_metadata(metadata_path, metadata_payload)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker="results_storage_error",
            message="Generated result could not be stored.",
        ) from exc

    metadata_item = build_result_metadata_item(metadata_payload, final_path)
    if metadata_item is None:
        final_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker="results_metadata_invalid",
            message="Stored result metadata is invalid.",
        )

    enforce_result_retention()
    return metadata_item


def read_result_item(
    metadata_path: Path,
    *,
    read_json_file_detail: Callable[[Path], tuple[dict | None, str | None]],
    result_root: Path,
    build_result_metadata_item: Callable[[dict, Path], dict | None],
) -> dict | None:
    payload, error = read_json_file_detail(metadata_path)
    if payload is None or error is not None:
        return None

    file_name = str(payload.get("file_name") or "").strip()
    if not file_name:
        return None

    image_path = (result_root / Path(file_name).name).resolve()
    try:
        image_path.relative_to(result_root)
    except ValueError:
        return None

    return build_result_metadata_item(payload, image_path)


def list_stored_results(
    *,
    limit: int,
    result_root: Path,
    read_result_item: Callable[[Path], dict | None],
) -> list[dict]:
    result_root.mkdir(parents=True, exist_ok=True)
    metadata_paths = sorted(
        (path for path in result_root.iterdir() if path.is_file() and path.suffix.lower() == ".json"),
        reverse=True,
    )

    items: list[dict] = []
    for metadata_path in metadata_paths:
        item = read_result_item(metadata_path)
        if item is not None:
            items.append(item)

    items.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("result_id") or ""),
        ),
        reverse=True,
    )
    return items[:limit]


def resolve_result_download_item(
    result_id: str,
    *,
    result_root: Path,
    read_result_item: Callable[[Path], dict | None],
    is_accessible_output_file: Callable[[Path], bool],
) -> tuple[dict | None, Path | None]:
    metadata_path = (result_root / f"{Path(result_id).name}.json").resolve()
    try:
        metadata_path.relative_to(result_root)
    except ValueError:
        return None, None

    item = read_result_item(metadata_path)
    if item is None:
        return None, None

    image_path = (result_root / item["file_name"]).resolve()
    try:
        image_path.relative_to(result_root)
    except ValueError:
        return None, None

    if not is_accessible_output_file(image_path):
        return None, None
    return item, image_path


def sanitize_export_token(value: object, *, fallback: str, max_length: int) -> str:
    raw = str(value or "").strip().lower()
    normalized_chars: list[str] = []
    last_was_separator = False
    for char in raw:
        if char.isalnum():
            normalized_chars.append(char)
            last_was_separator = False
            continue
        if last_was_separator:
            continue
        normalized_chars.append("_")
        last_was_separator = True

    token = "".join(normalized_chars).strip("_")
    if not token:
        token = fallback
    return token[:max_length]


def count_export_store_files(
    *,
    export_root: Path,
    valid_upload_extensions: set[str] | frozenset[str],
) -> int:
    export_root.mkdir(parents=True, exist_ok=True)
    count = 0
    for candidate in export_root.iterdir():
        if candidate.is_file() and candidate.suffix.lower() in valid_upload_extensions:
            count += 1
    return count


def reserve_export_target_path(base_file_name: str, *, export_root: Path) -> Path:
    export_root.mkdir(parents=True, exist_ok=True)

    base_name = Path(base_file_name).name
    candidate = (export_root / base_name).resolve()
    try:
        candidate.relative_to(export_root)
    except ValueError:
        candidate = (export_root / f"export-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.png").resolve()

    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix or ".png"
    for index in range(2, 1000):
        next_candidate = (export_root / f"{stem}-{index:02d}{suffix}").resolve()
        if not next_candidate.exists():
            return next_candidate

    return (export_root / f"{stem}-{secrets.token_hex(3)}{suffix}").resolve()


def build_result_export_file_name(
    result_item: dict,
    *,
    sanitize_export_token: Callable[[object, str, int], str],
    valid_upload_extensions: set[str] | frozenset[str],
) -> str:
    mode_token = sanitize_export_token(result_item.get("mode"), "render", 20)
    result_token = sanitize_export_token(result_item.get("result_id"), "result", 24)
    extension = Path(str(result_item.get("file_name") or "")).suffix.lower()
    if extension not in valid_upload_extensions:
        extension = ".png"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"export-{timestamp}-{mode_token}-{result_token}{extension}"


def build_results_storage_summary(
    *,
    app_results_count: int,
    cleanup_report: dict | None,
    retention_limit: int,
    default_retention_limit: int,
    results_dir: str,
    exports_dir: str,
    exports_dir_access_state: Callable[[], tuple[bool, str | None]],
    count_export_store_files: Callable[[], int],
) -> dict:
    exports_dir_ok, exports_dir_error = exports_dir_access_state()
    export_count = count_export_store_files() if exports_dir_ok else 0
    cleanup_payload = cleanup_report if isinstance(cleanup_report, dict) else {}

    def cleanup_count(key: str) -> int:
        value = cleanup_payload.get(key)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, float) and value.is_integer():
            return max(0, int(value))
        return 0

    return {
        "results_scope": "app_results_managed",
        "results_dir": results_dir,
        "results_count": max(0, int(app_results_count)),
        "retention_limit": retention_limit if retention_limit >= 1 else default_retention_limit,
        "cleanup_scope": "results_only_managed",
        "stale_results_removed": cleanup_count("stale_results_removed"),
        "orphan_metadata_removed": cleanup_count("orphan_metadata_removed"),
        "orphan_images_removed": cleanup_count("orphan_images_removed"),
        "stale_temp_removed": cleanup_count("stale_temp_removed"),
        "exports_scope": "user_exports",
        "exports_dir": exports_dir,
        "exports_count": export_count,
        "exports_dir_accessible": exports_dir_ok,
        "exports_dir_error": exports_dir_error,
        "exports_protected": True,
    }


def create_result_export(
    result_id: str,
    *,
    results_dir_access_state: Callable[[], tuple[bool, str | None]],
    exports_dir_access_state: Callable[[], tuple[bool, str | None]],
    resolve_result_download_item: Callable[[str], tuple[dict | None, Path | None]],
    reserve_export_target_path: Callable[[str], Path],
    build_result_export_file_name: Callable[[dict], str],
    write_result_metadata: Callable[[Path, dict], None],
    export_url_builder: Callable[[Path], str],
    utc_now_iso: Callable[[], str],
) -> dict:
    normalized_result_id = str(result_id or "").strip()
    if not normalized_result_id or normalized_result_id in {".", ".."} or Path(normalized_result_id).name != normalized_result_id:
        raise ResultStoreError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_result_id",
            message="result_id is invalid.",
        )

    results_dir_ok, results_dir_error = results_dir_access_state()
    if not results_dir_ok:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker=results_dir_error or "results_dir_not_accessible",
            message="Results directory is not accessible.",
        )

    exports_dir_ok, exports_dir_error = exports_dir_access_state()
    if not exports_dir_ok:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker=exports_dir_error or "exports_dir_not_accessible",
            message="Export directory is not accessible.",
        )

    result_item, source_path = resolve_result_download_item(normalized_result_id)
    if result_item is None or source_path is None:
        raise ResultStoreError(
            status_code=HTTPStatus.NOT_FOUND,
            error_type="invalid_request",
            blocker="result_not_found",
            message="Result could not be found.",
        )

    target_path = reserve_export_target_path(build_result_export_file_name(result_item))
    temp_path = target_path.with_name(f".{target_path.name}.tmp")
    metadata_path = target_path.with_suffix(".json")
    exported_at = utc_now_iso()
    metadata_payload = {
        "created_at": exported_at,
        "source_result_id": normalized_result_id,
        "file_name": target_path.name,
        "source_file_name": result_item.get("file_name"),
        "mode": result_item.get("mode"),
        "checkpoint": result_item.get("checkpoint"),
        "store_scope": "user_exports",
        "cleanup_policy": "no_auto_cleanup",
    }

    try:
        shutil.copyfile(source_path, temp_path)
        temp_path.replace(target_path)
        write_result_metadata(metadata_path, metadata_payload)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        target_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker="export_storage_error",
            message="Result could not be exported.",
        ) from exc

    return {
        "result_id": normalized_result_id,
        "export_file_name": target_path.name,
        "export_url": export_url_builder(target_path),
        "exported_at": exported_at,
        "export_scope": "user_exports",
    }


def delete_stored_result(
    result_id: str,
    *,
    is_managed_result_id: Callable[[object], bool],
    results_dir_access_state: Callable[[], tuple[bool, str | None]],
    resolve_result_download_item: Callable[[str], tuple[dict | None, Path | None]],
    result_root: Path,
    list_result_store_records: Callable[[], list[dict]],
) -> dict:
    normalized_result_id = str(result_id or "").strip()
    if (
        not normalized_result_id
        or normalized_result_id in {".", ".."}
        or Path(normalized_result_id).name != normalized_result_id
        or not is_managed_result_id(normalized_result_id)
    ):
        raise ResultStoreError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_result_id",
            message="result_id is invalid.",
        )

    results_dir_ok, results_dir_error = results_dir_access_state()
    if not results_dir_ok:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker=results_dir_error or "results_dir_not_accessible",
            message="Results directory is not accessible.",
        )

    result_item, image_path = resolve_result_download_item(normalized_result_id)
    if result_item is None or image_path is None:
        raise ResultStoreError(
            status_code=HTTPStatus.NOT_FOUND,
            error_type="invalid_request",
            blocker="result_not_found",
            message="Result could not be found.",
        )

    store_scope = str(result_item.get("store_scope") or "").strip().lower() or "app_results"
    if store_scope != "app_results":
        raise ResultStoreError(
            status_code=HTTPStatus.FORBIDDEN,
            error_type="invalid_request",
            blocker="result_delete_forbidden_scope",
            message="Only app-managed results can be deleted.",
        )

    metadata_path = (result_root / f"{normalized_result_id}.json").resolve()
    try:
        metadata_path.relative_to(result_root)
    except ValueError as exc:
        raise ResultStoreError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_result_id",
            message="result_id is invalid.",
        ) from exc

    removed_files = 0
    for target_path in (metadata_path, image_path):
        try:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
                removed_files += 1
        except OSError as exc:
            raise ResultStoreError(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                error_type="api_error",
                blocker="result_delete_failed",
                message="Result could not be deleted.",
            ) from exc

    remaining_count = len(list_result_store_records())
    return {
        "result_id": normalized_result_id,
        "deleted": True,
        "deleted_files": removed_files,
        "remaining_results": remaining_count,
        "store_scope": "app_results",
    }


def finalize_generate_result(
    result: dict,
    request_id: str,
    *,
    prompt: str,
    checkpoint: str | None,
    use_input_image: bool,
    use_inpainting: bool,
    extra_metadata: dict | None,
    capture_generated_result: Callable[..., dict],
    build_generate_response: Callable[..., dict],
    build_error_response: Callable[..., dict],
) -> tuple[HTTPStatus, dict]:
    mode = result.get("mode")
    prompt_id = result.get("prompt_id")
    status = str(result.get("status"))

    if status != "ok":
        return HTTPStatus.BAD_REQUEST, build_generate_response(
            status=status,
            mode=mode,
            output_file=None,
            error_type=result.get("error_type"),
            blocker=result.get("blocker"),
            prompt_id=prompt_id,
            request_id=request_id,
        )

    try:
        stored_result = capture_generated_result(
            result.get("output_file"),
            render_mode=mode,
            prompt=prompt,
            checkpoint=checkpoint,
            use_input_image=use_input_image,
            use_inpainting=use_inpainting,
            extra_metadata=extra_metadata,
        )
    except ResultStoreError as exc:
        return exc.status_code, build_error_response(
            mode=mode,
            error_type=exc.error_type,
            blocker=exc.blocker,
            prompt_id=prompt_id,
            request_id=request_id,
        )

    response_payload = build_generate_response(
        status="ok",
        mode=mode,
        output_file=stored_result["preview_url"],
        error_type=None,
        blocker=None,
        prompt_id=prompt_id,
        request_id=request_id,
    )
    response_payload["result_id"] = stored_result["result_id"]
    response_payload["download_url"] = stored_result["download_url"]
    return HTTPStatus.OK, response_payload


def build_results_list_response(*, count: int, total_count: int, limit: int, items: list[dict], storage: dict) -> dict:
    return {
        "status": "ok",
        "count": count,
        "total_count": total_count,
        "limit": limit,
        "items": items,
        "storage": storage,
    }


def build_result_export_success_response(export_payload: dict) -> dict:
    return {
        "status": "ok",
        "ok": True,
        **export_payload,
    }


def build_result_delete_success_response(delete_payload: dict) -> dict:
    return {
        "status": "ok",
        "ok": True,
        **delete_payload,
    }
