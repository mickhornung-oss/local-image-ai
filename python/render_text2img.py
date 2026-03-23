import argparse
import copy
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import checkpoint_inventory
from comfy_client import ComfyClient, ComfyClientError


MINIMAL_WORKFLOW_NAME = "sdxl_text2img_minimal.json"
IMG2IMG_WORKFLOW_NAME = "sdxl_img2img_minimal.json"
INPAINT_WORKFLOW_NAME = "sdxl_inpaint_minimal.json"
PLACEHOLDER_WORKFLOW_NAME = "api_healthcheck_placeholder.json"
CHECKPOINT_EXTENSIONS = checkpoint_inventory.CHECKPOINT_EXTENSIONS
INPUT_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MASK_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SUCCESS_STATUS_VALUES = {"success", "completed"}
DEFAULT_BASE_URL = "http://127.0.0.1:8188"
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_WAIT_TIMEOUT = 180
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, deformed"
DEFAULT_STEPS = 20
DEFAULT_CFG = 6.5
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
DEFAULT_DENOISE_STRENGTH = 0.35
MIN_DENOISE_STRENGTH = 0.05
MAX_DENOISE_STRENGTH = 0.95


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def comfy_root() -> Path:
    return repo_root() / "vendor" / "ComfyUI"


def comfy_output_dir() -> Path:
    return comfy_root() / "output"


def comfy_input_dir() -> Path:
    return comfy_root() / "input"


def comfy_app_input_dir() -> Path:
    return comfy_input_dir() / "local-image-app"


def workflow_dir() -> Path:
    return Path(__file__).resolve().parent / "workflows"


