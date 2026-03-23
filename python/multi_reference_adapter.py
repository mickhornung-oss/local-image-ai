import json
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


MAX_MULTI_REFERENCE_SLOTS = 3
MIN_MULTI_REFERENCE_READY_COUNT = 2
VALID_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VALID_UPLOAD_FORMATS = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}
MULTI_REFERENCE_STAGING_SUBFOLDER = "identity_multi_reference"
READINESS_ONLY_BLOCKERS = {"insufficient_multi_reference_images"}
BLOCKER_ERROR_MESSAGES = {
    "multi_reference_store_unavailable": "Multi-reference store is unavailable.",
    "missing_multi_reference_file": "A stored multi-reference slot points to a missing image file.",
    "invalid_multi_reference_metadata": "Multi-reference metadata is incomplete or inconsistent.",
    "invalid_multi_reference_image": "A stored multi-reference slot does not contain a valid image.",
    "duplicate_multi_reference_slot": "Multiple stored multi-reference images claim the same slot.",
    "insufficient_multi_reference_images": "At least 2 multi-reference images are required.",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def multi_reference_root() -> Path:
    return (repo_root() / "data" / "multi_reference_images").resolve()


def metadata_path_for_image(path: Path) -> Path:
    return path.with_name(f"{path.name}.json")


def image_path_for_metadata(path: Path) -> Path:
    suffix = "".join(path.suffixes)
    if suffix.lower().endswith(".json"):
        return path.with_name(path.name[:-5])
    return path


def read_json_file(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def normalize_slot_index(value: object) -> int | None:
    normalized = str(value if value is not None else "").strip()
    if not normalized or not normalized.isdigit():
        return None
    parsed = int(normalized)
    if parsed < 1 or parsed > MAX_MULTI_REFERENCE_SLOTS:
        return None
    return parsed


def inspect_reference_image(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        return None

    mime_type, extension = format_info
    return {
        "mime_type": mime_type,
        "extension": extension,
        "width": int(width),
        "height": int(height),
        "size_bytes": path.stat().st_size,
    }


def build_reference_record(image_path: Path, metadata: dict) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    image_info = inspect_reference_image(image_path)
    if image_info is None:
        return None, ["invalid_multi_reference_image"]

    slot_index = normalize_slot_index(metadata.get("slot_index"))
    if slot_index is None:
        blockers.append("invalid_multi_reference_metadata")
    source_type = str(metadata.get("source_type") or "").strip().lower()
    if source_type != "multi_reference":
        blockers.append("invalid_multi_reference_metadata")

    if blockers:
        return None, sorted(set(blockers))

    image_id = image_path.stem.strip()
    if not image_id:
        return None, ["invalid_multi_reference_metadata"]

    created_at = str(metadata.get("created_at") or "").strip() or None
    return {
        "slot_index": slot_index,
        "image_id": image_id,
        "path": str(image_path.resolve()),
        "stored_name": image_path.name,
        "mime_type": image_info["mime_type"],
        "width": image_info["width"],
        "height": image_info["height"],
        "size_bytes": image_info["size_bytes"],
        "created_at": created_at,
        "preview_url": f"/multi-reference/{image_path.name}",
    }, []


def choose_primary_reference(references: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not references:
        return None
    for reference in references:
        if int(reference["slot_index"]) == 1:
            return reference
    return references[0]


def build_staging_plan(references: list[dict[str, Any]], primary_reference: dict[str, Any] | None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for reference in references:
        source_path = Path(reference["path"])
        target_name = f"slot_{int(reference['slot_index'])}_{reference['image_id']}{source_path.suffix.lower()}"
        entries.append(
            {
                "slot_index": int(reference["slot_index"]),
                "source_path": str(source_path),
                "target_name": target_name,
                "target_subfolder": MULTI_REFERENCE_STAGING_SUBFOLDER,
            }
        )

    primary_target_name = None
    if primary_reference is not None:
        primary_source_path = Path(primary_reference["path"])
        primary_target_name = f"slot_{int(primary_reference['slot_index'])}_{primary_reference['image_id']}{primary_source_path.suffix.lower()}"

    return {
        "target_subfolder": MULTI_REFERENCE_STAGING_SUBFOLDER,
        "entries": entries,
        "primary_target_name": primary_target_name,
    }


def derive_error_state(blockers: list[str]) -> tuple[str, str | None, str | None]:
    if not blockers:
        return "ok", None, None

    prioritized_blockers = [
        "multi_reference_store_unavailable",
        "missing_multi_reference_file",
        "invalid_multi_reference_metadata",
        "invalid_multi_reference_image",
        "duplicate_multi_reference_slot",
        "insufficient_multi_reference_images",
    ]
    selected_blocker = next((blocker for blocker in prioritized_blockers if blocker in blockers), blockers[0])
    status = "ok" if set(blockers).issubset(READINESS_ONLY_BLOCKERS) else "error"
    return status, selected_blocker, BLOCKER_ERROR_MESSAGES.get(selected_blocker)


def build_multi_reference_adapter_state(*, root_override: Path | None = None) -> dict[str, Any]:
    root = root_override.resolve() if root_override is not None else multi_reference_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {
            "status": "error",
            "ready": False,
            "reference_count": 0,
            "required_reference_count": MIN_MULTI_REFERENCE_READY_COUNT,
            "references": [],
            "primary_reference": None,
            "blockers": ["multi_reference_store_unavailable"],
            "slot_summary": [],
            "staging_plan": build_staging_plan([], None),
            "error_type": "api_error",
            "error_message": str(exc),
        }

    metadata_paths = sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() == ".json")
    image_paths = sorted(path for path in root.iterdir() if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS)

    blockers: list[str] = []
    references: list[dict[str, Any]] = []
    slot_images: dict[int, dict[str, Any]] = {}
    slot_errors: dict[int, list[str]] = {slot_index: [] for slot_index in range(1, MAX_MULTI_REFERENCE_SLOTS + 1)}

    for metadata_path in metadata_paths:
        image_path = image_path_for_metadata(metadata_path)
        metadata = read_json_file(metadata_path)
        slot_index = normalize_slot_index(metadata.get("slot_index")) if metadata is not None else None
        if metadata is None:
            blockers.append("invalid_multi_reference_metadata")
            continue
        if not image_path.exists() or not image_path.is_file():
            blockers.append("missing_multi_reference_file")
            if slot_index is not None:
                slot_errors.setdefault(slot_index, []).append("missing_multi_reference_file")

    for image_path in image_paths:
        metadata = read_json_file(metadata_path_for_image(image_path))
        if metadata is None:
            blockers.append("invalid_multi_reference_metadata")
            continue

        reference_record, record_blockers = build_reference_record(image_path, metadata)
        if reference_record is None:
            blockers.extend(record_blockers)
            slot_index = normalize_slot_index(metadata.get("slot_index"))
            if slot_index is not None:
                slot_errors.setdefault(slot_index, []).extend(record_blockers)
            continue

        slot_index = int(reference_record["slot_index"])
        if slot_index in slot_images:
            blockers.append("duplicate_multi_reference_slot")
            slot_errors.setdefault(slot_index, []).append("duplicate_multi_reference_slot")
            continue

        references.append(reference_record)
        slot_images[slot_index] = reference_record

    references.sort(key=lambda item: int(item["slot_index"]))
    primary_reference = choose_primary_reference(references)

    if len(references) < MIN_MULTI_REFERENCE_READY_COUNT:
        blockers.append("insufficient_multi_reference_images")

    slot_summary: list[dict[str, Any]] = []
    for slot_index in range(1, MAX_MULTI_REFERENCE_SLOTS + 1):
        slot_image = slot_images.get(slot_index)
        slot_blockers = sorted(set(slot_errors.get(slot_index, [])))
        slot_summary.append(
            {
                "slot_index": slot_index,
                "occupied": slot_image is not None,
                "image": slot_image,
                "blockers": slot_blockers,
            }
        )

    blockers = sorted(set(blockers))
    status, error_type, error_message = derive_error_state(blockers)
    return {
        "status": status,
        "ready": not blockers,
        "reference_count": len(references),
        "required_reference_count": MIN_MULTI_REFERENCE_READY_COUNT,
        "references": references,
        "primary_reference": primary_reference,
        "blockers": blockers,
        "slot_summary": slot_summary,
        "staging_plan": build_staging_plan(references, primary_reference),
        "error_type": error_type,
        "error_message": error_message,
    }
