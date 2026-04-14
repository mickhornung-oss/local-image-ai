import argparse
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import checkpoint_inventory
from comfy_client import ComfyClient, ComfyClientError
from multi_reference_adapter import (
    MULTI_REFERENCE_STAGING_SUBFOLDER,
    build_multi_reference_adapter_state,
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
    comfy_output_dir,
    load_workflow,
    log_history_summary,
    log_line,
    log_run_context,
    mutate_workflow,
    repo_root,
    validate_checkpoint_preflight,
)


IDENTITY_MULTI_REFERENCE_MODE = "identity_multi_reference"
IDENTITY_MULTI_REFERENCE_WORKFLOW_NAME = "v6_2_instantid_multi_reference_api.json"
IDENTITY_MULTI_REFERENCE_DEFAULT_STEPS = 30
IDENTITY_MULTI_REFERENCE_DEFAULT_CFG = 4.5
IDENTITY_MULTI_REFERENCE_WAIT_TIMEOUT = 300
IDENTITY_MULTI_REFERENCE_MAX_ACTIVE_REFERENCES = 2
IDENTITY_MULTI_REFERENCE_PROMPT_SUFFIX = (
    "same person as the reference images, preserve recognizable face, same identity, same hair color, same key facial features"
)
IDENTITY_MULTI_REFERENCE_NEGATIVE_SUFFIX = (
    "different person, different face, different hair color, different hairstyle, identity drift, unrecognizable face"
)
IDENTITY_MULTI_REFERENCE_REQUIRED_NODES = (
    "InstantIDModelLoader",
    "InstantIDFaceAnalysis",
    "ApplyInstantID",
    "ImageBatch",
)


def workflow_path() -> Path:
    return repo_root() / "python" / "workflows" / IDENTITY_MULTI_REFERENCE_WORKFLOW_NAME


def emit_status(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


def resolve_multi_reference_runtime_error(blocker: str) -> tuple[str, str]:
    if blocker == "insufficient_multi_reference_images":
        return "invalid_request", blocker
    return "api_error", blocker


def build_identity_multi_reference_runtime_state(
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    adapter_state: dict[str, Any] | None = None,
    workflow_path_override: Path | None = None,
    required_nodes_override: tuple[str, ...] | None = None,
    required_models_override: dict[str, list[Path]] | None = None,
) -> dict[str, Any]:
    current_adapter_state = adapter_state if isinstance(adapter_state, dict) else build_multi_reference_adapter_state()
    if current_adapter_state.get("ready") is not True:
        blockers = current_adapter_state.get("blockers")
        blocker = blockers[0] if isinstance(blockers, list) and blockers else "insufficient_multi_reference_images"
        error_type, normalized_blocker = resolve_multi_reference_runtime_error(str(blocker))
        return {
            "ok": False,
            "error_type": error_type,
            "blocker": normalized_blocker,
            "adapter_state": current_adapter_state,
            "workflow_path": str((workflow_path_override.resolve() if workflow_path_override is not None else workflow_path())),
            "insightface_version": None,
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }

    runtime_state = build_identity_runtime_state(
        base_url=base_url,
        timeout=timeout,
        workflow_path_override=workflow_path_override.resolve() if workflow_path_override is not None else workflow_path(),
        required_nodes_override=required_nodes_override if required_nodes_override is not None else IDENTITY_MULTI_REFERENCE_REQUIRED_NODES,
        required_models_override=required_models_override,
    )
    runtime_state["adapter_state"] = current_adapter_state
    return runtime_state


def stage_multi_reference_images_for_comfy(adapter_state: dict[str, Any]) -> list[str]:
    references = adapter_state.get("references")
    if not isinstance(references, list) or not references:
        raise ValueError("insufficient_multi_reference_images")
    references = references[:IDENTITY_MULTI_REFERENCE_MAX_ACTIVE_REFERENCES]

    target_dir = comfy_app_input_dir() / MULTI_REFERENCE_STAGING_SUBFOLDER
    target_dir.mkdir(parents=True, exist_ok=True)

    staged_names: list[str] = []
    expected_names: set[str] = set()
    for reference in references:
        source_path = Path(str(reference["path"])).resolve()
        target_name = f"slot_{int(reference['slot_index'])}_{reference['image_id']}{source_path.suffix.lower()}"
        target_path = target_dir / target_name
        temp_path = target_dir / f".{target_name}.tmp"
        shutil.copy2(source_path, temp_path)
        temp_path.replace(target_path)
        expected_names.add(target_name)
        staged_names.append("/".join(target_path.relative_to(comfy_app_input_dir().parent).parts))

    for stale_path in target_dir.iterdir():
        if not stale_path.is_file():
            continue
        if stale_path.name.startswith("."):
            stale_path.unlink(missing_ok=True)
            continue
        if stale_path.name not in expected_names:
            stale_path.unlink(missing_ok=True)

    return staged_names


def mutate_multi_reference_workflow(
    *,
    workflow: dict[str, Any],
    staged_image_names: list[str],
    prompt_text: str,
    negative_prompt: str,
    seed: int,
    steps: int,
    cfg: float,
    width: int,
    height: int,
    checkpoint_name: str | None,
    job_suffix: str,
) -> dict[str, Any]:
    if len(staged_image_names) < 2:
        raise ValueError("insufficient_multi_reference_images")

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
    )

    mutated["13"]["inputs"]["image"] = staged_image_names[0]
    mutated["14"]["inputs"]["image"] = staged_image_names[1]
    mutated["60"]["inputs"]["image_kps"] = ["13", 0]

    if len(staged_image_names) >= 3:
        mutated["17"]["inputs"]["image"] = staged_image_names[2]
        mutated["60"]["inputs"]["image"] = ["18", 0]
    else:
        mutated["60"]["inputs"]["image"] = ["15", 0]
        mutated.pop("17", None)
        mutated.pop("18", None)

    return mutated


