import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import checkpoint_inventory
import requests
from comfy_client import ComfyClient, ComfyClientError
from render_text2img import (
    DEFAULT_BASE_URL,
    DEFAULT_CFG,
    DEFAULT_HEIGHT,
    DEFAULT_NEGATIVE_PROMPT,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_STEPS,
    DEFAULT_WAIT_TIMEOUT,
    DEFAULT_WIDTH,
    INPUT_IMAGE_EXTENSIONS,
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
    stage_image_for_comfy,
    validate_checkpoint_preflight,
)

IDENTITY_REFERENCE_MODE = "identity_reference"
IDENTITY_WORKFLOW_NAME = "v6_1_instantid_single_reference_api.json"
IDENTITY_RUNTIME_MIN_VERSION = (0, 7, 0)
IDENTITY_RUNTIME_TIMEOUT = 45
IDENTITY_REFERENCE_DEFAULT_STEPS = 28
IDENTITY_REFERENCE_DEFAULT_CFG = 4.8
IDENTITY_REFERENCE_WAIT_TIMEOUT = 300
IDENTITY_REFERENCE_PROMPT_SUFFIX = "same person as the reference image, preserve recognizable face, same identity, same hair color, same key facial features"
IDENTITY_REFERENCE_NEGATIVE_SUFFIX = "different person, different face, different hair color, different hairstyle, identity drift, unrecognizable face"
COMFYUI_VENV_PYTHON = (
    repo_root() / "vendor" / "ComfyUI" / "venv" / "Scripts" / "python.exe"
)
IDENTITY_REQUIRED_NODES = (
    "InstantIDModelLoader",
    "InstantIDFaceAnalysis",
    "ApplyInstantID",
)
IDENTITY_REQUIRED_MODELS = {
    "antelopev2": [
        repo_root()
        / "vendor"
        / "ComfyUI"
        / "models"
        / "insightface"
        / "models"
        / "antelopev2"
        / "1k3d68.onnx",
        repo_root()
        / "vendor"
        / "ComfyUI"
        / "models"
        / "insightface"
        / "models"
        / "antelopev2"
        / "2d106det.onnx",
        repo_root()
        / "vendor"
        / "ComfyUI"
        / "models"
        / "insightface"
        / "models"
        / "antelopev2"
        / "genderage.onnx",
        repo_root()
        / "vendor"
        / "ComfyUI"
        / "models"
        / "insightface"
        / "models"
        / "antelopev2"
        / "glintr100.onnx",
        repo_root()
        / "vendor"
        / "ComfyUI"
        / "models"
        / "insightface"
        / "models"
        / "antelopev2"
        / "scrfd_10g_bnkps.onnx",
    ],
    "instantid_model": [
        repo_root() / "vendor" / "ComfyUI" / "models" / "instantid" / "ip-adapter.bin",
    ],
    "instantid_controlnet": [
        repo_root()
        / "vendor"
        / "ComfyUI"
        / "models"
        / "controlnet"
        / "instantid"
        / "diffusion_pytorch_model.safetensors",
    ],
}


def workflow_path() -> Path:
    return repo_root() / "python" / "workflows" / IDENTITY_WORKFLOW_NAME


def emit_status(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))


def validate_reference_image_preflight(
    reference_image_path: Path | None,
) -> tuple[str | None, str | None]:
    if reference_image_path is None:
        return "invalid_request", "missing_reference_image"
    if not reference_image_path.exists() or not reference_image_path.is_file():
        return "invalid_request", "missing_reference_image"
    if reference_image_path.suffix.lower() not in INPUT_IMAGE_EXTENSIONS:
        return "invalid_request", "invalid_reference_image_type"
    if reference_image_path.stat().st_size <= 0:
        return "invalid_request", "missing_reference_image"
    return None, None


def stage_reference_image_for_comfy(reference_image_path: Path) -> str:
    return stage_image_for_comfy(reference_image_path, subfolder="reference")


def parse_version_tuple(raw_version: str | None) -> tuple[int, ...]:
    if not isinstance(raw_version, str):
        return ()
    numeric_parts = [int(part) for part in re.findall(r"\d+", raw_version)]
    return tuple(numeric_parts[:3])


