from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Callable

from PIL import Image, UnidentifiedImageError

try:
    from python.image_input_validation import UploadRequestError
except ModuleNotFoundError:
    from image_input_validation import UploadRequestError


def build_upload_success_response(payload: dict) -> dict:
    return {
        "status": "ok",
        "ok": True,
        "image_id": payload["image_id"],
        "source_type": payload["source_type"],
        "original_name": payload["original_name"],
        "stored_name": payload["stored_name"],
        "mime_type": payload["mime_type"],
        "size_bytes": payload["size_bytes"],
        "width": payload["width"],
        "height": payload["height"],
        "preview_url": payload["preview_url"],
    }


def build_multi_reference_upload_success_response(payload: dict) -> dict:
    response_payload = build_upload_success_response(payload)
    response_payload["slot_index"] = payload["slot_index"]
    response_payload["created_at"] = payload.get("created_at")
    return response_payload


def build_identity_transfer_upload_success_response(payload: dict) -> dict:
    response_payload = build_upload_success_response(payload)
    response_payload["role"] = payload["role"]
    response_payload["created_at"] = payload.get("created_at")
    return response_payload


def input_metadata_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.json")


def write_input_metadata(path: Path, metadata: dict) -> None:
    metadata_path = input_metadata_path(path)
    temp_path = metadata_path.with_name(f"{metadata_path.name}.tmp")
    temp_path.write_text(json.dumps(metadata, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    temp_path.replace(metadata_path)


def read_input_metadata(path: Path) -> dict | None:
    metadata_path = input_metadata_path(path)
    if not metadata_path.exists() or not metadata_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _describe_stored_image(
    path: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    valid_upload_formats: dict[str, tuple[str, str]],
    metadata_reader: Callable[[Path], dict | None],
    preview_url: str,
    source_type: str,
    metadata_enricher: Callable[[dict], dict] | None = None,
) -> dict | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in valid_upload_extensions:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = valid_upload_formats.get(format_name)
    if format_info is None:
        return None

    _, mime_type = format_info
    metadata = metadata_reader(path) or {}
    original_name = str(metadata.get("original_name") or path.name).strip() or path.name
    payload = {
        "image_id": path.stem,
        "source_type": source_type,
        "original_name": original_name,
        "stored_name": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
        "width": int(width),
        "height": int(height),
        "preview_url": preview_url,
    }
    if metadata_enricher is not None:
        payload.update(metadata_enricher(metadata))
    return payload


def describe_stored_input_image(
    path: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    valid_upload_formats: dict[str, tuple[str, str]],
    valid_upload_source_types: set[str] | frozenset[str],
    preview_url_builder: Callable[[Path], str],
) -> dict | None:
    def enrich(metadata: dict) -> dict:
        source_type = str(metadata.get("source_type") or "file").strip().lower()
        if source_type not in valid_upload_source_types:
            source_type = "file"
        return {"source_type": source_type}

    return _describe_stored_image(
        path,
        valid_upload_extensions=valid_upload_extensions,
        valid_upload_formats=valid_upload_formats,
        metadata_reader=read_input_metadata,
        preview_url=preview_url_builder(path),
        source_type="file",
        metadata_enricher=enrich,
    )


def describe_stored_mask_image(
    path: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    valid_upload_formats: dict[str, tuple[str, str]],
    preview_url_builder: Callable[[Path], str],
) -> dict | None:
    return _describe_stored_image(
        path,
        valid_upload_extensions=valid_upload_extensions,
        valid_upload_formats=valid_upload_formats,
        metadata_reader=read_input_metadata,
        preview_url=preview_url_builder(path),
        source_type="mask",
    )


def describe_stored_reference_image(
    path: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    valid_upload_formats: dict[str, tuple[str, str]],
    preview_url_builder: Callable[[Path], str],
) -> dict | None:
    return _describe_stored_image(
        path,
        valid_upload_extensions=valid_upload_extensions,
        valid_upload_formats=valid_upload_formats,
        metadata_reader=read_input_metadata,
        preview_url=preview_url_builder(path),
        source_type="reference",
    )


def describe_stored_identity_transfer_role_image(
    path: Path,
    role: str,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    valid_upload_formats: dict[str, tuple[str, str]],
    preview_url_builder: Callable[[Path, str], str],
) -> dict | None:
    def enrich(metadata: dict) -> dict:
        created_at = str(metadata.get("created_at") or "").strip()
        return {
            "role": role,
            "created_at": created_at or None,
        }

    return _describe_stored_image(
        path,
        valid_upload_extensions=valid_upload_extensions,
        valid_upload_formats=valid_upload_formats,
        metadata_reader=read_input_metadata,
        preview_url=preview_url_builder(path, role),
        source_type="identity_transfer_role",
        metadata_enricher=enrich,
    )


def describe_stored_multi_reference_image(
    path: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    valid_upload_formats: dict[str, tuple[str, str]],
    preview_url_builder: Callable[[Path], str],
    required_slot_index_parser: Callable[[object], int],
) -> dict | None:
    def enrich(metadata: dict) -> dict:
        slot_index = required_slot_index_parser(metadata.get("slot_index"))
        created_at = str(metadata.get("created_at") or "").strip()
        return {
            "slot_index": slot_index,
            "created_at": created_at or None,
        }

    try:
        return _describe_stored_image(
            path,
            valid_upload_extensions=valid_upload_extensions,
            valid_upload_formats=valid_upload_formats,
            metadata_reader=read_input_metadata,
            preview_url=preview_url_builder(path),
            source_type="multi_reference",
            metadata_enricher=enrich,
        )
    except ValueError:
        return None


def _current_stored_image_state(
    root: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    describe_callback: Callable[[Path], dict | None],
) -> dict | None:
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in valid_upload_extensions
        )
    except OSError:
        return None

    for candidate in candidates:
        description = describe_callback(candidate)
        if description is not None:
            return description
    return None


def current_input_image_state(
    root: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    describe_callback: Callable[[Path], dict | None],
) -> dict | None:
    return _current_stored_image_state(
        root,
        valid_upload_extensions=valid_upload_extensions,
        describe_callback=describe_callback,
    )


def current_mask_image_state(
    root: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    describe_callback: Callable[[Path], dict | None],
) -> dict | None:
    return _current_stored_image_state(
        root,
        valid_upload_extensions=valid_upload_extensions,
        describe_callback=describe_callback,
    )


def current_reference_image_state(
    root: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    describe_callback: Callable[[Path], dict | None],
) -> dict | None:
    return _current_stored_image_state(
        root,
        valid_upload_extensions=valid_upload_extensions,
        describe_callback=describe_callback,
    )


def current_identity_transfer_role_state(
    root: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    describe_callback: Callable[[Path], dict | None],
) -> dict | None:
    return _current_stored_image_state(
        root,
        valid_upload_extensions=valid_upload_extensions,
        describe_callback=describe_callback,
    )


def list_stored_multi_reference_images(
    root: Path,
    *,
    valid_upload_extensions: set[str] | frozenset[str],
    describe_callback: Callable[[Path], dict | None],
) -> list[dict]:
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = [
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in valid_upload_extensions
        ]
    except OSError:
        return []

    grouped: dict[int, list[dict]] = {}
    for candidate in candidates:
        description = describe_callback(candidate)
        if description is None:
            continue
        grouped.setdefault(int(description["slot_index"]), []).append(description)

    items: list[dict] = []
    for slot_index in sorted(grouped):
        slot_items = grouped[slot_index]
        slot_items.sort(
            key=lambda item: (
                str(item.get("created_at") or ""),
                str(item.get("image_id") or ""),
            ),
            reverse=True,
        )
        items.append(slot_items[0])
    return items


def _store_file(
    *,
    final_path: Path,
    temp_path: Path,
    payload: bytes,
    metadata: dict,
    write_metadata: Callable[[Path, dict], None],
) -> None:
    temp_path.write_bytes(payload)
    temp_path.replace(final_path)
    write_metadata(final_path, metadata)


def store_uploaded_image(
    original_name: str,
    payload: bytes,
    source_type: str,
    *,
    normalize_source_type: Callable[[str | None], str],
    mask_root: Callable[[], Path],
    input_root: Callable[[], Path],
    mask_dir_access_state: Callable[[], tuple[bool, str | None]],
    input_dir_access_state: Callable[[], tuple[bool, str | None]],
    inspect_image_upload: Callable[[str, bytes], dict],
    normalize_mask_upload_payload: Callable[[bytes], tuple[bytes, dict]],
    clear_stored_mask_images: Callable[[], None],
    clear_stored_input_images: Callable[[], None],
    describe_stored_mask_image: Callable[[Path], dict | None],
    describe_stored_input_image: Callable[[Path], dict | None],
    is_accessible_output_file: Callable[[Path], bool],
) -> dict:
    normalized_source_type = normalize_source_type(source_type)
    is_mask_upload = normalized_source_type == "mask"
    root = mask_root() if is_mask_upload else input_root()
    dir_accessible, dir_error = (mask_dir_access_state() if is_mask_upload else input_dir_access_state())
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or ("mask_dir_not_accessible" if is_mask_upload else "input_dir_not_accessible"),
            message="Input directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    stored_payload = payload
    if is_mask_upload:
        normalized_payload, normalized_mask_info = normalize_mask_upload_payload(payload)
        stored_payload = normalized_payload
        image_info.update(normalized_mask_info)

    image_id = f"{'mask' if is_mask_upload else 'input'}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = root / stored_name
    temp_path = root / f".{stored_name}.tmp"

    try:
        if is_mask_upload:
            clear_stored_mask_images()
        else:
            clear_stored_input_images()
        _store_file(
            final_path=final_path,
            temp_path=temp_path,
            payload=stored_payload,
            metadata={
                "original_name": image_info["original_name"],
                "source_type": normalized_source_type,
            },
            write_metadata=write_input_metadata,
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="input_storage_error",
            message="Uploaded image could not be stored.",
        ) from exc

    stored_image = describe_stored_mask_image(final_path) if is_mask_upload else describe_stored_input_image(final_path)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_image_not_accessible",
            message="Stored image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = normalized_source_type
    return stored_image


def store_reference_image(
    original_name: str,
    payload: bytes,
    *,
    reference_root: Callable[[], Path],
    reference_dir_access_state: Callable[[], tuple[bool, str | None]],
    inspect_image_upload: Callable[[str, bytes], dict],
    clear_stored_reference_images: Callable[[], None],
    describe_stored_reference_image: Callable[[Path], dict | None],
    is_accessible_output_file: Callable[[Path], bool],
) -> dict:
    dir_accessible, dir_error = reference_dir_access_state()
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or "reference_dir_not_accessible",
            message="Reference directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    image_id = f"reference-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = reference_root() / stored_name
    temp_path = reference_root() / f".{stored_name}.tmp"

    try:
        clear_stored_reference_images()
        _store_file(
            final_path=final_path,
            temp_path=temp_path,
            payload=payload,
            metadata={
                "original_name": image_info["original_name"],
                "source_type": "reference",
            },
            write_metadata=write_input_metadata,
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="reference_storage_error",
            message="Uploaded reference image could not be stored.",
        ) from exc

    stored_image = describe_stored_reference_image(final_path)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_reference_not_accessible",
            message="Stored reference image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = "reference"
    return stored_image


def store_multi_reference_image(
    original_name: str,
    payload: bytes,
    *,
    slot_index: int | None,
    multi_reference_root: Callable[[], Path],
    multi_reference_dir_access_state: Callable[[], tuple[bool, str | None]],
    inspect_image_upload: Callable[[str, bytes], dict],
    find_first_free_multi_reference_slot: Callable[[], int | None],
    clear_stored_multi_reference_images: Callable[..., None],
    describe_stored_multi_reference_image: Callable[[Path], dict | None],
    is_accessible_output_file: Callable[[Path], bool],
    utc_now_iso: Callable[[], str],
) -> dict:
    dir_accessible, dir_error = multi_reference_dir_access_state()
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or "multi_reference_dir_not_accessible",
            message="Multi-reference directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    resolved_slot_index = slot_index if slot_index is not None else find_first_free_multi_reference_slot()
    if resolved_slot_index is None:
        raise UploadRequestError(
            status_code=HTTPStatus.CONFLICT,
            error_type="invalid_request",
            blocker="multi_reference_slots_full",
            message="All multi-reference slots are occupied. Choose a slot to replace.",
        )

    created_at = utc_now_iso()
    image_id = f"multi-reference-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = multi_reference_root() / stored_name
    temp_path = multi_reference_root() / f".{stored_name}.tmp"

    try:
        clear_stored_multi_reference_images(slot_index=resolved_slot_index)
        _store_file(
            final_path=final_path,
            temp_path=temp_path,
            payload=payload,
            metadata={
                "original_name": image_info["original_name"],
                "source_type": "multi_reference",
                "slot_index": resolved_slot_index,
                "created_at": created_at,
            },
            write_metadata=write_input_metadata,
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="multi_reference_storage_error",
            message="Uploaded multi-reference image could not be stored.",
        ) from exc

    stored_image = describe_stored_multi_reference_image(final_path)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_multi_reference_not_accessible",
            message="Stored multi-reference image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = "multi_reference"
    stored_image["slot_index"] = resolved_slot_index
    stored_image["created_at"] = created_at
    return stored_image


def store_identity_transfer_role_image(
    original_name: str,
    payload: bytes,
    *,
    role: str,
    identity_transfer_role_root: Callable[[str], Path],
    identity_transfer_dir_access_state: Callable[[str], tuple[bool, str | None]],
    inspect_image_upload: Callable[[str, bytes], dict],
    clear_stored_identity_transfer_role_images: Callable[[str], None],
    describe_stored_identity_transfer_role_image: Callable[[Path, str], dict | None],
    is_accessible_output_file: Callable[[Path], bool],
    utc_now_iso: Callable[[], str],
) -> dict:
    dir_accessible, dir_error = identity_transfer_dir_access_state(role)
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or "identity_transfer_role_dir_not_accessible",
            message="Identity transfer role directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    created_at = utc_now_iso()
    image_id = f"{role}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = identity_transfer_role_root(role) / stored_name
    temp_path = identity_transfer_role_root(role) / f".{stored_name}.tmp"

    try:
        clear_stored_identity_transfer_role_images(role)
        _store_file(
            final_path=final_path,
            temp_path=temp_path,
            payload=payload,
            metadata={
                "original_name": image_info["original_name"],
                "source_type": "identity_transfer_role",
                "role": role,
                "created_at": created_at,
            },
            write_metadata=write_input_metadata,
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="identity_transfer_role_storage_error",
            message="Uploaded identity transfer role image could not be stored.",
        ) from exc

    stored_image = describe_stored_identity_transfer_role_image(final_path, role)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_identity_transfer_role_not_accessible",
            message="Stored identity transfer role image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = "identity_transfer_role"
    stored_image["role"] = role
    stored_image["created_at"] = created_at
    return stored_image
