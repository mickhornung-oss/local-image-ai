from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable

import requests
from comfy_client import ComfyClient, ComfyClientError
from render_identity_reference import (
    validate_reference_image_preflight,
    stage_reference_image_for_comfy,
)
from render_text2img import (
    DEFAULT_BASE_URL,
    DEFAULT_CFG,
    DEFAULT_HEIGHT,
    DEFAULT_NEGATIVE_PROMPT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_STEPS,
    DEFAULT_WAIT_TIMEOUT,
    DEFAULT_WIDTH,
    build_error_payload,
    build_success_payload,
    classify_error_type,
    comfy_output_dir,
    load_workflow,
    log_history_summary,
    log_line,
    log_run_context,
    mutate_workflow,
    repo_root,
    validate_checkpoint_preflight,
)
import checkpoint_inventory


PULID_V11_PROVIDER = "pulid_v11"
PULID_V11_WORKFLOW_NAME = "v6_4_pulid_v11_single_reference_api.json"
PULID_V11_PROMPT_SUFFIX = (
    "same person as the reference image, preserve the same facial identity, preserve hairstyle and core facial structure"
)
PULID_V11_NEGATIVE_SUFFIX = (
    "different person, different face, different hairstyle, identity drift, unrecognizable face"
)
PULID_V11_REQUIRED_NODE_TOKENS = ("pulid",)
PULID_V11_CUSTOM_NODE_DIR_CANDIDATES = (
    repo_root() / "vendor" / "ComfyUI" / "custom_nodes" / "PuLID_ComfyUI",
    repo_root() / "vendor" / "ComfyUI" / "custom_nodes" / "ComfyUI_PuLID",
)
PULID_V11_MODEL_DIR_CANDIDATES = (
    repo_root() / "vendor" / "ComfyUI" / "models" / "pulid",
    repo_root() / "vendor" / "ComfyUI" / "models" / "pulid_v11",
)


def workflow_path() -> Path:
    return repo_root() / "python" / "workflows" / PULID_V11_WORKFLOW_NAME


def _detect_custom_node_dir() -> Path | None:
    for candidate in PULID_V11_CUSTOM_NODE_DIR_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def _detect_model_dir() -> Path | None:
    for candidate in PULID_V11_MODEL_DIR_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    return None