def probe_insightface_runtime(
    *, timeout: int = IDENTITY_RUNTIME_TIMEOUT
) -> dict[str, Any]:
    python_executable = COMFYUI_VENV_PYTHON.resolve()
    if not python_executable.exists() or not python_executable.is_file():
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_runtime_unavailable",
            "insightface_version": None,
            "runtime_error": "comfyui_venv_python_missing",
        }

    runtime_script = f"""
import json
import pathlib
import re

result = {{"ok": False, "version": None, "error": None}}
root = pathlib.Path(r"{(repo_root() / 'vendor' / 'ComfyUI' / 'models' / 'insightface').resolve()}")
try:
    import insightface
    version = getattr(insightface, "__version__", None)
    result["version"] = version
    parts = tuple(int(part) for part in re.findall(r"\\d+", version or "")[:3])
    if parts < {IDENTITY_RUNTIME_MIN_VERSION!r}:
        result["error"] = "version_unsupported"
    else:
        from insightface.app import FaceAnalysis
        FaceAnalysis(name="antelopev2", root=str(root), providers=["CPUExecutionProvider"])
        result["ok"] = True
except Exception as exc:
    result["error"] = f"{{type(exc).__name__}}: {{exc}}"
print(json.dumps(result, ensure_ascii=True))
""".strip()

    try:
        completed = subprocess.run(
            [str(python_executable), "-c", runtime_script],
            capture_output=True,
            text=True,
            timeout=max(timeout, 10),
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_runtime_unavailable",
            "insightface_version": None,
            "runtime_error": str(exc),
        }

    stdout_lines = [
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    ]
    raw_payload = stdout_lines[-1] if stdout_lines else ""
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        runtime_error = (
            completed.stderr.strip() or raw_payload or "runtime_probe_invalid"
        )
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_runtime_invalid",
            "insightface_version": None,
            "runtime_error": runtime_error,
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_runtime_invalid",
            "insightface_version": None,
            "runtime_error": "runtime_probe_invalid",
        }

    insightface_version = (
        payload.get("version") if isinstance(payload.get("version"), str) else None
    )
    if payload.get("ok") is True:
        return {
            "ok": True,
            "error_type": None,
            "blocker": None,
            "insightface_version": insightface_version,
            "runtime_error": None,
        }

    runtime_error = str(payload.get("error") or "").strip() or (
        completed.stderr.strip() or None
    )
    if runtime_error == "version_unsupported":
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_runtime_version_unsupported",
            "insightface_version": insightface_version,
            "runtime_error": runtime_error,
        }

    return {
        "ok": False,
        "error_type": "api_error",
        "blocker": "identity_runtime_invalid",
        "insightface_version": insightface_version,
        "runtime_error": runtime_error,
    }


def build_identity_runtime_state(
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    workflow_path_override: Path | None = None,
    required_models_override: dict[str, list[Path]] | None = None,
    required_nodes_override: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    current_workflow_path = (
        workflow_path_override.resolve()
        if workflow_path_override is not None
        else workflow_path()
    )
    required_models = (
        required_models_override
        if required_models_override is not None
        else IDENTITY_REQUIRED_MODELS
    )
    required_nodes = (
        required_nodes_override
        if required_nodes_override is not None
        else IDENTITY_REQUIRED_NODES
    )
    if not current_workflow_path.exists() or not current_workflow_path.is_file():
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_workflow_missing",
            "workflow_path": str(current_workflow_path),
            "insightface_version": None,
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }

    try:
        load_workflow(current_workflow_path)
    except ComfyClientError:
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_workflow_invalid",
            "workflow_path": str(current_workflow_path),
            "insightface_version": None,
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }

    missing_models: list[str] = []
    for group_name, paths in required_models.items():
        for path in paths:
            if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
                missing_models.append(group_name)
                break

    if missing_models:
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_models_missing",
            "workflow_path": str(current_workflow_path),
            "insightface_version": None,
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": sorted(set(missing_models)),
        }

    runtime_state = probe_insightface_runtime(timeout=timeout)
    if runtime_state["ok"] is not True:
        return {
            "ok": False,
            "error_type": runtime_state["error_type"],
            "blocker": runtime_state["blocker"],
            "workflow_path": str(current_workflow_path),
            "insightface_version": runtime_state["insightface_version"],
            "runtime_error": runtime_state["runtime_error"],
            "missing_nodes": [],
            "missing_models": [],
        }

    try:
        response = requests.get(f"{base_url.rstrip('/')}/object_info", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_nodes_unreachable",
            "workflow_path": str(current_workflow_path),
            "insightface_version": runtime_state["insightface_version"],
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }
    except ValueError:
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_nodes_invalid",
            "workflow_path": str(current_workflow_path),
            "insightface_version": runtime_state["insightface_version"],
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }

    if not isinstance(payload, dict):
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_nodes_invalid",
            "workflow_path": str(current_workflow_path),
            "insightface_version": runtime_state["insightface_version"],
            "runtime_error": None,
            "missing_nodes": [],
            "missing_models": [],
        }

    missing_nodes = [
        node_name
        for node_name in required_nodes
        if not isinstance(payload.get(node_name), dict)
    ]
    if missing_nodes:
        return {
            "ok": False,
            "error_type": "api_error",
            "blocker": "identity_nodes_missing",
            "workflow_path": str(current_workflow_path),
            "insightface_version": runtime_state["insightface_version"],
            "runtime_error": None,
            "missing_nodes": missing_nodes,
            "missing_models": [],
        }

    return {
        "ok": True,
        "error_type": None,
        "blocker": None,
        "workflow_path": str(current_workflow_path),
        "insightface_version": runtime_state["insightface_version"],
        "runtime_error": None,
        "missing_nodes": [],
        "missing_models": [],
    }