def run_identity_multi_reference(
    *,
    prompt: str,
    adapter_state: dict[str, Any] | None = None,
    checkpoint: str | None = None,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = -1,
    steps: int = IDENTITY_MULTI_REFERENCE_DEFAULT_STEPS,
    cfg: float = IDENTITY_MULTI_REFERENCE_DEFAULT_CFG,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    wait: bool = False,
    wait_timeout: int = IDENTITY_MULTI_REFERENCE_WAIT_TIMEOUT,
    output_dir: Path | None = None,
    logger: Callable[[str], None] | None = None,
    error_logger: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    resolved_output_dir = output_dir.resolve() if output_dir is not None else comfy_output_dir().resolve()
    seed_value = seed if seed >= 0 else random.randint(0, 2**31 - 1)
    prompt_id: str | None = None
    checkpoint_path = checkpoint_inventory.resolve_requested_checkpoint(checkpoint)

    checkpoint_error_type, checkpoint_blocker = validate_checkpoint_preflight(checkpoint_path)
    if checkpoint_error_type is not None:
        return {
            "status": "error",
            "mode": IDENTITY_MULTI_REFERENCE_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": checkpoint_error_type,
            "blocker": checkpoint_blocker,
        }

    runtime_state = build_identity_multi_reference_runtime_state(
        base_url=base_url,
        timeout=timeout,
        adapter_state=adapter_state,
    )
    if runtime_state.get("ok") is not True:
        return {
            "status": "error",
            "mode": IDENTITY_MULTI_REFERENCE_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": runtime_state.get("error_type"),
            "blocker": runtime_state.get("blocker"),
        }

    effective_adapter_state = runtime_state["adapter_state"]
    references = effective_adapter_state["references"][:IDENTITY_MULTI_REFERENCE_MAX_ACTIVE_REFERENCES]
    try:
        workflow_payload = load_workflow(workflow_path())
        effective_prompt = str(prompt or "").strip()
        if effective_prompt:
            effective_prompt = f"{effective_prompt}, {IDENTITY_MULTI_REFERENCE_PROMPT_SUFFIX}"
        effective_negative_prompt = str(negative_prompt or "").strip()
        if effective_negative_prompt:
            effective_negative_prompt = f"{effective_negative_prompt}, {IDENTITY_MULTI_REFERENCE_NEGATIVE_SUFFIX}"
        else:
            effective_negative_prompt = IDENTITY_MULTI_REFERENCE_NEGATIVE_SUFFIX
        staged_image_names = stage_multi_reference_images_for_comfy(effective_adapter_state)
        queued_prompt = mutate_multi_reference_workflow(
            workflow=workflow_payload,
            staged_image_names=staged_image_names,
            prompt_text=effective_prompt,
            negative_prompt=effective_negative_prompt,
            seed=seed_value,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            checkpoint_name=checkpoint_path.name if checkpoint_path else None,
            job_suffix=str(seed_value),
        )

        client = ComfyClient(base_url=base_url, timeout=timeout)
        response = client.queue_prompt(queued_prompt)
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyClientError("ComfyUI queue response did not include prompt_id.", error_type="api_error")

        log_run_context(
            logger=logger,
            mode=IDENTITY_MULTI_REFERENCE_MODE,
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
            return build_error_payload(mode=IDENTITY_MULTI_REFERENCE_MODE, prompt_id=prompt_id, error_type=error_type)

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
                return build_error_payload(mode=IDENTITY_MULTI_REFERENCE_MODE, prompt_id=prompt_id, error_type=error_type)

            output_file = prompt_result.get("output_file")
            if not isinstance(output_file, str) or not output_file or not Path(output_file).exists():
                return build_error_payload(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    prompt_id=prompt_id,
                    error_type="unknown_execution_error",
                )

            payload = build_success_payload(
                mode=IDENTITY_MULTI_REFERENCE_MODE,
                prompt_id=prompt_id,
                output_file=output_file,
            )
            payload["checkpoint"] = checkpoint_path.name if checkpoint_path else None
            payload["reference_count"] = len(references)
            payload["reference_slots"] = [int(reference["slot_index"]) for reference in references]
            payload["reference_image_ids"] = [str(reference["image_id"]) for reference in references]
            payload["multi_reference_strategy"] = "instantid_primary_two_reference_batch"
            return payload

        payload = build_success_payload(
            mode=IDENTITY_MULTI_REFERENCE_MODE,
            prompt_id=prompt_id,
            output_file=None,
        )
        payload["checkpoint"] = checkpoint_path.name if checkpoint_path else None
        payload["reference_count"] = len(references)
        payload["reference_slots"] = [int(reference["slot_index"]) for reference in references]
        payload["reference_image_ids"] = [str(reference["image_id"]) for reference in references]
        payload["multi_reference_strategy"] = "instantid_primary_two_reference_batch"
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
        return build_error_payload(mode=IDENTITY_MULTI_REFERENCE_MODE, prompt_id=prompt_id, error_type=error_type)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the isolated V6.2.3 multi-reference identity workflow via ComfyUI.")
    parser.add_argument("--prompt", required=True, help="Positive prompt text.")
    parser.add_argument("--checkpoint", help="Explicit checkpoint filename or relative path inside models/checkpoints.")
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE_PROMPT, help="Negative prompt text.")
    parser.add_argument("--seed", type=int, default=-1, help="Seed value. -1 picks a random 32-bit seed.")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Sampling steps to inject when supported.")
    parser.add_argument("--cfg", type=float, default=DEFAULT_CFG, help="CFG scale to inject when supported.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Image width when supported.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Image height when supported.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ComfyUI base URL.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT, help="Per-request timeout in seconds.")
    parser.add_argument("--wait", action="store_true", help="Wait for completion and output file.")
    parser.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT, help="Timeout for waiting on completion.")
    parser.add_argument("--output-dir", type=Path, default=comfy_output_dir(), help="ComfyUI output directory.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run_identity_multi_reference(
        prompt=args.prompt,
        checkpoint=args.checkpoint,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        width=args.width,
        height=args.height,
        base_url=args.base_url,
        timeout=args.timeout,
        wait=args.wait,
        wait_timeout=args.wait_timeout,
        output_dir=args.output_dir,
        logger=lambda message: print(message),
        error_logger=lambda message: print(message, file=sys.stderr),
    )
    emit_status(payload)
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
