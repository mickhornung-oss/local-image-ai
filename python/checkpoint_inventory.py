import json
from pathlib import Path
from typing import Any


CHECKPOINT_EXTENSIONS = {".safetensors", ".ckpt"}
DEFAULT_PRODUCT_CHECKPOINT_NAME = "sdxl-base.safetensors"
PHOTO_STANDARD_MODE = "photo_standard"
ANIME_STANDARD_MODE = "anime_standard"
STANDARD_CHECKPOINT_MODES = {
    PHOTO_STANDARD_MODE: "RealVisXL_V5.0_fp16.safetensors",
    ANIME_STANDARD_MODE: "animagine-xl-4.0-opt.safetensors",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def checkpoint_dir() -> Path:
    return repo_root() / "vendor" / "ComfyUI" / "models" / "checkpoints"


def normalize_repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def is_sdxl_candidate_name(name: str) -> bool:
    lowered = name.lower()
    return "sdxl" in lowered or "xl" in lowered


def find_checkpoint_by_name(paths: list[Path], checkpoint_name: str) -> Path | None:
    lookup = checkpoint_name.strip().lower()
    for path in paths:
        if path.name.lower() == lookup:
            return path
    return None


def list_checkpoint_files(*, include_invalid: bool = False) -> list[Path]:
    root = checkpoint_dir()
    if not root.exists():
        return []

    paths = [
        path.resolve()
        for path in root.iterdir()
        if path.is_file() and (include_invalid or path.suffix.lower() in CHECKPOINT_EXTENSIONS)
    ]
    return sorted(paths, key=lambda item: (item.name.lower(), item.name))


def build_candidate(path: Path) -> dict[str, Any]:
    exists = path.exists() and path.is_file()
    return {
        "name": path.name,
        "relative_path": normalize_repo_relative(path),
        "exists": exists,
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size if exists else 0,
        "is_sdxl_candidate": is_sdxl_candidate_name(path.name),
    }


def select_checkpoint_path(paths: list[Path]) -> Path | None:
    if not paths:
        return None

    for path in paths:
        if path.name.lower() == DEFAULT_PRODUCT_CHECKPOINT_NAME:
            return path

    preferred = [path for path in paths if is_sdxl_candidate_name(path.name)]
    return preferred[0] if preferred else paths[0]


def build_standard_checkpoint_modes(paths: list[Path]) -> dict[str, dict[str, Any]]:
    modes: dict[str, dict[str, Any]] = {}
    for mode_name, checkpoint_name in STANDARD_CHECKPOINT_MODES.items():
        matched = find_checkpoint_by_name(paths, checkpoint_name)
        fallback_path = checkpoint_dir() / checkpoint_name
        path = matched if matched is not None else fallback_path
        modes[mode_name] = {
            "mode": mode_name,
            "checkpoint": checkpoint_name,
            "available": matched is not None,
            "relative_path": normalize_repo_relative(path),
        }
    return modes


def build_checkpoint_inventory() -> dict[str, Any]:
    paths = list_checkpoint_files()
    candidates = [build_candidate(path) for path in paths]
    selected = select_checkpoint_path(paths)
    return {
        "status": "ok",
        "count": len(candidates),
        "sdxl_count": sum(1 for candidate in candidates if candidate["is_sdxl_candidate"]),
        "selected": selected.name if selected else None,
        "fallback_checkpoint": DEFAULT_PRODUCT_CHECKPOINT_NAME,
        "standard_modes": build_standard_checkpoint_modes(paths),
        "candidates": candidates,
    }


def resolve_requested_checkpoint(name: str | None) -> Path | None:
    if name is None:
        return select_checkpoint_path(list_checkpoint_files())

    requested_text = str(name).strip()
    if not requested_text:
        return select_checkpoint_path(list_checkpoint_files())

    requested_mode = STANDARD_CHECKPOINT_MODES.get(requested_text.lower())
    if requested_mode:
        name = requested_mode

    requested = Path(name)
    root = checkpoint_dir()
    direct_candidates: list[Path] = []
    if requested.is_absolute():
        direct_candidates.append(requested)
    else:
        direct_candidates.append(root / requested)
        direct_candidates.append(repo_root() / requested)

    for candidate in direct_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    requested_key = str(requested).replace("\\", "/").lower()
    requested_name = requested.name.lower()
    for path in list_checkpoint_files(include_invalid=True):
        if path.name.lower() == requested_name:
            return path
        if normalize_repo_relative(path).lower() == requested_key:
            return path

    if requested.is_absolute():
        return requested.resolve()
    return (root / requested.name).resolve()


def main() -> int:
    try:
        payload = build_checkpoint_inventory()
        print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
        return 0
    except OSError as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}, ensure_ascii=True, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
