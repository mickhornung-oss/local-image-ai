import argparse
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import checkpoint_inventory
from comfy_client import ComfyClient, ComfyClientError
from identity_transfer_adapter import (
    IDENTITY_TRANSFER_STAGING_SUBFOLDER,
    build_identity_transfer_adapter_state,
)
from render_identity_reference import build_identity_runtime_state
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
    comfy_app_input_dir,
    comfy_input_dir,
    comfy_output_dir,
    load_workflow,
    log_history_summary,
    log_line,
    log_run_context,
    mutate_workflow,
    repo_root,
    validate_checkpoint_preflight,
)

IDENTITY_TRANSFER_MODE = "identity_transfer"
IDENTITY_TRANSFER_WORKFLOW_NAME = "v6_3_identity_transfer_api.json"
IDENTITY_TRANSFER_REQUIRED_NODES = (
    "InstantIDModelLoader",
    "InstantIDFaceAnalysis",
    "ApplyInstantID",
    "LoadImage",
    "VAEEncode",
)
IDENTITY_TRANSFER_STRATEGY = "instantid_target_body_init_image"
IDENTITY_TRANSFER_DEFAULT_DENOISE = 0.65


def workflow_path() -> Path:
    return repo_root() / "python" / "workflows" / IDENTITY_TRANSFER_WORKFLOW_NAME


