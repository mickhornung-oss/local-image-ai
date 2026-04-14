from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def _error(http_status: HTTPStatus, *, error_type: str, blocker: str) -> dict:
    return {
        "http_status": http_status,
        "error_type": error_type,
        "blocker": blocker,
    }


def coerce_general_generate_payload(payload: object) -> tuple[dict | None, dict | None]:
    if not isinstance(payload, dict):
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_json",
        )
    return payload, None


def prepare_general_generate_request(
    payload: object,
    *,
    normalize_negative_prompt: Callable[[object], tuple[str | None, str | None]],
    parse_boolean_flag: Callable[[object], bool],
    normalize_denoise_strength_value: Callable[..., float],
    resolve_generation_request: Callable[..., tuple[str, str, str | None]],
    resolve_requested_input_image: Callable[[object], tuple[dict, object]],
    resolve_requested_mask_image: Callable[[object], tuple[dict, object]],
    resolve_inpainting_tuning: Callable[..., dict],
) -> tuple[dict | None, dict | None]:
    payload_dict, payload_error = coerce_general_generate_payload(payload)
    if payload_error is not None or payload_dict is None:
        return None, payload_error

    prompt = payload_dict.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="empty_prompt",
        )

    negative_prompt, negative_prompt_error = normalize_negative_prompt(payload_dict.get("negative_prompt"))
    if negative_prompt_error is not None:
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker=negative_prompt_error,
        )

    try:
        use_input_image = parse_boolean_flag(payload_dict.get("use_input_image"))
        use_inpainting = parse_boolean_flag(payload_dict.get("use_inpainting"))
    except ValueError as exc:
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker=str(exc),
        )

    use_edit_image = use_input_image and not use_inpainting
    try:
        denoise_strength = normalize_denoise_strength_value(
            payload_dict.get("denoise_strength"),
            for_inpainting=use_inpainting,
            for_edit=use_edit_image,
        )
    except ValueError as exc:
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker=str(exc),
        )

    try:
        mode, workflow, checkpoint = resolve_generation_request(
            payload_dict,
            use_input_image=use_input_image,
            use_inpainting=use_inpainting,
        )
    except ValueError as exc:
        return None, _error(
            HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker=str(exc),
        )

    input_image_path = None
    if use_input_image or use_inpainting:
        try:
            _, input_image_path = resolve_requested_input_image(payload_dict.get("input_image_id"))
        except ValueError as exc:
            return None, _error(
                HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker=str(exc),
            )

    mask_image_path = None
    inpaint_tuning = None
    if use_inpainting:
        try:
            _, mask_image_path = resolve_requested_mask_image(payload_dict.get("mask_image_id"))
        except ValueError as exc:
            return None, _error(
                HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker=str(exc),
            )
        inpaint_tuning = resolve_inpainting_tuning(
            prompt=prompt,
            checkpoint=checkpoint,
            mask_image_path=mask_image_path,
            requested_denoise_strength=payload_dict.get("denoise_strength"),
        )
        if isinstance(inpaint_tuning.get("denoise_strength"), (int, float)):
            denoise_strength = float(inpaint_tuning["denoise_strength"])

    return {
        "payload": payload_dict,
        "prompt": prompt.strip(),
        "negative_prompt": negative_prompt,
        "use_input_image": use_input_image,
        "use_inpainting": use_inpainting,
        "use_edit_image": use_edit_image,
        "denoise_strength": denoise_strength,
        "mode": mode,
        "workflow": workflow,
        "checkpoint": checkpoint,
        "input_image_path": input_image_path,
        "mask_image_path": mask_image_path,
        "inpaint_tuning": inpaint_tuning,
    }, None


def build_general_generate_system_failure(system_state: Mapping[str, object] | None) -> dict | None:
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


def build_general_render_request(
    prepared: Mapping[str, object],
    *,
    resolve_general_generate_tuning: Callable[..., tuple[float, int, str | None]],
    resolve_render_prompt: Callable[..., str],
    inpaint_locality_negative_suffix: str,
) -> dict:
    inpaint_tuning = prepared.get("inpaint_tuning") if isinstance(prepared.get("inpaint_tuning"), Mapping) else None
    checkpoint = prepared.get("checkpoint")
    negative_prompt = prepared.get("negative_prompt")
    use_inpainting = prepared.get("use_inpainting") is True
    use_edit_image = prepared.get("use_edit_image") is True
    prompt_text = str(prepared.get("prompt") or "")

    cfg_value, steps_value, negative_prompt_value = resolve_general_generate_tuning(
        checkpoint=checkpoint,
        use_inpainting=use_inpainting,
        use_edit_image=use_edit_image,
        extra_negative_prompt=negative_prompt,
        cfg_override=inpaint_tuning.get("cfg") if isinstance(inpaint_tuning, Mapping) else None,
        steps_override=inpaint_tuning.get("steps") if isinstance(inpaint_tuning, Mapping) else None,
        inpaint_negative_suffix=(
            f"{inpaint_locality_negative_suffix}, {inpaint_tuning.get('negative_suffix')}"
            if isinstance(inpaint_tuning, Mapping)
            and isinstance(inpaint_tuning.get("negative_suffix"), str)
            and inpaint_tuning.get("negative_suffix").strip()
            else None
        ),
    )
    render_prompt = resolve_render_prompt(
        prompt_text,
        use_inpainting=use_inpainting,
        use_edit_image=use_edit_image,
        inpaint_prompt_suffix=inpaint_tuning.get("prompt_suffix") if isinstance(inpaint_tuning, Mapping) else None,
    )

    return {
        "prompt_text": prompt_text,
        "render_prompt": render_prompt,
        "cfg_value": cfg_value,
        "steps_value": steps_value,
        "negative_prompt_value": negative_prompt_value,
        "grow_mask_by_override": (
            inpaint_tuning.get("grow_mask_by") if isinstance(inpaint_tuning, Mapping) else None
        ),
    }
