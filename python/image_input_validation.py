from __future__ import annotations

from email.parser import BytesParser
from email.policy import default as email_policy_default
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


class UploadRequestError(Exception):
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


def normalize_optional_negative_prompt(value: object, *, max_length: int) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "negative_prompt_not_string"
    normalized_prompt = value.strip()
    if not normalized_prompt:
        return None, None
    if len(normalized_prompt) > max_length:
        return None, "negative_prompt_too_long"
    return normalized_prompt, None


def sanitize_original_name(filename: str | None) -> str:
    if not isinstance(filename, str):
        return "upload"
    normalized = Path(filename).name.replace("\x00", "").strip()
    return normalized or "upload"


def validate_multipart_content_type(content_type: str) -> None:
    if "multipart/form-data" not in str(content_type or "").lower():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )


def normalize_upload_source_type(value: str | None, *, valid_source_types: set[str] | frozenset[str]) -> str:
    normalized = str(value or "file").strip().lower()
    if normalized not in valid_source_types:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_source_type",
            message="Upload source_type must be file, clipboard, or mask.",
        )
    return normalized


def parse_multipart_image(
    content_type: str,
    body: bytes,
    *,
    source_type_normalizer,
) -> tuple[str, bytes, str]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    source_type = "file"
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "source_type":
                source_type = source_type_normalizer(part.get_content())
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if not file_parts:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_file",
            message="No upload file was provided.",
        )
    if len(file_parts) > 1:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one image file is supported.",
        )
    original_name, payload = file_parts[0]
    return original_name, payload, source_type


def parse_multipart_multi_reference_image(
    content_type: str,
    body: bytes,
    *,
    slot_index_parser,
) -> tuple[str, bytes, int | None]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    slot_index: int | None = None
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "slot_index":
                try:
                    slot_index = slot_index_parser(part.get_content())
                except ValueError as exc:
                    raise UploadRequestError(
                        status_code=HTTPStatus.BAD_REQUEST,
                        error_type="invalid_request",
                        blocker=str(exc),
                        message="slot_index must be auto, empty, or 1-3.",
                    ) from exc
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if not file_parts:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_file",
            message="No upload file was provided.",
        )
    if len(file_parts) > 1:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one image file is supported.",
        )

    original_name, payload = file_parts[0]
    return original_name, payload, slot_index


def parse_multipart_identity_transfer_role_image(
    content_type: str,
    body: bytes,
    *,
    role_parser,
) -> tuple[str, bytes, str]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    role: str | None = None
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "role":
                try:
                    role = role_parser(part.get_content())
                except ValueError as exc:
                    raise UploadRequestError(
                        status_code=HTTPStatus.BAD_REQUEST,
                        error_type="invalid_request",
                        blocker=str(exc),
                        message="role must be one of the supported V6.3.1 transfer roles.",
                    ) from exc
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if role is None:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_identity_transfer_role",
            message="role must be one of the supported V6.3.1 transfer roles.",
        )
    if not file_parts:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_file",
            message="No upload file was provided.",
        )
    if len(file_parts) > 1:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one image file is supported.",
        )

    original_name, payload = file_parts[0]
    return original_name, payload, role


def inspect_image_upload(
    original_name: str,
    payload: bytes,
    *,
    valid_extensions: set[str] | frozenset[str],
    upload_max_bytes: int,
    valid_formats: dict[str, tuple[str, str]],
) -> dict:
    sanitized_name = sanitize_original_name(original_name)
    original_extension = Path(sanitized_name).suffix.lower()
    if original_extension not in valid_extensions:
        raise UploadRequestError(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="invalid_file_type",
            message="Supported formats: .png .jpg .jpeg .webp",
        )
    if not payload:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_file",
            message="Uploaded file is empty.",
        )
    if len(payload) > upload_max_bytes:
        raise UploadRequestError(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            error_type="invalid_upload",
            blocker="file_too_large",
            message="Uploaded file exceeds the size limit.",
        )

    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="invalid_image_data",
            message="Uploaded payload is not a supported image.",
        ) from exc

    format_info = valid_formats.get(format_name)
    if format_info is None:
        raise UploadRequestError(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="invalid_file_type",
            message="Supported formats: .png .jpg .jpeg .webp",
        )

    extension, mime_type = format_info
    return {
        "original_name": sanitized_name,
        "extension": extension,
        "mime_type": mime_type,
        "size_bytes": len(payload),
        "width": int(width),
        "height": int(height),
    }


def normalize_mask_upload_payload(payload: bytes, *, mask_binary_threshold: int) -> tuple[bytes, dict]:
    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            grayscale = image.convert("L")
            binary_mask = grayscale.point(
                lambda pixel: 255 if int(pixel) >= mask_binary_threshold else 0,
                mode="L",
            )
            buffer = BytesIO()
            binary_mask.save(buffer, format="PNG")
            normalized_payload = buffer.getvalue()
            width, height = binary_mask.size
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="invalid_image_data",
            message="Uploaded payload is not a supported image.",
        ) from exc

    return normalized_payload, {
        "extension": ".png",
        "mime_type": "image/png",
        "size_bytes": len(normalized_payload),
        "width": int(width),
        "height": int(height),
    }


def validate_browser_mask_payload(
    payload: bytes,
    source_image_path: Path,
    *,
    mask_binary_threshold: int,
) -> None:
    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            grayscale = image.convert("L")
            binary_mask = grayscale.point(
                lambda pixel: 255 if int(pixel) >= mask_binary_threshold else 0,
                mode="L",
            )
            mask_size = binary_mask.size
            mask_bbox = binary_mask.getbbox()
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="invalid_image_data",
            message="Uploaded payload is not a supported image.",
        ) from exc

    try:
        with Image.open(source_image_path) as source_image:
            source_image.load()
            source_size = source_image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_input_image",
            message="Source image is not readable.",
        ) from exc

    if mask_size != source_size:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="mask_size_mismatch",
            message="Mask dimensions must match the current source image.",
        )

    if mask_bbox is None:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_mask",
            message="Mask contains no painted area.",
        )


def parse_required_identity_transfer_role(
    value: object,
    *,
    allowed_roles: set[str] | frozenset[str],
) -> str:
    normalized = str(value or "").strip()
    if normalized not in allowed_roles:
        raise ValueError("invalid_identity_transfer_role")
    return normalized


def parse_optional_multi_reference_slot_index(
    value: object,
    *,
    max_slots: int,
) -> int | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized or normalized == "auto":
        return None
    if not normalized.isdigit():
        raise ValueError("invalid_multi_reference_slot")
    parsed = int(normalized)
    if parsed < 1 or parsed > max_slots:
        raise ValueError("invalid_multi_reference_slot")
    return parsed


def parse_required_multi_reference_slot_index(
    value: object,
    *,
    max_slots: int,
) -> int:
    slot_index = parse_optional_multi_reference_slot_index(value, max_slots=max_slots)
    if slot_index is None:
        raise ValueError("invalid_multi_reference_slot")
    return slot_index
