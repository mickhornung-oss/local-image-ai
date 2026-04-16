from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from render_identity_reference import (
    IDENTITY_REFERENCE_MODE,
    IDENTITY_WORKFLOW_NAME,
    build_identity_runtime_state,
    run_identity_reference,
)
from render_identity_research_pulid_v11 import (
    PULID_V11_PROVIDER,
    PULID_V11_WORKFLOW_NAME,
    build_pulid_v11_runtime_state,
    run_pulid_v11_identity_research,
)

IDENTITY_RESEARCH_MODE = "identity_research"
IDENTITY_RESEARCH_DEFAULT_PROVIDER = "instantid"
IDENTITY_RESEARCH_SUPPORTED_PROVIDERS = (
    IDENTITY_RESEARCH_DEFAULT_PROVIDER,
    PULID_V11_PROVIDER,
)


def _build_instantid_runtime_state() -> dict[str, Any]:
    runtime_state = dict(build_identity_runtime_state())
    runtime_state["mode"] = IDENTITY_RESEARCH_MODE
    runtime_state["provider"] = IDENTITY_RESEARCH_DEFAULT_PROVIDER
    runtime_state["workflow_name"] = IDENTITY_WORKFLOW_NAME
    runtime_state["experimental"] = True
    return runtime_state


def _build_provider_runtime_state(provider: str) -> dict[str, Any]:
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider == IDENTITY_RESEARCH_DEFAULT_PROVIDER:
        return _build_instantid_runtime_state()
    if normalized_provider == PULID_V11_PROVIDER:
        runtime_state = dict(build_pulid_v11_runtime_state())
        runtime_state["mode"] = IDENTITY_RESEARCH_MODE
        runtime_state["experimental"] = True
        return runtime_state
    return {
        "ok": False,
        "error_type": "invalid_request",
        "blocker": "unsupported_identity_research_provider",
        "mode": IDENTITY_RESEARCH_MODE,
        "provider": normalized_provider,
        "workflow_name": None,
        "experimental": True,
    }


def build_identity_research_runtime_state(
    *,
    provider: str | None = None,
) -> dict[str, Any]:
    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider:
        return _build_provider_runtime_state(normalized_provider)

    providers_payload = {
        provider_id: _build_provider_runtime_state(provider_id)
        for provider_id in IDENTITY_RESEARCH_SUPPORTED_PROVIDERS
    }
    return {
        "ok": all(
            provider_state.get("ok") is True
            for provider_state in providers_payload.values()
        ),
        "mode": IDENTITY_RESEARCH_MODE,
        "provider": None,
        "providers": providers_payload,
        "supported_providers": list(IDENTITY_RESEARCH_SUPPORTED_PROVIDERS),
        "default_provider": IDENTITY_RESEARCH_DEFAULT_PROVIDER,
        "experimental": True,
    }


def run_identity_research(
    *,
    prompt: str,
    reference_image_path: Path | None,
    provider: str = IDENTITY_RESEARCH_DEFAULT_PROVIDER,
    checkpoint: str | None = None,
    workflow: str | None = None,
    negative_prompt: str = "",
    seed: int = -1,
    steps: int | None = None,
    cfg: float | None = None,
    width: int | None = None,
    height: int | None = None,
    wait: bool = False,
    output_dir: Path | None = None,
    logger: Callable[[str], None] | None = None,
    error_logger: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    normalized_provider = (
        str(provider or "").strip().lower() or IDENTITY_RESEARCH_DEFAULT_PROVIDER
    )
    if normalized_provider not in IDENTITY_RESEARCH_SUPPORTED_PROVIDERS:
        return {
            "status": "error",
            "mode": IDENTITY_RESEARCH_MODE,
            "prompt_id": None,
            "output_file": None,
            "error_type": "invalid_request",
            "blocker": "unsupported_identity_research_provider",
            "provider": normalized_provider,
        }

    call_kwargs: dict[str, Any] = {
        "prompt": prompt,
        "reference_image_path": reference_image_path,
        "checkpoint": checkpoint,
        "workflow": workflow,
        "negative_prompt": negative_prompt,
        "seed": seed,
        "wait": wait,
        "output_dir": output_dir,
        "logger": logger,
        "error_logger": error_logger,
    }
    if steps is not None:
        call_kwargs["steps"] = steps
    if cfg is not None:
        call_kwargs["cfg"] = cfg
    if width is not None:
        call_kwargs["width"] = width
    if height is not None:
        call_kwargs["height"] = height

    if normalized_provider == IDENTITY_RESEARCH_DEFAULT_PROVIDER:
        result = dict(run_identity_reference(**call_kwargs))
        workflow_name = Path(str(workflow or IDENTITY_WORKFLOW_NAME)).name
        if result.get("identity_reference_mode") is None:
            result["identity_reference_mode"] = IDENTITY_REFERENCE_MODE
    else:
        result = dict(run_pulid_v11_identity_research(**call_kwargs))
        workflow_name = Path(str(workflow or PULID_V11_WORKFLOW_NAME)).name

    result["mode"] = IDENTITY_RESEARCH_MODE
    result["provider"] = normalized_provider
    result["experimental"] = True
    result["research_path"] = IDENTITY_RESEARCH_MODE
    result["backbone"] = normalized_provider
    result["workflow_name"] = workflow_name
    return result