def run_identity_reference(
    *,
    prompt: str,
    reference_image_path: Path | None,
    checkpoint: str | None = None,
    workflow: str | None = None,
    negative_prompt: str = DEFAULT_NEGATIVE_PROMPT,
    seed: int = -1,
    steps: int = IDENTITY_REFERENCE_DEFAULT_STEPS,
    cfg: float = IDENTITY_REFERENCE_DEFAULT_CFG,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    base_url: str = DEFAULT_BASE_URL,
    timeout: int = DEFAULT_REQUEST_TIMEOUT,
    wait: bool = False,
    wait_timeout: int = IDENTITY_REFERENCE_WAIT_TIMEOUT,
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
    current_workflow_path = Path(workflow).resolve() if workflow else workflow_path()

    checkpoint_error_type, checkpoint_blocker = validate_checkpoint_preflight(
        checkpoint_path
    )
    if checkpoint_error_type is not None:
        return {
            "status": "error",
            "mode": IDENTITY_REFERENCE_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": checkpoint_error_type,
            "blocker": checkpoint_blocker,
        }

    reference_error_type, reference_blocker = validate_reference_image_preflight(
        reference_image_path.resolve() if reference_image_path is not None else None
    )
    if reference_error_type is not None:
        return {
            "status": "error",
            "mode": IDENTITY_REFERENCE_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": reference_error_type,
            "blocker": reference_blocker,
        }

    runtime_state = build_identity_runtime_state(base_url=base_url, timeout=timeout)
    if runtime_state["ok"] is not True:
        return {
            "status": "error",
            "mode": IDENTITY_REFERENCE_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": runtime_state["error_type"],
            "blocker": runtime_state["blocker"],
        }

    try:
        workflow_payload = load_workflow(current_workflow_path)
        staged_reference_image_name = stage_reference_image_for_comfy(
            reference_image_path.resolve()
        )
        effective_prompt = str(prompt or "").strip()
        if effective_prompt:
            effective_prompt = f"{effective_prompt}, {IDENTITY_REFERENCE_PROMPT_SUFFIX}"
        effective_negative_prompt = str(negative_prompt or "").strip()
        if effective_negative_prompt:
            effective_negative_prompt = (
                f"{effective_negative_prompt}, {IDENTITY_REFERENCE_NEGATIVE_SUFFIX}"
            )
        else:
            effective_negative_prompt = IDENTITY_REFERENCE_NEGATIVE_SUFFIX
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
            raise ComfyClientError(
                "ComfyUI queue response did not include prompt_id.",
                error_type="api_error",
            )

        log_run_context(
            logger=logger,
            mode=IDENTITY_REFERENCE_MODE,
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
            return build_error_payload(
                mode=IDENTITY_REFERENCE_MODE, prompt_id=prompt_id, error_type=error_type
            )

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
                    mode=IDENTITY_REFERENCE_MODE,
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
                    mode=IDENTITY_REFERENCE_MODE,
                    prompt_id=prompt_id,
                    error_type="unknown_execution_error",
                )
            log_line(logger, f"output_file: {output_file}")
            payload = build_success_payload(
                mode=IDENTITY_REFERENCE_MODE,
                prompt_id=prompt_id,
                output_file=output_file,
            )
            payload["checkpoint"] = checkpoint_path.name if checkpoint_path else None
            return payload

        payload = build_success_payload(
            mode=IDENTITY_REFERENCE_MODE,
            prompt_id=prompt_id,
            output_file=None,
        )
        payload["checkpoint"] = checkpoint_path.name if checkpoint_path else None
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
            mode=IDENTITY_REFERENCE_MODE, prompt_id=prompt_id, error_type=error_type
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the isolated V6.1 identity reference workflow via ComfyUI."
    )
    parser.add_argument("--prompt", required=True, help="Positive prompt text.")
    parser.add_argument(
        "--reference-image-path",
        required=True,
        type=Path,
        help="Path to the reference image.",
    )
    parser.add_argument(
        "--checkpoint",
        help="Explicit checkpoint filename or relative path inside models/checkpoints.",
    )
    parser.add_argument("--workflow", help="Optional workflow file name or JSON path.")
    parser.add_argument(
        "--negative-prompt",
        default=DEFAULT_NEGATIVE_PROMPT,
        help="Negative prompt text.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=-1,
        help="Seed value. -1 picks a random 32-bit seed.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_STEPS,
        help="Sampling steps to inject when supported.",
    )
    parser.add_argument(
        "--cfg",
        type=float,
        default=DEFAULT_CFG,
        help="CFG scale to inject when supported.",
    )
    parser.add_argument(
        "--width", type=int, default=DEFAULT_WIDTH, help="Image width when supported."
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help="Image height when supported.",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="ComfyUI base URL."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_REQUEST_TIMEOUT,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--wait", action="store_true", help="Wait for completion and output file."
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=DEFAULT_WAIT_TIMEOUT,
        help="Timeout for waiting on completion.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=comfy_output_dir(),
        help="ComfyUI output directory.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run_identity_reference(
        prompt=args.prompt,
        reference_image_path=args.reference_image_path,
        checkpoint=args.checkpoint,
        workflow=args.workflow,
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
