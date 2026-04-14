from __future__ import annotations

from typing import Mapping


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _message_count(value: object) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    return count if count >= 0 else 0


def _messages(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _excerpt_text(value: str, *, limit: int) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 1)].rstrip()}..."


def build_text_chat_active_chat_payload(
    slot_index: int,
    slot_data: Mapping[str, object] | None,
    *,
    default_title: str,
    default_model_profile: str,
) -> dict:
    data = slot_data if isinstance(slot_data, Mapping) else {}
    occupied = bool(data.get("occupied") is True)
    messages = _messages(data.get("messages"))
    return {
        "slot_index": slot_index,
        "occupied": occupied,
        "title": _optional_text(data.get("title")) or default_title,
        "summary": _optional_text(data.get("summary")),
        "language": _optional_text(data.get("language")),
        "model_profile": _optional_text(data.get("model_profile")) or default_model_profile,
        "model": _optional_text(data.get("model")),
        "created_at": _optional_text(data.get("created_at")),
        "updated_at": _optional_text(data.get("updated_at")),
        "message_count": _message_count(data.get("message_count")),
        "messages": messages,
        "last_assistant_message": _optional_text(data.get("last_assistant_message")),
    }


def build_text_chat_slot_overview_payload(
    slot_index: int,
    slot_data: Mapping[str, object] | None,
    *,
    default_title: str,
    default_model_profile: str,
    preview_limit: int,
) -> dict:
    data = slot_data if isinstance(slot_data, Mapping) else {}
    preview = _optional_text(data.get("last_message_preview"))
    if preview is None:
        last_assistant_message = _optional_text(data.get("last_assistant_message"))
        preview = _excerpt_text(last_assistant_message or "", limit=preview_limit) if last_assistant_message else None
    return {
        "slot_index": slot_index,
        "occupied": bool(data.get("occupied") is True),
        "title": _optional_text(data.get("title")) or default_title,
        "summary": _optional_text(data.get("summary")),
        "language": _optional_text(data.get("language")),
        "model_profile": _optional_text(data.get("model_profile")) or default_model_profile,
        "model": _optional_text(data.get("model")),
        "created_at": _optional_text(data.get("created_at")),
        "updated_at": _optional_text(data.get("updated_at")),
        "message_count": _message_count(data.get("message_count")),
        "last_message_preview": preview,
    }


def build_text_chat_overview_payload(
    *,
    slot_count: int,
    active_slot_index: int,
    active_chat: Mapping[str, object] | None,
    slots: list[dict],
    profile_state: Mapping[str, object] | None,
) -> dict:
    profile_data = profile_state if isinstance(profile_state, Mapping) else {}
    profiles = profile_data.get("profiles")
    if not isinstance(profiles, list):
        profiles = []
    return {
        "status": "ok",
        "ok": True,
        "slot_count": slot_count,
        "active_slot_index": active_slot_index,
        "model_profiles": profiles,
        "current_model_profile_id": profile_data.get("current_profile_id"),
        "model_switch_state": profile_data.get("switch_state"),
        "slots": [slot for slot in slots if isinstance(slot, dict)],
        "active_chat": dict(active_chat) if isinstance(active_chat, Mapping) else {},
    }