def emit_status(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


def resolve_identity_transfer_runtime_error(blocker: str) -> tuple[str, str]:
    if blocker in {"missing_identity_head_reference", "missing_target_body_image"}:
        return "invalid_request", blocker
    return "api_error", blocker


def build_identity_transfer_runtime_state(
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    adapter_state: dict[str, Any] | None = None,
    workflow_path_override: Path | None = None,
    required_nodes_override: tuple[str, ...] | None = None,
    required_models_override: dict[str, list[Path]] | None = None,
) -> dict[str, Any]:
    current_adapter_state = (
        adapter_state
        if isinstance(adapter_state, dict)
        else build_identity_transfer_adapter_state()
    )
    if current_adapter_state.get("ready") is not True:
        blocker = str(current_adapter_state.get("error_type") or "")
        if not blocker:
            blockers = current_adapter_state.get("blockers")
            blocker = (
                str(blockers[0])
                if isinstance(blockers, list) and blockers
                else "missing_identity_head_reference"
            )
        error_type, normalized_blocker = resolve_identity_transfer_runtime_error(
            blocker
        )
        return {
            "ok": False,
            "error_type": error_type,
            "blocker": normalized_blocker,
            "adapter_state": current_adapter_state,
            "required_roles_present": current_adapter_state.get(
                "required_roles_present"
            ),
            "optional_roles_present": current_adapter_state.get(
                "optional_roles_present"
            ),
            "ordered_roles": current_adapter_state.get("ordered_roles"),
            "staging_plan": current_adapter_state.get("staging_plan"),
            "workflow_path": str(
                (
                    workflow_path_override.resolve()
                    if workflow_path_override is not None
                    else workflow_path()
                )
            ),
            "insightface_version": None,
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }

    runtime_state = build_identity_runtime_state(
        base_url=base_url,
        timeout=timeout,
        workflow_path_override=(
            workflow_path_override.resolve()
            if workflow_path_override is not None
            else workflow_path()
        ),
        required_nodes_override=(
            required_nodes_override
            if required_nodes_override is not None
            else IDENTITY_TRANSFER_REQUIRED_NODES
        ),
        required_models_override=required_models_override,
    )
    runtime_state["adapter_state"] = current_adapter_state
    runtime_state["required_roles_present"] = current_adapter_state.get(
        "required_roles_present"
    )
    runtime_state["optional_roles_present"] = current_adapter_state.get(
        "optional_roles_present"
    )
    runtime_state["ordered_roles"] = current_adapter_state.get("ordered_roles")
    runtime_state["staging_plan"] = current_adapter_state.get("staging_plan")
    return runtime_state


def build_identity_transfer_activation_plan(roles: dict[str, Any]) -> dict[str, Any]:
    pose_reference_record = (
        roles.get("pose_reference") if isinstance(roles, dict) else None
    )
    pose_reference_used = isinstance(pose_reference_record, dict)
    used_roles = ["identity_head_reference", "target_body_image"]
    if pose_reference_used:
        used_roles.append("pose_reference")
    return {
        "used_roles": used_roles,
        "pose_reference_used": pose_reference_used,
        "transfer_mask_used": False,
    }


def stage_identity_transfer_images_for_comfy(
    adapter_state: dict[str, Any], activation_plan: dict[str, Any]
) -> dict[str, str]:
    roles = adapter_state.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("missing_identity_head_reference")

    head_record = roles.get("identity_head_reference")
    if not isinstance(head_record, dict):
        raise ValueError("missing_identity_head_reference")

    target_record = roles.get("target_body_image")
    if not isinstance(target_record, dict):
        raise ValueError("missing_target_body_image")

    used_roles = tuple(
        str(role_name)
        for role_name in activation_plan.get("used_roles")
        or ("identity_head_reference", "target_body_image")
    )
    target_dir = comfy_app_input_dir() / IDENTITY_TRANSFER_STAGING_SUBFOLDER
    target_dir.mkdir(parents=True, exist_ok=True)

    staged_names: dict[str, str] = {}
    expected_names: set[str] = set()
    for role_name in used_roles:
        record = roles[role_name]
        source_path = Path(str(record["path"])).resolve()
        target_name = f"{role_name}__{record['image_id']}{source_path.suffix.lower()}"
        target_path = target_dir / target_name
        temp_path = target_dir / f".{target_name}.tmp"
        shutil.copy2(source_path, temp_path)
        temp_path.replace(target_path)
        expected_names.add(target_name)
        staged_names[role_name] = "/".join(
            target_path.relative_to(comfy_input_dir()).parts
        )

    for stale_path in target_dir.iterdir():
        if not stale_path.is_file():
            continue
        if stale_path.name.startswith("."):
            stale_path.unlink(missing_ok=True)
            continue
        if stale_path.name not in expected_names:
            stale_path.unlink(missing_ok=True)

    return staged_names


def mutate_identity_transfer_workflow(
    *,
    workflow: dict[str, Any],
    staged_role_images: dict[str, str],
    activation_plan: dict[str, Any],
    prompt_text: str,
    negative_prompt: str,
    seed: int,
    steps: int,
    cfg: float,
    width: int,
    height: int,
    checkpoint_name: str | None,
    denoise: float,
    job_suffix: str,
) -> dict[str, Any]:
    if "identity_head_reference" not in staged_role_images:
        raise ValueError("missing_identity_head_reference")
    if "target_body_image" not in staged_role_images:
        raise ValueError("missing_target_body_image")

    mutated = mutate_workflow(
        workflow=workflow,
        prompt_text=prompt_text,
        negative_prompt=negative_prompt,
        seed=seed,
        steps=steps,
        cfg=cfg,
        width=width,
        height=height,
        checkpoint_name=checkpoint_name,
        job_suffix=job_suffix,
        denoise_strength=denoise,
    )
    mutated["13"]["inputs"]["image"] = staged_role_images["identity_head_reference"]
    mutated["20"]["inputs"]["image"] = staged_role_images["target_body_image"]
    mutated["3"]["inputs"]["latent_image"] = ["21", 0]

    if (
        activation_plan.get("pose_reference_used") is True
        and "pose_reference" in staged_role_images
    ):
        mutated["22"] = {
            "inputs": {
                "image": staged_role_images["pose_reference"],
            },
            "class_type": "LoadImage",
            "_meta": {
                "title": "Load Pose Reference",
            },
        }
        mutated["60"]["inputs"]["image_kps"] = ["22", 0]
    else:
        mutated["60"]["inputs"].pop("image_kps", None)
        mutated.pop("22", None)
    mutated["60"]["inputs"].pop("mask", None)
    mutated["3"]["inputs"]["latent_image"] = ["21", 0]

    return mutated


def run_identity_transfer(
    *,
    prompt: str,
    adapter_state: dict[str, Any] | None = None,
    checkpoint: str | None = None,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = -1,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    denoise: float = IDENTITY_TRANSFER_DEFAULT_DENOISE,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    wait: bool = False,
    wait_timeout: int = DEFAULT_WAIT_TIMEOUT,
    output_dir: Path | None = None,
    logger: Callable[[str], None] | None = None,
    error_logger: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    resolved_output_dir = (
        output_dir.resolve() if output_dir is not None else comfy_output_dir().resolve()
    )
    seed_value = seed if seed >= 0 else random.randint(0, 2**31 - 1)
    prompt_id: str | None = None
    checkpoint_path = checkpoint_inventory.resolve_requested_checkpoint(checkpoint)

    checkpoint_error_type, checkpoint_blocker = validate_checkpoint_preflight(
        checkpoint_path
    )
    if checkpoint_error_type is not None:
        return {
            "status": "error",
            "mode": IDENTITY_TRANSFER_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": checkpoint_error_type,
            "blocker": checkpoint_blocker,
        }

    runtime_state = build_identity_transfer_runtime_state(
        base_url=base_url,
        timeout=timeout,
        adapter_state=adapter_state,
    )
    if runtime_state.get("ok") is not True:
        return {
            "status": "error",
            "mode": IDENTITY_TRANSFER_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": runtime_state.get("error_type"),
            "blocker": runtime_state.get("blocker"),
        }

    effective_adapter_state = runtime_state["adapter_state"]
    roles = effective_adapter_state["roles"]
    activation_plan = build_identity_transfer_activation_plan(roles)
    try:
        workflow_payload = load_workflow(workflow_path())
        staged_role_images = stage_identity_transfer_images_for_comfy(
            effective_adapter_state, activation_plan
        )
        queued_prompt = mutate_identity_transfer_workflow(
            workflow=workflow_payload,
            staged_role_images=staged_role_images,
            activation_plan=activation_plan,
            prompt_text=prompt,
            negative_prompt=negative_prompt,
            seed=seed_value,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            checkpoint_name=checkpoint_path.name if checkpoint_path else None,
            denoise=denoise,
            job_suffix=str(seed_value),
        )

        client = ComfyClient(base_url=base_url, timeout=timeout)
        response = client.queue_prompt(queued_prompt)
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyClientError(
                "ComfyUI queue response did not include prompt_id.",
                error_type="api_error",
            )

        log_run_context(
            logger=logger,
            mode=IDENTITY_TRANSFER_MODE,
            workflow_path=workflow_path(),
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
            return build_error_payload(
                mode=IDENTITY_TRANSFER_MODE, prompt_id=prompt_id, error_type=error_type
            )

        pose_reference_present = isinstance(roles.get("pose_reference"), dict)
        transfer_mask_present = isinstance(roles.get("transfer_mask"), dict)
        extra_payload = {
            "checkpoint": checkpoint_path.name if checkpoint_path else None,
            "used_roles": activation_plan["used_roles"],
            "pose_reference_present": pose_reference_present,
            "pose_reference_used": activation_plan["pose_reference_used"],
            "transfer_mask_present": transfer_mask_present,
            "transfer_mask_used": activation_plan["transfer_mask_used"],
            "identity_head_reference_image_id": str(
                roles["identity_head_reference"]["image_id"]
            ),
            "target_body_image_id": str(roles["target_body_image"]["image_id"]),
            "pose_reference_image_id": (
                str(roles["pose_reference"]["image_id"])
                if pose_reference_present
                else None
            ),
            "transfer_mask_image_id": (
                str(roles["transfer_mask"]["image_id"])
                if transfer_mask_present
                else None
            ),
            "identity_transfer_strategy": IDENTITY_TRANSFER_STRATEGY,
        }

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
                return build_error_payload(
                    mode=IDENTITY_TRANSFER_MODE,
                    prompt_id=prompt_id,
                    error_type=error_type,
                )

            output_file = prompt_result.get("output_file")
            if (
                not isinstance(output_file, str)
                or not output_file
                or not Path(output_file).exists()
            ):
                return build_error_payload(
                    mode=IDENTITY_TRANSFER_MODE,
                    prompt_id=prompt_id,
                    error_type="unknown_execution_error",
                )

            payload = build_success_payload(
                mode=IDENTITY_TRANSFER_MODE,
                prompt_id=prompt_id,
                output_file=output_file,
            )
            payload.update(extra_payload)
            return payload

        payload = build_success_payload(
            mode=IDENTITY_TRANSFER_MODE,
            prompt_id=prompt_id,
            output_file=None,
        )
        payload.update(extra_payload)
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
        return build_error_payload(
            mode=IDENTITY_TRANSFER_MODE, prompt_id=prompt_id, error_type=error_type
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the isolated V6.3.3 identity-transfer workflow via ComfyUI."
    )
    parser.add_argument("--prompt", required=True, help="Positive prompt text.")
    parser.add_argument(
        "--checkpoint",
        help="Explicit checkpoint filename or relative path inside models/checkpoints.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for completion and emit the final result JSON.",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Wait timeout in seconds.",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="ComfyUI base URL."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_identity_transfer(
        prompt=args.prompt,
        checkpoint=args.checkpoint,
        wait=args.wait,
        wait_timeout=args.wait_timeout,
        base_url=args.base_url,
    )
    emit_status(result)
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