def build_pulid_v11_runtime_state(
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    workflow_path_override: Path | None = None,
) -> dict[str, Any]:
    current_workflow_path = workflow_path_override.resolve() if workflow_path_override is not None else workflow_path()
    custom_node_dir = _detect_custom_node_dir()
    model_dir = _detect_model_dir()

    base_payload: dict[str, Any] = {
        "ok": False,
        "error_type": "api_error",
        "blocker": None,
        "provider": PULID_V11_PROVIDER,
        "workflow_path": str(current_workflow_path),
        "workflow_name": current_workflow_path.name,
        "custom_node_dir": str(custom_node_dir) if custom_node_dir is not None else None,
        "model_dir": str(model_dir) if model_dir is not None else None,
        "detected_nodes": [],
        "experimental": True,
    }

    if not current_workflow_path.exists() or not current_workflow_path.is_file():
        base_payload["blocker"] = "pulid_v11_workflow_missing"
        return base_payload

    try:
        load_workflow(current_workflow_path)
    except ComfyClientError:
        base_payload["blocker"] = "pulid_v11_workflow_invalid"
        return base_payload

    if custom_node_dir is None:
        base_payload["blocker"] = "pulid_v11_custom_node_missing"
        return base_payload

    if model_dir is None:
        base_payload["blocker"] = "pulid_v11_models_missing"
        return base_payload

    has_model_files = any(candidate.is_file() for candidate in model_dir.rglob("*"))
    if not has_model_files:
        base_payload["blocker"] = "pulid_v11_models_missing"
        return base_payload

    try:
        response = requests.get(f"{base_url.rstrip('/')}/object_info", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        base_payload["blocker"] = "pulid_v11_nodes_unreachable"
        return base_payload
    except ValueError:
        base_payload["blocker"] = "pulid_v11_nodes_invalid"
        return base_payload

    if not isinstance(payload, dict):
        base_payload["blocker"] = "pulid_v11_nodes_invalid"
        return base_payload

    detected_nodes = sorted(
        node_name
        for node_name in payload.keys()
        if isinstance(node_name, str) and any(token in node_name.lower() for token in PULID_V11_REQUIRED_NODE_TOKENS)
    )
    base_payload["detected_nodes"] = detected_nodes
    if not detected_nodes:
        base_payload["blocker"] = "pulid_v11_nodes_missing"
        return base_payload

    base_payload["ok"] = True
    base_payload["error_type"] = None
    base_payload["blocker"] = None
    return base_payload


def run_pulid_v11_identity_research(
    *,
    prompt: str,
    reference_image_path: Path | None,
    checkpoint: str | None = None,
    workflow: str | None = None,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = -1,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    wait: bool = False,
    wait_timeout: int = DEFAULT_WAIT_TIMEOUT,
    output_dir: Path | None = None,
    logger: Callable[[str], None] | None = None,
    error_logger: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    resolved_output_dir = output_dir.resolve() if output_dir is not None else comfy_output_dir().resolve()
    seed_value = seed if seed >= 0 else random.randint(0, 2**31 - 1)
    prompt_id: str | None = None
    checkpoint_path = checkpoint_inventory.resolve_requested_checkpoint(checkpoint)
    current_workflow_path = Path(workflow).resolve() if workflow else workflow_path()

    checkpoint_error_type, checkpoint_blocker = validate_checkpoint_preflight(checkpoint_path)
    if checkpoint_error_type is not None:
        return {
            "status": "error",
            "mode": PULID_V11_PROVIDER,
            "prompt_id": None,
            "output_file": None,
            "error_type": checkpoint_error_type,
            "blocker": checkpoint_blocker,
            "provider": PULID_V11_PROVIDER,
        }

    reference_error_type, reference_blocker = validate_reference_image_preflight(
        reference_image_path.resolve() if reference_image_path is not None else None
    )
    if reference_error_type is not None:
        return {
            "status": "error",
            "mode": PULID_V11_PROVIDER,
            "prompt_id": None,
            "output_file": None,
            "error_type": reference_error_type,
            "blocker": reference_blocker,
            "provider": PULID_V11_PROVIDER,
        }

    runtime_state = build_pulid_v11_runtime_state(
        base_url=base_url,
        timeout=timeout,
        workflow_path_override=current_workflow_path,
    )
    if runtime_state.get("ok") is not True:
        return {
            "status": "error",
            "mode": PULID_V11_PROVIDER,
            "prompt_id": None,
            "output_file": None,
            "error_type": str(runtime_state.get("error_type") or "api_error"),
            "blocker": str(runtime_state.get("blocker") or "pulid_v11_unavailable"),
            "provider": PULID_V11_PROVIDER,
            "workflow_name": current_workflow_path.name,
        }

    try:
        workflow_payload = load_workflow(current_workflow_path)
        staged_reference_image_name = stage_reference_image_for_comfy(reference_image_path.resolve())
        effective_prompt = str(prompt or "").strip()
        if effective_prompt:
            effective_prompt = f"{effective_prompt}, {PULID_V11_PROMPT_SUFFIX}"
        effective_negative_prompt = str(negative_prompt or "").strip()
        if effective_negative_prompt:
            effective_negative_prompt = f"{effective_negative_prompt}, {PULID_V11_NEGATIVE_SUFFIX}"
        else:
            effective_negative_prompt = PULID_V11_NEGATIVE_SUFFIX

        queued_prompt = mutate_workflow(
            workflow=workflow_payload,
            prompt_text=effective_prompt,
            negative_prompt=effective_negative_prompt,
            seed=seed_value,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            checkpoint_name=checkpoint_path.name if checkpoint_path else None,
            job_suffix=str(seed_value),
            input_image_name=staged_reference_image_name,
        )

        client = ComfyClient(base_url=base_url, timeout=timeout)
        response = client.queue_prompt(queued_prompt)
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyClientError("ComfyUI queue response did not include prompt_id.", error_type="api_error")

        log_run_context(
            logger=logger,
            mode=PULID_V11_PROVIDER,
            workflow_path=current_workflow_path,
            prompt_id=prompt_id,
            seed=seed_value,
            output_dir=resolved_output_dir,
            checkpoint_path=checkpoint_path,
        )
        log_line(logger, json.dumps(response, indent=2))

        node_errors = response.get("node_errors")
        if isinstance(node_errors, dict) and node_errors:
            error_type = classify_error_type(
                error_text="queue node errors",
                payload={"node_errors": node_errors},
                mode="sdxl",
            )
            return build_error_payload(mode=PULID_V11_PROVIDER, prompt_id=prompt_id, error_type=error_type)

        if wait:
            prompt_result = client.wait_for_prompt_result(
                prompt_id,
                output_dir=resolved_output_dir,
                timeout=wait_timeout,
            )
            log_line(logger, "history:")
            log_line(logger, json.dumps(prompt_result["history"], indent=2))
            log_history_summary(prompt_result, logger=logger)

            history_error = prompt_result.get("error_text")
            if isinstance(history_error, str) and history_error:
                error_type = classify_error_type(
                    error_text=history_error,
                    payload=prompt_result["history"],
                    mode="sdxl",
                )
                return build_error_payload(mode=PULID_V11_PROVIDER, prompt_id=prompt_id, error_type=error_type)

            output_file = prompt_result.get("output_file")
            if not isinstance(output_file, str) or not output_file or not Path(output_file).exists():
                return build_error_payload(
                    mode=PULID_V11_PROVIDER,
                    prompt_id=prompt_id,
                    error_type="unknown_execution_error",
                )
            log_line(logger, f"output_file: {output_file}")
            payload = build_success_payload(
                mode=PULID_V11_PROVIDER,
                prompt_id=prompt_id,
                output_file=output_file,
            )
            payload["checkpoint"] = checkpoint_path.name if checkpoint_path else None
            payload["workflow_name"] = current_workflow_path.name
            payload["provider"] = PULID_V11_PROVIDER
            return payload

        payload = build_success_payload(
            mode=PULID_V11_PROVIDER,
            prompt_id=prompt_id,
            output_file=None,
        )
        payload["checkpoint"] = checkpoint_path.name if checkpoint_path else None
        payload["workflow_name"] = current_workflow_path.name
        payload["provider"] = PULID_V11_PROVIDER
        return payload
    except ComfyClientError as exc:
        error_text = str(exc)
        error_type = classify_error_type(
            error_text=error_text,
            payload=exc.payload,
            mode="sdxl",
        )
        if exc.error_type == "timeout":
            error_type = "timeout"
        if error_logger is not None:
            error_logger(f"ERROR: {error_text}")
        return build_error_payload(mode=PULID_V11_PROVIDER, prompt_id=prompt_id, error_type=error_type)
