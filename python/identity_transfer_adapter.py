import json
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


IDENTITY_TRANSFER_ROLES = (
    "identity_head_reference",
    "target_body_image",
    "pose_reference",
    "transfer_mask",
)
IDENTITY_TRANSFER_REQUIRED_ROLES = (
    "identity_head_reference",
    "target_body_image",
)
IDENTITY_TRANSFER_OPTIONAL_ROLES = tuple(
    role for role in IDENTITY_TRANSFER_ROLES if role not in IDENTITY_TRANSFER_REQUIRED_ROLES
)
VALID_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VALID_UPLOAD_FORMATS = {
    "PNG": ("image/png", ".png"),
    "JPEG": ("image/jpeg", ".jpg"),
    "WEBP": ("image/webp", ".webp"),
}
IDENTITY_TRANSFER_STAGING_SUBFOLDER = "identity_transfer_roles"
READINESS_ONLY_BLOCKERS = {
    "missing_identity_head_reference",
    "missing_target_body_image",
}
BLOCKER_ERROR_MESSAGES = {
    "identity_transfer_store_unavailable": "The V6.3.1 role store is not accessible.",
    "missing_identity_head_reference": "The required identity_head_reference image is missing.",
    "missing_target_body_image": "The required target_body_image image is missing.",
    "missing_identity_transfer_file": "A stored V6.3.1 role points to a missing image file.",
    "invalid_identity_transfer_metadata": "Stored V6.3.1 role metadata is incomplete or inconsistent.",
    "invalid_identity_transfer_image": "A stored V6.3.1 role does not contain a valid image.",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def identity_transfer_root(*, root_override: Path | None = None) -> Path:
    return root_override.resolve() if root_override is not None else (repo_root() / "data" / "identity_transfer_roles").resolve()


def identity_transfer_role_root(role: str, *, root_override: Path | None = None) -> Path:
    return (identity_transfer_root(root_override=root_override) / role).resolve()


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


def inspect_transfer_image(path: Path) -> dict[str, Any] | None:
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


def build_role_record(image_path: Path, metadata: dict, role: str) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    image_info = inspect_transfer_image(image_path)
    if image_info is None:
        return None, ["invalid_identity_transfer_image"]

    source_type = str(metadata.get("source_type") or "").strip().lower()
    if source_type != "identity_transfer_role":
        blockers.append("invalid_identity_transfer_metadata")

    metadata_role = str(metadata.get("role") or "").strip()
    if metadata_role != role:
        blockers.append("invalid_identity_transfer_metadata")

    image_id = image_path.stem.strip()
    if not image_id:
        blockers.append("invalid_identity_transfer_metadata")

    if blockers:
        return None, sorted(set(blockers))

    created_at = str(metadata.get("created_at") or "").strip() or None
    return {
        "role": role,
        "image_id": image_id,
        "path": str(image_path.resolve()),
        "stored_name": image_path.name,
        "mime_type": image_info["mime_type"],
        "width": image_info["width"],
        "height": image_info["height"],
        "size_bytes": image_info["size_bytes"],
        "created_at": created_at,
        "preview_url": f"/identity-transfer/{role}/{image_path.name}",
    }, []


def build_staging_plan(roles: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for role in IDENTITY_TRANSFER_ROLES:
        record = roles.get(role)
        if not isinstance(record, dict):
            continue
        source_path = Path(record["path"])
        target_name = f"{role}__{record['image_id']}{source_path.suffix.lower()}"
        entries.append(
            {
                "role": role,
                "source_path": str(source_path),
                "target_name": target_name,
                "target_subfolder": IDENTITY_TRANSFER_STAGING_SUBFOLDER,
            }
        )

    return {
        "target_subfolder": IDENTITY_TRANSFER_STAGING_SUBFOLDER,
        "entries": entries,
    }


def derive_error_state(blockers: list[str]) -> tuple[str, str | None, str | None]:
    if not blockers:
        return "ok", None, None

    prioritized_blockers = [
        "identity_transfer_store_unavailable",
        "missing_identity_transfer_file",
        "invalid_identity_transfer_metadata",
        "invalid_identity_transfer_image",
        "missing_identity_head_reference",
        "missing_target_body_image",
    ]
    selected_blocker = next((blocker for blocker in prioritized_blockers if blocker in blockers), blockers[0])
    status = "ok" if set(blockers).issubset(READINESS_ONLY_BLOCKERS) else "error"
    return status, selected_blocker, BLOCKER_ERROR_MESSAGES.get(selected_blocker)


def build_identity_transfer_adapter_state(*, root_override: Path | None = None) -> dict[str, Any]:
    root = identity_transfer_root(root_override=root_override)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {
            "status": "error",
            "ready": False,
            "roles": {role: None for role in IDENTITY_TRANSFER_ROLES},
            "required_roles_present": {role: False for role in IDENTITY_TRANSFER_REQUIRED_ROLES},
            "optional_roles_present": {role: False for role in IDENTITY_TRANSFER_OPTIONAL_ROLES},
            "occupied_role_count": 0,
            "ordered_roles": [],
            "blockers": ["identity_transfer_store_unavailable"],
            "staging_plan": build_staging_plan({}),
            "error_type": "identity_transfer_store_unavailable",
            "error_message": str(exc),
        }

    blockers: list[str] = []
    roles: dict[str, dict[str, Any] | None] = {}
    ordered_roles: list[dict[str, Any]] = []
    occupied_role_count = 0

    for role in IDENTITY_TRANSFER_ROLES:
        role_root = identity_transfer_role_root(role, root_override=root)
        role_blockers: list[str] = []
        try:
            role_root.mkdir(parents=True, exist_ok=True)
            image_paths = sorted(
                path for path in role_root.iterdir()
                if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS
            )
            metadata_paths = sorted(
                path for path in role_root.iterdir()
                if path.is_file() and path.suffix.lower() == ".json"
            )
        except OSError:
            blockers.append("identity_transfer_store_unavailable")
            ordered_roles.append(
                {
                    "role": role,
                    "required": role in IDENTITY_TRANSFER_REQUIRED_ROLES,
                    "occupied": False,
                    "image": None,
                    "blockers": ["identity_transfer_store_unavailable"],
                }
            )
            roles[role] = None
            continue

        for metadata_path in metadata_paths:
            image_path = image_path_for_metadata(metadata_path)
            if not image_path.exists() or not image_path.is_file():
                role_blockers.append("missing_identity_transfer_file")

        current_role_record: dict[str, Any] | None = None
        if len(image_paths) > 1:
            role_blockers.append("invalid_identity_transfer_metadata")
        elif len(image_paths) == 1:
            image_path = image_paths[0]
            metadata = read_json_file(metadata_path_for_image(image_path))
            if metadata is None:
                role_blockers.append("invalid_identity_transfer_metadata")
            else:
                role_record, record_blockers = build_role_record(image_path, metadata, role)
                if role_record is None:
                    role_blockers.extend(record_blockers)
                else:
                    current_role_record = role_record

        if current_role_record is None and role in IDENTITY_TRANSFER_REQUIRED_ROLES:
            role_blockers.append(f"missing_{role}")

        role_blockers = sorted(set(role_blockers))
        blockers.extend(role_blockers)
        if current_role_record is not None:
            occupied_role_count += 1
        roles[role] = current_role_record
        ordered_roles.append(
            {
                "role": role,
                "required": role in IDENTITY_TRANSFER_REQUIRED_ROLES,
                "occupied": current_role_record is not None,
                "image": current_role_record,
                "blockers": role_blockers,
            }
        )

    required_roles_present = {
        role: isinstance(roles.get(role), dict) for role in IDENTITY_TRANSFER_REQUIRED_ROLES
    }
    optional_roles_present = {
        role: isinstance(roles.get(role), dict) for role in IDENTITY_TRANSFER_OPTIONAL_ROLES
    }
    blockers = sorted(set(blockers))
    status, error_type, error_message = derive_error_state(blockers)
    return {
        "status": status,
        "ready": not blockers,
        "roles": roles,
        "required_roles": list(IDENTITY_TRANSFER_REQUIRED_ROLES),
        "optional_roles": list(IDENTITY_TRANSFER_OPTIONAL_ROLES),
        "required_roles_present": required_roles_present,
        "optional_roles_present": optional_roles_present,
        "occupied_role_count": occupied_role_count,
        "ordered_roles": ordered_roles,
        "blockers": blockers,
        "staging_plan": build_staging_plan(roles),
        "error_type": error_type,
        "error_message": error_message,
    }