def emit_status(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


def log_line(logger: Callable[[str], None] | None, message: str) -> None:
    if logger is not None:
        logger(message)


def load_workflow(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ComfyClientError(f"Workflow file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ComfyClientError(f"Workflow file is not valid JSON: {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ComfyClientError(f"Workflow file must contain a JSON object: {path}")
    return payload


def resolve_explicit_workflow(name_or_path: str) -> Path:
    candidate = Path(name_or_path)
    if candidate.exists():
        return candidate.resolve()
    return (workflow_dir() / name_or_path).resolve()


def select_workflow_and_checkpoint(
    *,
    explicit_workflow: str | None,
    explicit_checkpoint: str | None,
    render_mode: str,
    use_input_image: bool = False,
    use_inpainting: bool = False,
) -> tuple[Path, Path | None, str]:
    normalized_mode = render_mode.lower()
    if normalized_mode not in {"auto", "sdxl", "placeholder"}:
        raise ComfyClientError(f"Unsupported render mode: {render_mode}", error_type="api_error")

    checkpoint_path = checkpoint_inventory.resolve_requested_checkpoint(explicit_checkpoint)
    if use_inpainting:
        sdxl_workflow_name = INPAINT_WORKFLOW_NAME
    elif use_input_image:
        sdxl_workflow_name = IMG2IMG_WORKFLOW_NAME
    else:
        sdxl_workflow_name = MINIMAL_WORKFLOW_NAME

    if normalized_mode == "placeholder":
        if use_input_image or use_inpainting:
            raise ComfyClientError(
                "Image-guided generation requires SDXL mode.",
                error_type="api_error",
            )
        if explicit_checkpoint:
            raise ComfyClientError(
                "Placeholder workflow cannot be combined with a checkpoint.",
                error_type="checkpoint_load_error",
            )
        return workflow_dir() / PLACEHOLDER_WORKFLOW_NAME, None, "placeholder"

    if explicit_workflow:
        workflow_path = resolve_explicit_workflow(explicit_workflow)
        if workflow_path.name == PLACEHOLDER_WORKFLOW_NAME:
            if normalized_mode == "sdxl":
                return workflow_dir() / sdxl_workflow_name, checkpoint_path, "sdxl"
            if explicit_checkpoint:
                raise ComfyClientError(
                    "Placeholder workflow cannot be combined with a checkpoint.",
                    error_type="checkpoint_load_error",
                )
            return workflow_path, None, "placeholder"
        return workflow_path, checkpoint_path, "sdxl"

    if normalized_mode == "sdxl":
        return workflow_dir() / sdxl_workflow_name, checkpoint_path, "sdxl"

    if use_input_image:
        return workflow_dir() / sdxl_workflow_name, checkpoint_path, "sdxl"

    if checkpoint_path is None:
        return workflow_dir() / PLACEHOLDER_WORKFLOW_NAME, None, "placeholder"

    return workflow_dir() / sdxl_workflow_name, checkpoint_path, "sdxl"


def validate_checkpoint_preflight(checkpoint_path: Path | None) -> tuple[str | None, str | None]:
    if checkpoint_path is None:
        return "missing_checkpoint", "missing_checkpoint"
    if not checkpoint_path.exists() or not checkpoint_path.is_file():
        return "missing_checkpoint", "missing_checkpoint"
    if checkpoint_path.suffix.lower() not in CHECKPOINT_EXTENSIONS:
        return "checkpoint_load_error", "checkpoint_load_error"
    if checkpoint_path.stat().st_size <= 0:
        return "checkpoint_load_error", "checkpoint_load_error"
    return None, None


def normalize_denoise_strength(value: float) -> float:
    return max(MIN_DENOISE_STRENGTH, min(MAX_DENOISE_STRENGTH, float(value)))


def validate_input_image_preflight(input_image_path: Path | None) -> tuple[str | None, str | None]:
    if input_image_path is None:
        return "invalid_request", "missing_input_image"
    if not input_image_path.exists() or not input_image_path.is_file():
        return "invalid_request", "missing_input_image"
    if input_image_path.suffix.lower() not in INPUT_IMAGE_EXTENSIONS:
        return "invalid_request", "invalid_input_image_type"
    if input_image_path.stat().st_size <= 0:
        return "invalid_request", "missing_input_image"
    return None, None


def validate_mask_image_preflight(mask_image_path: Path | None) -> tuple[str | None, str | None]:
    if mask_image_path is None:
        return "invalid_request", "missing_mask_image"
    if not mask_image_path.exists() or not mask_image_path.is_file():
        return "invalid_request", "missing_mask_image"
    if mask_image_path.suffix.lower() not in MASK_IMAGE_EXTENSIONS:
        return "invalid_request", "invalid_mask_image_type"
    if mask_image_path.stat().st_size <= 0:
        return "invalid_request", "missing_mask_image"
    return None, None


def stage_image_for_comfy(image_path: Path, *, subfolder: str) -> str:
    source_path = image_path.resolve()
    target_dir = comfy_app_input_dir() / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / source_path.name
    temp_path = target_dir / f".{source_path.name}.tmp"
    shutil.copy2(source_path, temp_path)
    temp_path.replace(target_path)

    for stale_path in target_dir.iterdir():
        if not stale_path.is_file():
            continue
        if stale_path == target_path:
            continue
        stale_path.unlink(missing_ok=True)

    return "/".join(target_path.relative_to(comfy_input_dir()).parts)


def stage_input_image_for_comfy(input_image_path: Path) -> str:
    return stage_image_for_comfy(input_image_path, subfolder="source")


def stage_mask_image_for_comfy(mask_image_path: Path) -> str:
    return stage_image_for_comfy(mask_image_path, subfolder="mask")


def ensure_image_sizes_match(source_image_path: Path, mask_image_path: Path) -> tuple[str | None, str | None]:
    source_path = source_image_path.resolve()
    mask_path = mask_image_path.resolve()
    try:
        from PIL import Image
        with Image.open(source_path) as source_image:
            source_image.load()
            source_size = source_image.size
        with Image.open(mask_path) as mask_image:
            mask_image.load()
            mask_size = mask_image.size
    except OSError:
        return "invalid_request", "missing_mask_image"

    if source_size != mask_size:
        return "invalid_request", "mask_size_mismatch"
    return None, None


def mutate_workflow(
    workflow: dict[str, Any],
    prompt_text: str,
    negative_prompt: str | None,
    seed: int,
    steps: int,
    cfg: float,
    width: int,
    height: int,
    checkpoint_name: str | None,
    job_suffix: str,
    denoise_strength: float | None = None,
    input_image_name: str | None = None,
    mask_image_name: str | None = None,
) -> dict[str, Any]:
    mutated = copy.deepcopy(workflow)

    for node in mutated.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            continue

        class_type = str(node.get("class_type", ""))
        title = str(node.get("_meta", {}).get("title", ""))
        descriptor = f"{class_type} {title}".lower()

        if class_type == "CLIPTextEncode":
            if "negative" in descriptor:
                if negative_prompt is not None and "text" in inputs:
                    inputs["text"] = negative_prompt
            elif "text" in inputs:
                inputs["text"] = prompt_text

        if class_type == "CheckpointLoaderSimple" and checkpoint_name:
            inputs["ckpt_name"] = checkpoint_name

        if class_type == "LoadImage" and input_image_name and isinstance(inputs.get("image"), str):
            inputs["image"] = input_image_name
        if class_type == "LoadImageMask" and mask_image_name and isinstance(inputs.get("image"), str):
            inputs["image"] = mask_image_name

        if class_type == "SaveImage" and isinstance(inputs.get("filename_prefix"), str):
            inputs["filename_prefix"] = f"{inputs['filename_prefix']}_{job_suffix}"

        if "seed" in inputs and isinstance(inputs.get("seed"), (int, float)):
            inputs["seed"] = seed
        if "steps" in inputs and isinstance(inputs.get("steps"), (int, float)):
            inputs["steps"] = steps
        if "cfg" in inputs and isinstance(inputs.get("cfg"), (int, float)):
            inputs["cfg"] = cfg
        if denoise_strength is not None and "denoise" in inputs and isinstance(inputs.get("denoise"), (int, float)):
            inputs["denoise"] = denoise_strength
        if "width" in inputs and isinstance(inputs.get("width"), (int, float)):
            inputs["width"] = width
        if "height" in inputs and isinstance(inputs.get("height"), (int, float)):
            inputs["height"] = height

    return mutated


def build_error_text(message: str, payload: dict[str, Any] | None = None) -> str:
    if not payload:
        return message
    return f"{message} {json.dumps(payload, ensure_ascii=True)}"


def classify_error_type(
    *,
    error_text: str,
    payload: dict[str, Any] | None = None,
    mode: str,
) -> str:
    combined = error_text
    if payload:
        combined = f"{combined} {json.dumps(payload, ensure_ascii=True)}"
    normalized = combined.lower()

    if "timed out" in normalized or "timeout" in normalized:
        return "timeout"

    memory_patterns = (
        "out of memory",
        "oom",
        "not enough memory",
        "insufficient memory",
        "vram",
        "bad_alloc",
    )
    if any(pattern in normalized for pattern in memory_patterns):
        return "oom_or_memory_error"

    missing_checkpoint_patterns = (
        "missing checkpoint",
        "checkpoint not found",
        "no such file",
        "does not exist",
        "file not found",
    )
    if ("checkpoint" in normalized or "ckpt_name" in normalized) and any(
        pattern in normalized for pattern in missing_checkpoint_patterns
    ):
        return "missing_checkpoint"

    checkpoint_load_patterns = (
        "ckpt_name",
        "checkpointloadersimple",
        "failed to load checkpoint",
        "error loading checkpoint",
        "could not load checkpoint",
        "prompt_outputs_failed_validation",
        "value_not_in_list",
        "not in []",
    )
    if any(pattern in normalized for pattern in checkpoint_load_patterns):
        return "checkpoint_load_error"

    api_patterns = (
        "could not connect to comfyui",
        "returned http",
        "http request",
        "invalid json",
        "/prompt",
        "/history",
        "/system_stats",
        "api",
    )
    if any(pattern in normalized for pattern in api_patterns):
        return "api_error"

    execution_patterns = (
        "execution error",
        "execution status",
        "error occurred when executing",
        "runtimeerror",
        "exception",
        "matmul",
        "tensor",
        "model",
    )
    if any(pattern in normalized for pattern in execution_patterns):
        return "model_execution_error"

    if mode == "sdxl":
        return "unknown_execution_error"
    return "unknown_execution_error"


def blocker_for_error_type(error_type: str) -> str:
    return error_type


def log_run_context(
    *,
    logger: Callable[[str], None] | None,
    mode: str,
    workflow_path: Path,
    prompt_id: str | None,
    seed: int,
    output_dir: Path,
    checkpoint_path: Path | None,
) -> None:
    log_line(logger, f"mode: {mode}")
    log_line(logger, f"workflow: {workflow_path}")
    if checkpoint_path:
        log_line(logger, f"checkpoint: {checkpoint_path.name}")
    log_line(logger, f"prompt_id: {prompt_id}")
    log_line(logger, f"seed: {seed}")
    log_line(logger, f"output_dir: {output_dir.resolve()}")


def log_history_summary(
    prompt_result: dict[str, Any],
    *,
    logger: Callable[[str], None] | None,
) -> None:
    history_nodes_seen = prompt_result.get("history_nodes_seen")
    if isinstance(history_nodes_seen, int):
        log_line(logger, f"history_nodes_seen: {history_nodes_seen}")

    output_files = prompt_result.get("output_files")
    if isinstance(output_files, list) and len(output_files) > 1:
        log_line(logger, f"output_candidates: {len(output_files)}")


def build_success_payload(
    *,
    mode: str,
    prompt_id: str | None,
    output_file: str | None,
) -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": mode,
        "prompt_id": prompt_id,
        "output_file": output_file,
        "error_type": None,
        "blocker": None,
    }


def build_error_payload(
    *,
    mode: str | None,
    prompt_id: str | None,
    error_type: str,
) -> dict[str, Any]:
    return {
        "status": "error",
        "mode": mode,
        "prompt_id": prompt_id,
        "output_file": None,
        "error_type": error_type,
        "blocker": blocker_for_error_type(error_type),
    }


def run_render(
    *,
    prompt: str,
    mode: str = "auto",
    checkpoint: str | None = None,
    workflow: str | None = None,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = -1,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    use_input_image: bool = False,
    input_image_path: Path | None = None,
    use_inpainting: bool = False,
    mask_image_path: Path | None = None,
    denoise_strength: float = DEFAULT_DENOISE_STRENGTH,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    wait: bool = False,
    wait_timeout: int = DEFAULT_WAIT_TIMEOUT,
    output_dir: Path | None = None,
    queue_only: bool = False,
    logger: Callable[[str], None] | None = None,
    error_logger: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    resolved_output_dir = output_dir.resolve() if output_dir is not None else comfy_output_dir().resolve()
    seed_value = seed if seed >= 0 else random.randint(0, 2**31 - 1)
    prompt_id: str | None = None
    output_file: str | None = None
    resolved_mode: str | None = "placeholder"
    checkpoint_path: Path | None = None
    resolved_input_image_path: Path | None = None
    resolved_mask_image_path: Path | None = None
    staged_input_image_name: str | None = None
    staged_mask_image_name: str | None = None

    try:
        workflow_path, checkpoint_path, resolved_mode = select_workflow_and_checkpoint(
            explicit_workflow=workflow,
            explicit_checkpoint=checkpoint,
            render_mode=mode,
            use_input_image=use_input_image,
            use_inpainting=use_inpainting,
        )

        if resolved_mode == "sdxl":
            preflight_error_type, _ = validate_checkpoint_preflight(checkpoint_path)
            if preflight_error_type is not None:
                if checkpoint_path:
                    log_line(logger, f"checkpoint: {checkpoint_path}")
                return build_error_payload(
                    mode=resolved_mode,
                    prompt_id=prompt_id,
                    error_type=preflight_error_type,
                )

        if use_input_image or use_inpainting:
            resolved_input_image_path = input_image_path.resolve() if input_image_path is not None else None
            input_error_type, input_blocker = validate_input_image_preflight(resolved_input_image_path)
            if input_error_type is not None:
                return {
                    "status": "error",
                    "mode": resolved_mode,
                    "prompt_id": prompt_id,
                    "output_file": None,
                    "error_type": input_error_type,
                    "blocker": input_blocker,
                }
            staged_input_image_name = stage_input_image_for_comfy(resolved_input_image_path)

        if use_inpainting:
            resolved_mask_image_path = mask_image_path.resolve() if mask_image_path is not None else None
            mask_error_type, mask_blocker = validate_mask_image_preflight(resolved_mask_image_path)
            if mask_error_type is not None:
                return {
                    "status": "error",
                    "mode": resolved_mode,
                    "prompt_id": prompt_id,
                    "output_file": None,
                    "error_type": mask_error_type,
                    "blocker": mask_blocker,
                }
            if resolved_input_image_path is None:
                return {
                    "status": "error",
                    "mode": resolved_mode,
                    "prompt_id": prompt_id,
                    "output_file": None,
                    "error_type": "invalid_request",
                    "blocker": "missing_input_image",
                }
            size_error_type, size_blocker = ensure_image_sizes_match(resolved_input_image_path, resolved_mask_image_path)
            if size_error_type is not None:
                return {
                    "status": "error",
                    "mode": resolved_mode,
                    "prompt_id": prompt_id,
                    "output_file": None,
                    "error_type": size_error_type,
                    "blocker": size_blocker,
                }
            staged_mask_image_name = stage_mask_image_for_comfy(resolved_mask_image_path)

        workflow_payload = load_workflow(workflow_path)
        queued_prompt = mutate_workflow(
            workflow=workflow_payload,
            prompt_text=prompt,
            negative_prompt=negative_prompt,
            seed=seed_value,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
            checkpoint_name=checkpoint_path.name if checkpoint_path else None,
            job_suffix=str(seed_value),
            denoise_strength=normalize_denoise_strength(denoise_strength) if (use_input_image or use_inpainting) else None,
            input_image_name=staged_input_image_name,
            mask_image_name=staged_mask_image_name,
        )

        client = ComfyClient(base_url=base_url, timeout=timeout)
        response = client.queue_prompt(queued_prompt)
        prompt_id = response.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyClientError("ComfyUI queue response did not include prompt_id.", error_type="api_error")

        log_run_context(
            logger=logger,
            mode=resolved_mode,
            workflow_path=workflow_path,
            prompt_id=prompt_id,
            seed=seed_value,
            output_dir=resolved_output_dir,
            checkpoint_path=checkpoint_path,
        )
        log_line(logger, json.dumps(response, indent=2))

        node_errors = response.get("node_errors")
        if isinstance(node_errors, dict) and node_errors:
            error_text = build_error_text("queue node errors", {"node_errors": node_errors})
            error_type = classify_error_type(
                error_text=error_text,
                payload={"node_errors": node_errors},
                mode=resolved_mode,
            )
            return build_error_payload(mode=resolved_mode, prompt_id=prompt_id, error_type=error_type)

        if wait and not queue_only:
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
                    mode=resolved_mode,
                )
                return build_error_payload(mode=resolved_mode, prompt_id=prompt_id, error_type=error_type)

            status_str = prompt_result.get("status_str")
            if isinstance(status_str, str) and status_str.lower() not in SUCCESS_STATUS_VALUES:
                error_type = classify_error_type(
                    error_text=f"execution status {status_str}",
                    payload=prompt_result["history"],
                    mode=resolved_mode,
                )
                return build_error_payload(mode=resolved_mode, prompt_id=prompt_id, error_type=error_type)

            resolved_output = prompt_result.get("output_file")
            if isinstance(resolved_output, str) and resolved_output:
                output_file = resolved_output
                log_line(logger, f"output_file: {output_file}")
                if resolved_mode == "sdxl" and not Path(output_file).exists():
                    return build_error_payload(
                        mode=resolved_mode,
                        prompt_id=prompt_id,
                        error_type="unknown_execution_error",
                    )
            else:
                error_type = classify_error_type(
                    error_text="execution completed without output file",
                    payload=prompt_result["history"],
                    mode=resolved_mode,
                )
                return build_error_payload(mode=resolved_mode, prompt_id=prompt_id, error_type=error_type)

        return build_success_payload(
            mode=resolved_mode,
            prompt_id=prompt_id,
            output_file=output_file,
        )

    except ComfyClientError as exc:
        error_text = str(exc)
        error_type = classify_error_type(
            error_text=error_text,
            payload=exc.payload,
            mode=resolved_mode or mode,
        )
        if exc.error_type == "timeout":
            error_type = "timeout"
        if error_logger is not None:
            error_logger(f"ERROR: {error_text}")
        return build_error_payload(mode=resolved_mode or mode, prompt_id=prompt_id, error_type=error_type)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a text-to-image job via local ComfyUI.")
    parser.add_argument("--workflow", help="Optional workflow file name or JSON path. Default is auto-selection.")
    parser.add_argument("--checkpoint", help="Explicit checkpoint filename or relative path inside models/checkpoints.")
    parser.add_argument("--mode", choices=("auto", "sdxl", "placeholder"), default="auto", help="Render mode.")
    parser.add_argument("--prompt", required=True, help="Positive prompt text.")
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE_PROMPT, help="Negative prompt text.")
    parser.add_argument("--seed", type=int, default=-1, help="Seed value. -1 picks a random 32-bit seed.")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS, help="Sampling steps to inject when supported.")
    parser.add_argument("--cfg", type=float, default=DEFAULT_CFG, help="CFG scale to inject when supported.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Image width when supported.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Image height when supported.")
    parser.add_argument("--use-input-image", action="store_true", help="Use a staged input image for SDXL img2img.")
    parser.add_argument("--input-image-path", type=Path, help="Path to the uploaded input image.")
    parser.add_argument("--use-inpainting", action="store_true", help="Use a staged input image and mask for SDXL inpainting.")
    parser.add_argument("--mask-image-path", type=Path, help="Path to the uploaded mask image.")
    parser.add_argument("--denoise-strength", type=float, default=DEFAULT_DENOISE_STRENGTH, help="Img2img denoise strength.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="ComfyUI base URL.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_REQUEST_TIMEOUT, help="Per-request timeout in seconds.")
    parser.add_argument("--wait", action="store_true", help="Wait for completion and output file.")
    parser.add_argument("--wait-timeout", type=int, default=DEFAULT_WAIT_TIMEOUT, help="Timeout for waiting on completion or output.")
    parser.add_argument("--output-dir", type=Path, default=comfy_output_dir(), help="ComfyUI output directory.")
    parser.add_argument("--queue-only", action="store_true", help="Queue only and skip waiting for execution or output.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    payload = run_render(
        prompt=args.prompt,
        mode=args.mode,
        checkpoint=args.checkpoint,
        workflow=args.workflow,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        width=args.width,
        height=args.height,
        use_input_image=args.use_input_image,
        input_image_path=args.input_image_path,
        use_inpainting=args.use_inpainting,
        mask_image_path=args.mask_image_path,
        denoise_strength=args.denoise_strength,
        base_url=args.base_url,
        timeout=args.timeout,
        wait=args.wait,
        wait_timeout=args.wait_timeout,
        output_dir=args.output_dir,
        queue_only=args.queue_only,
        logger=lambda message: print(message),
        error_logger=lambda message: print(message, file=sys.stderr),
    )
    emit_status(payload)
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
