from __future__ import annotations

from typing import Callable

TEXT_CHAT_SLOT_ACTIONS = frozenset(
    {"activate", "rename", "clear", "replace", "profile", "message"}
)


def coerce_optional_text_chat_payload(payload: object) -> tuple[dict, str | None]:
    if payload is None:
        return {}, None
    if not isinstance(payload, dict):
        return {}, "invalid_json"
    return payload, None


def coerce_required_text_chat_payload(
    payload: object,
) -> tuple[dict | None, str | None]:
    if payload is None or not isinstance(payload, dict):
        return None, "invalid_json"
    return payload, None


def resolve_text_chat_slot_request_path(
    request_path: str,
    *,
    slots_path: str,
    slot_index_normalizer: Callable[[object], int],
) -> tuple[int, str | None] | None:
    prefix = f"{slots_path}/slot/"
    if not request_path.startswith(prefix):
        return None
    suffix = request_path[len(prefix) :].strip("/")
    if not suffix:
        return None
    parts = suffix.split("/")
    if len(parts) > 2:
        return None
    try:
        slot_index = slot_index_normalizer(parts[0])
    except ValueError:
        return None
    action = parts[1].strip().lower() if len(parts) == 2 and parts[1].strip() else None
    return slot_index, action


def normalize_text_chat_slot_action(action: object) -> str | None:
    if not isinstance(action, str):
        return None
    normalized = action.strip().lower()
    if normalized in TEXT_CHAT_SLOT_ACTIONS:
        return normalized
    return None


def normalize_create_text_chat_title(
    value: object,
    *,
    title_normalizer: Callable[[object], tuple[str | None, str | None]],
) -> tuple[str | None, str | None]:
    return title_normalizer(value)


def normalize_required_text_chat_title(
    value: object,
    *,
    title_normalizer: Callable[[object], tuple[str | None, str | None]],
) -> tuple[str | None, str | None]:
    title, title_error = title_normalizer(value)
    if title is None and title_error is None:
        return None, "invalid_text_chat_title"
    return title, title_error


def normalize_optional_text_chat_title(
    value: object,
    *,
    title_normalizer: Callable[[object], tuple[str | None, str | None]],
) -> tuple[str | None, str | None]:
    title, title_error = title_normalizer(value)
    if title_error == "empty_text_chat_title":
        return None, None
    return title, title_error
