from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def _normalized_slot_index(value: object) -> int | None:
    try:
        slot_index = int(value)
    except (TypeError, ValueError):
        return None
    return slot_index if slot_index >= 1 else None


def build_multi_reference_status_payload(
    items: list[dict] | None,
    *,
    max_slots: int,
) -> dict:
    normalized_items = [item for item in (items or []) if isinstance(item, dict)]
    item_by_slot: dict[int, dict] = {}
    for item in normalized_items:
        slot_index = _normalized_slot_index(item.get("slot_index"))
        if slot_index is None:
            continue
        item_by_slot[slot_index] = item

    slots: list[dict] = []
    for slot_index in range(1, max_slots + 1):
        current_item = item_by_slot.get(slot_index)
        slots.append(
            {
                "slot_index": slot_index,
                "occupied": current_item is not None,
                "image": current_item,
            }
        )

    reference_count = len(item_by_slot)
    return {
        "status": "ok",
        "max_slots": max_slots,
        "reference_count": reference_count,
        "multi_reference_ready": reference_count >= 2,
        "slots": slots,
    }


def find_first_free_multi_reference_slot(
    status_payload: Mapping[str, object] | None,
) -> int | None:
    payload = status_payload if isinstance(status_payload, Mapping) else {}
    slots = payload.get("slots")
    if not isinstance(slots, list):
        return None
    for slot in slots:
        if not isinstance(slot, Mapping):
            continue
        if slot.get("occupied") is True:
            continue
        slot_index = _normalized_slot_index(slot.get("slot_index"))
        if slot_index is not None:
            return slot_index
    return None


def resolve_multi_reference_readiness_http_status(
    readiness_state: Mapping[str, object] | None,
    *,
    status_code_resolver: Callable[..., HTTPStatus],
) -> HTTPStatus:
    state = readiness_state if isinstance(readiness_state, Mapping) else {}
    if state.get("ok") is True:
        return HTTPStatus.OK
    error_type = (
        state.get("error_type") if isinstance(state.get("error_type"), str) else None
    )
    blocker = state.get("blocker") if isinstance(state.get("blocker"), str) else None
    return status_code_resolver(error_type=error_type, blocker=blocker)
