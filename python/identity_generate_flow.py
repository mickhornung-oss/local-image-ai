from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def _error(http_status: HTTPStatus, *, error_type: str, blocker: str) -> dict:
    return {
        "http_status": http_status,
        "error_type": error_type,
        "blocker": blocker,
    }


def coerce_identity_generate_payload(payload: object) -> tuple[dict | None, dict | None]:
    if not isinstance(payload, dict):
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_json",
        )
    return payload, None


def normalize_identity_prompt_and_checkpoint(payload: Mapping[str, object]) -> tuple[dict | None, dict | None]:
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="empty_prompt",
        )
    checkpoint = None
    checkpoint_value = payload.get("checkpoint")
    if isinstance(checkpoint_value, str) and checkpoint_value.strip():
        checkpoint = checkpoint_value.strip()
    return {
        "prompt": prompt.strip(),
        "checkpoint": checkpoint,
    }, None


def prepare_identity_reference_request(
    payload: object,
    *,
    resolve_reference_image: Callable[[object], tuple[dict | None, object]],
) -> tuple[dict | None, dict | None]:
    payload_dict, payload_error = coerce_identity_generate_payload(payload)
    if payload_error is not None or payload_dict is None:
        return None, payload_error
    normalized, normalize_error = normalize_identity_prompt_and_checkpoint(payload_dict)
    if normalize_error is not None or normalized is None:
        return None, normalize_error
    try:
        reference_image_payload, reference_image_path = resolve_reference_image(payload_dict.get("reference_image_id"))
    except ValueError as exc:
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker=str(exc),
        )
    normalized["reference_image_payload"] = reference_image_payload
    normalized["reference_image_path"] = reference_image_path
    return normalized, None


def prepare_identity_research_request(
    payload: object,
    *,
    resolve_reference_image: Callable[[object], tuple[dict | None, object]],
    normalize_negative_prompt: Callable[[object], tuple[str | None, str | None]],
    default_provider: str,
) -> tuple[dict | None, dict | None]:
    normalized, error = prepare_identity_reference_request(
        payload,
        resolve_reference_image=resolve_reference_image,
    )
    if error is not None or normalized is None:
        return None, error
    negative_prompt, negative_prompt_error = normalize_negative_prompt(
        payload.get("negative_prompt") if isinstance(payload, Mapping) else None
    )
    if negative_prompt_error is not None:
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker=negative_prompt_error,
        )
    provider_value = payload.get("provider") if isinstance(payload, Mapping) else None
    provider = str(provider_value or default_provider).strip().lower() or default_provider
    normalized["negative_prompt"] = negative_prompt
    normalized["provider"] = provider
    return normalized, None


def build_runtime_preflight_failure(
    runtime_state: Mapping[str, object] | None,
    *,
    unavailable_blocker: str,
    status_code_resolver: Callable[..., HTTPStatus],
) -> dict | None:
    state = runtime_state if isinstance(runtime_state, Mapping) else {}
    if state.get("ok") is True:
        return None
    blocker = str(state.get("blocker") or unavailable_blocker)
    error_type = str(state.get("error_type") or "api_error")
    return _error(
        status_code_resolver(error_type=error_type, blocker=blocker),
        error_type=error_type,
        blocker=blocker,
    )


def build_system_preflight_failure(system_state: Mapping[str, object] | None) -> dict | None:
    state = system_state if isinstance(system_state, Mapping) else {}
    if state.get("comfyui_reachable") is not True:
        blocker = "runner_state_invalid" if state.get("runner_error") == "runner_state_invalid" else "comfyui_unreachable"
        return _error(
            HTTPStatus.SERVICE_UNAVAILABLE,
            error_type="api_error",
            blocker=blocker,
        )
    if state.get("runner_status") == "unknown":
        return _error(
            HTTPStatus.SERVICE_UNAVAILABLE,
            error_type="api_error",
            blocker="runner_state_invalid",
        )
    return None


def resolve_multi_reference_adapter_state(
    runtime_state: Mapping[str, object] | None,
    *,
    fallback_adapter_state: dict,
) -> dict:
    state = runtime_state if isinstance(runtime_state, Mapping) else {}
    adapter_state = state.get("adapter_state")
    return adapter_state if isinstance(adapter_state, dict) else fallback_adapter_state
