from __future__ import annotations

from typing import Mapping


def _profile_list(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def build_text_chat_slot_detail_response(
    *,
    slot: Mapping[str, object] | None,
    profile_state: Mapping[str, object] | None,
) -> dict:
    profile_data = profile_state if isinstance(profile_state, Mapping) else {}
    return {
        "status": "ok",
        "ok": True,
        "slot": dict(slot) if isinstance(slot, Mapping) else {},
        "model_profiles": _profile_list(profile_data.get("profiles")),
        "current_model_profile_id": profile_data.get("current_profile_id"),
        "model_switch_state": profile_data.get("switch_state"),
    }
