from __future__ import annotations

from pathlib import Path
from typing import Mapping


def build_text_service_state(
    *,
    configured: bool,
    config: Mapping[str, object] | None,
    config_error: str | None,
    model_switch_state: Mapping[str, object] | None,
    health_payload: Mapping[str, object] | None,
    health_error: str | None,
    info_payload: Mapping[str, object] | None,
    info_error: str | None,
) -> dict:
    config_data = config if isinstance(config, Mapping) else {}
    switch_state = dict(model_switch_state) if isinstance(model_switch_state, Mapping) else None
    state = {
        "text_service_configured": configured,
        "text_service_reachable": False,
        "text_service_error": config_error,
        "text_service": {
            "service_name": None,
            "service_mode": None,
            "runner_type": None,
            "runner_present": None,
            "runner_reachable": None,
            "runner_startable": None,
            "stub_mode": None,
            "inference_available": None,
            "model_status": None,
            "model_configured": None,
            "model_present": None,
            "resolved_model_path": None,
            "current_model_name": None,
            "model_switch": switch_state,
        },
    }

    if not configured or not config_data:
        return state

    if health_error is not None or not isinstance(health_payload, Mapping):
        state["text_service_error"] = "unreachable" if health_error in {"unreachable", "timeout"} else "invalid_health"
        state["text_service"]["service_name"] = config_data.get("service_name")
        state["text_service"]["runner_type"] = config_data.get("runner_type")
        state["text_service"]["model_status"] = config_data.get("model_status")
        state["text_service"]["model_configured"] = config_data.get("model_configured")
        state["text_service"]["model_switch"] = switch_state
        return state

    service_name = health_payload.get("service")
    if not isinstance(service_name, str) or not service_name.strip():
        state["text_service_error"] = "invalid_health"
        return state

    expected_service_name = config_data.get("service_name")
    if isinstance(expected_service_name, str) and expected_service_name.strip() and service_name.strip() != expected_service_name:
        state["text_service_error"] = "unexpected_service"
        return state

    state["text_service_reachable"] = True
    state["text_service_error"] = None
    state["text_service"] = {
        "service_name": service_name.strip(),
        "service_mode": health_payload.get("service_mode") if isinstance(health_payload.get("service_mode"), str) else None,
        "runner_type": health_payload.get("runner_type") if isinstance(health_payload.get("runner_type"), str) else config_data.get("runner_type"),
        "runner_present": health_payload.get("runner_present") if isinstance(health_payload.get("runner_present"), bool) else None,
        "runner_reachable": health_payload.get("runner_reachable") if isinstance(health_payload.get("runner_reachable"), bool) else None,
        "runner_startable": health_payload.get("runner_startable") if isinstance(health_payload.get("runner_startable"), bool) else None,
        "stub_mode": health_payload.get("stub_mode") is True,
        "inference_available": health_payload.get("inference_available") if isinstance(health_payload.get("inference_available"), bool) else None,
        "model_status": health_payload.get("model_status") if isinstance(health_payload.get("model_status"), str) else config_data.get("model_status"),
        "model_configured": health_payload.get("model_configured") if isinstance(health_payload.get("model_configured"), bool) else config_data.get("model_configured"),
        "model_present": health_payload.get("model_present") if isinstance(health_payload.get("model_present"), bool) else None,
        "resolved_model_path": None,
        "current_model_name": None,
        "model_switch": switch_state,
    }

    if info_error is None and isinstance(info_payload, Mapping):
        if isinstance(info_payload.get("service_mode"), str) and str(info_payload.get("service_mode")).strip():
            state["text_service"]["service_mode"] = str(info_payload.get("service_mode")).strip()
        if isinstance(info_payload.get("runner_type"), str) and str(info_payload.get("runner_type")).strip():
            state["text_service"]["runner_type"] = str(info_payload.get("runner_type")).strip()
        if isinstance(info_payload.get("runner_present"), bool):
            state["text_service"]["runner_present"] = info_payload.get("runner_present")
        if isinstance(info_payload.get("runner_reachable"), bool):
            state["text_service"]["runner_reachable"] = info_payload.get("runner_reachable")
        if isinstance(info_payload.get("runner_startable"), bool):
            state["text_service"]["runner_startable"] = info_payload.get("runner_startable")
        state["text_service"]["stub_mode"] = info_payload.get("stub_mode") is True
        if isinstance(info_payload.get("inference_available"), bool):
            state["text_service"]["inference_available"] = info_payload.get("inference_available")
        if isinstance(info_payload.get("model_status"), str) and str(info_payload.get("model_status")).strip():
            state["text_service"]["model_status"] = str(info_payload.get("model_status")).strip()
        if isinstance(info_payload.get("model_configured"), bool):
            state["text_service"]["model_configured"] = info_payload.get("model_configured")
        if isinstance(info_payload.get("model_present"), bool):
            state["text_service"]["model_present"] = info_payload.get("model_present")
        if isinstance(info_payload.get("resolved_model_path"), str) and str(info_payload.get("resolved_model_path")).strip():
            resolved_model_path = str(info_payload.get("resolved_model_path")).strip()
            state["text_service"]["resolved_model_path"] = resolved_model_path
            state["text_service"]["current_model_name"] = Path(resolved_model_path).name
    elif info_error is not None:
        state["text_service_error"] = "info_unavailable"

    return state


def build_system_state_payload(
    *,
    runner_payload: object,
    runner_status: str | None,
    runner_error: str | None,
    comfyui_reachable: bool,
    comfyui_error: str | None,
    output_dir_accessible: bool,
    output_dir_error: str | None,
    input_dir_accessible: bool,
    input_dir_error: str | None,
    reference_dir_accessible: bool,
    reference_dir_error: str | None,
    mask_dir_accessible: bool,
    mask_dir_error: str | None,
    results_dir_accessible: bool,
    results_dir_error: str | None,
    input_image: object,
    reference_image: object,
    mask_image: object,
    inventory: Mapping[str, object] | None,
    text_service_state: Mapping[str, object] | None,
    render_state: Mapping[str, object] | None,
) -> dict:
    inventory_data = inventory if isinstance(inventory, Mapping) else {}
    payload = {
        "service": "local-image-app",
        "status": "ok",
        "runner": runner_payload,
        "runner_status": runner_status,
        "runner_error": runner_error,
        "comfyui_reachable": comfyui_reachable,
        "comfyui_error": comfyui_error,
        "api_error": comfyui_error,
        "output_dir_accessible": output_dir_accessible,
        "output_dir_error": output_dir_error,
        "input_dir_accessible": input_dir_accessible,
        "input_dir_error": input_dir_error,
        "reference_dir_accessible": reference_dir_accessible,
        "reference_dir_error": reference_dir_error,
        "mask_dir_accessible": mask_dir_accessible,
        "mask_dir_error": mask_dir_error,
        "results_dir_accessible": results_dir_accessible,
        "results_dir_error": results_dir_error,
        "input_image": input_image,
        "reference_image": reference_image,
        "mask_image": mask_image,
        "sdxl_available": int(inventory_data.get("sdxl_count") or 0) >= 1,
        "selected_checkpoint": inventory_data.get("selected"),
        "inventory": dict(inventory_data),
    }
    if isinstance(text_service_state, Mapping):
        payload.update(text_service_state)
    if isinstance(render_state, Mapping):
        payload.update(render_state)
    return payload
