from __future__ import annotations

import base64
import binascii
import json
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs


def read_json_file_detail(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, "missing"

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None, "invalid_json"
    except OSError:
        return None, "read_failed"

    if not isinstance(payload, dict):
        return None, "invalid_payload"
    return payload, None


def parse_results_limit(
    query_string: str, *, default_limit: int, max_limit: int
) -> int:
    parsed = parse_qs(str(query_string or "").lstrip("?"), keep_blank_values=False)
    raw_value = parsed.get("limit", [str(default_limit)])[0]
    try:
        numeric_value = int(str(raw_value).strip())
    except ValueError as exc:
        raise ValueError("invalid_results_limit") from exc

    if numeric_value <= 0:
        raise ValueError("invalid_results_limit")
    return min(max_limit, numeric_value)


def decode_data_url_image(
    data_url: object,
    *,
    valid_upload_mime_types: set[str],
    upload_error_cls,
) -> tuple[str, bytes]:
    if not isinstance(data_url, str) or not data_url.strip():
        raise upload_error_cls(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_mask_data",
            message="Mask data is missing.",
        )

    raw_value = data_url.strip()
    if "," not in raw_value:
        raise upload_error_cls(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mask_data",
            message="Mask data URL is invalid.",
        )

    header, encoded = raw_value.split(",", 1)
    if not header.lower().startswith("data:") or ";base64" not in header.lower():
        raise upload_error_cls(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mask_data",
            message="Mask data URL is invalid.",
        )

    mime_type = header[5:].split(";", 1)[0].strip().lower()
    if mime_type not in valid_upload_mime_types:
        raise upload_error_cls(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="invalid_file_type",
            message="Supported formats: .png .jpg .jpeg .webp",
        )

    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise upload_error_cls(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mask_data",
            message="Mask data URL is invalid.",
        ) from exc

    if not payload:
        raise upload_error_cls(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_mask_data",
            message="Mask payload is empty.",
        )

    return mime_type, payload


def validate_mode(value: object, *, valid_modes: set[str]) -> str:
    normalized = str(value if value is not None else "auto").strip().lower()
    if normalized not in valid_modes:
        raise ValueError("invalid_mode")
    return normalized


def parse_boolean_flag(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    raise ValueError("invalid_use_input_image")
