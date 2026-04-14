from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def resolve_text_chat_profile_id(slot: Mapping[str, object] | None, *, default_profile_id: str) -> str:
    if isinstance(slot, Mapping):
        profile_id = _optional_text(slot.get("model_profile"))
        if profile_id:
            return profile_id
    return default_profile_id


def build_text_chat_recent_messages(messages: object, *, limit: int) -> list[dict]:
    if not isinstance(messages, list):
        return []
    recent_messages = messages[-limit:] if limit > 0 else []
    return [
        {
            "role": str(message.get("role") or ""),
            "content": str(message.get("content") or ""),
        }
        for message in recent_messages
        if isinstance(message, Mapping)
    ]


def prepare_text_chat_service_request(
    *,
    slot: Mapping[str, object] | None,
    prompt: str,
    requested_title: str | None,
    default_title: str,
    default_profile_id: str,
    recent_messages_limit: int,
    infer_language: Callable[[str], str],
    compose_prompt: Callable[..., str],
) -> dict:
    slot_data = slot if isinstance(slot, Mapping) else {}
    recent_messages = build_text_chat_recent_messages(
        slot_data.get("messages"),
        limit=recent_messages_limit,
    )
    summary = _optional_text(slot_data.get("summary"))
    return {
        "current_title": requested_title or _optional_text(slot_data.get("title")) or default_title,
        "inferred_language": infer_language(prompt),
        "profile_id": resolve_text_chat_profile_id(slot_data, default_profile_id=default_profile_id),
        "recent_messages": recent_messages,
        "summary": summary,
        "composed_prompt": compose_prompt(
            prompt,
            summary=summary,
            recent_messages=recent_messages,
        ),
    }


def execute_text_chat_service_request(
    *,
    request_callable: Callable[..., tuple[object, object, object, object, object]],
    retry_predicate: Callable[..., bool],
    sleep_callable: Callable[[float], None],
    switch_result: Mapping[str, object] | None,
    composed_prompt: str,
    mode: str | None,
    summary: str | None,
    recent_messages: list[dict],
) -> dict:
    response_payload, response_error, response_status, service_name, model_status = request_callable(
        composed_prompt,
        mode=mode,
        summary=summary,
        recent_messages=recent_messages,
    )
    if retry_predicate(
        switch_result=switch_result,
        response_error=response_error,
        response_status=response_status,
    ):
        sleep_callable(5.0)
        response_payload, response_error, response_status, service_name, model_status = request_callable(
            composed_prompt,
            mode=mode,
            summary=summary,
            recent_messages=recent_messages,
        )
    return {
        "response_payload": response_payload,
        "response_error": response_error,
        "response_status": response_status,
        "service_name": service_name,
        "model_status": model_status,
    }


def normalize_text_chat_service_result(
    *,
    response_payload: object,
    response_error: object,
    response_status: object,
    service_name: object,
    model_status: object,
) -> dict:
    if response_error is not None or response_status is None:
        blocker = "text_service_unreachable" if response_error in {"unreachable", "timeout"} else "text_service_invalid_response"
        return {
            "ok": False,
            "http_status": HTTPStatus.SERVICE_UNAVAILABLE,
            "blocker": blocker,
            "message": "Text-KI ist aktuell nicht erreichbar.",
        }

    if response_status != HTTPStatus.OK or not isinstance(response_payload, dict) or response_payload.get("ok") is not True:
        error_value = str(
            response_payload.get("blocker") or response_payload.get("error_type") or "text_service_request_failed"
        ) if isinstance(response_payload, Mapping) else "text_service_request_failed"
        error_message = (
            str(response_payload.get("message")).strip()
            if isinstance(response_payload, Mapping)
            and isinstance(response_payload.get("message"), str)
            and str(response_payload.get("message")).strip()
            else "Text service request failed."
        )
        return {
            "ok": False,
            "http_status": HTTPStatus(response_status),
            "blocker": error_value,
            "message": error_message,
        }

    response_text = response_payload.get("response_text") if isinstance(response_payload, Mapping) else None
    if not isinstance(response_text, str) or not response_text.strip():
        return {
            "ok": False,
            "http_status": HTTPStatus.BAD_GATEWAY,
            "blocker": "text_service_invalid_response",
            "message": "Text service returned no usable response.",
        }

    return {
        "ok": True,
        "response_text": response_text.strip(),
        "service_name": _optional_text(service_name),
        "model_status": _optional_text(model_status),
    }


def build_text_chat_post_response_state(
    *,
    updated_slot: Mapping[str, object] | None,
    slot_index: int,
    current_title: str,
    prompt: str,
    default_title: str,
    excerpt_text: Callable[..., str],
    build_summary: Callable[[list[dict]], str | None],
) -> dict:
    slot_data = updated_slot if isinstance(updated_slot, Mapping) else {}
    message_count = slot_data.get("message_count")
    try:
        normalized_message_count = int(message_count)
    except (TypeError, ValueError):
        normalized_message_count = 0
    resolved_title = current_title
    if normalized_message_count == 2 and current_title == default_title:
        resolved_title = excerpt_text(prompt, limit=50) or current_title
    messages = slot_data.get("messages")
    normalized_messages = messages if isinstance(messages, list) else []
    return {
        "current_title": resolved_title,
        "updated_summary": build_summary(normalized_messages),
    }
