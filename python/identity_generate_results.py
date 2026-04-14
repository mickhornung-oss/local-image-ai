from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def finalize_identity_generate_outcome(
    result: Mapping[str, object] | None,
    *,
    request_id: str,
    mode: str,
    prompt: str,
    checkpoint: str | None,
    default_failed_blocker: str,
    status_code_resolver: Callable[..., HTTPStatus],
    finalize_result: Callable[..., tuple[HTTPStatus, dict]],
    error_response_builder: Callable[..., dict],
    extra_metadata: dict | None = None,
) -> tuple[HTTPStatus, dict]:
    payload = result if isinstance(result, Mapping) else {}
    if payload.get("status") == "ok":
        return finalize_result(
            payload,
            request_id,
            prompt=prompt,
            checkpoint=str(payload.get("checkpoint") or checkpoint or ""),
            use_input_image=False,
            use_inpainting=False,
            extra_metadata=extra_metadata,
        )

    error_type = str(payload.get("error_type") or "api_error")
    blocker = str(payload.get("blocker") or default_failed_blocker)
    return (
        status_code_resolver(
            error_type=str(payload.get("error_type") or ""),
            blocker=str(payload.get("blocker") or ""),
        ),
        error_response_builder(
            mode=mode,
            error_type=error_type,
            blocker=blocker,
            prompt_id=payload.get("prompt_id") if isinstance(payload.get("prompt_id"), str) else None,
            request_id=request_id,
        ),
    )


def build_identity_generate_server_error(
    *,
    mode: str,
    request_id: str,
    error_response_builder: Callable[..., dict],
) -> tuple[HTTPStatus, dict]:
    return (
        HTTPStatus.INTERNAL_SERVER_ERROR,
        error_response_builder(
            mode=mode,
            error_type="api_error",
            blocker="server_error",
            request_id=request_id,
        ),
    )


def build_identity_generate_error(
    *,
    http_status: HTTPStatus,
    mode: str,
    error_type: str,
    blocker: str,
    request_id: str,
    error_response_builder: Callable[..., dict],
) -> tuple[HTTPStatus, dict]:
    return (
        http_status,
        error_response_builder(
            mode=mode,
            error_type=error_type,
            blocker=blocker,
            request_id=request_id,
        ),
    )
