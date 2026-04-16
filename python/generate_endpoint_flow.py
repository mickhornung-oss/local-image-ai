from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def build_generate_endpoint_error(
    *,
    mode: str | None,
    request_id: str,
    failure: Mapping[str, object] | None,
    error_response_builder: Callable[..., dict],
    fallback_http_status: HTTPStatus,
    fallback_error_type: str,
    fallback_blocker: str,
) -> tuple[HTTPStatus, dict]:
    payload = failure if isinstance(failure, Mapping) else {}
    http_status = payload.get("http_status")
    resolved_http_status = (
        http_status if isinstance(http_status, HTTPStatus) else fallback_http_status
    )
    resolved_error_type = str(payload.get("error_type") or fallback_error_type)
    resolved_blocker = str(payload.get("blocker") or fallback_blocker)
    return (
        resolved_http_status,
        error_response_builder(
            mode=mode,
            error_type=resolved_error_type,
            blocker=resolved_blocker,
            request_id=request_id,
        ),
    )


def try_begin_generate_render(
    *,
    request_id: str,
    try_begin_render: Callable[[str], bool],
    busy_response_builder: Callable[..., dict],
) -> tuple[HTTPStatus, dict] | None:
    if try_begin_render(request_id):
        return None
    return HTTPStatus.CONFLICT, busy_response_builder(request_id=request_id)


def execute_generate_endpoint(
    *,
    render_callable: Callable[[], Mapping[str, object] | dict],
    finalize_callable: Callable[[Mapping[str, object] | dict], tuple[HTTPStatus, dict]],
    server_error_callable: Callable[[], tuple[HTTPStatus, dict]],
    finish_render: Callable[[], None],
) -> tuple[HTTPStatus, dict]:
    try:
        result = render_callable()
        return finalize_callable(result)
    except Exception:
        return server_error_callable()
    finally:
        finish_render()
