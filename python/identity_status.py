from __future__ import annotations

from http import HTTPStatus
from typing import Callable, Mapping


def resolve_identity_reference_status_code(
    *,
    error_type: str | None,
    blocker: str | None,
    service_unavailable_blockers: set[str] | frozenset[str],
) -> HTTPStatus:
    if error_type == "invalid_request":
        return HTTPStatus.BAD_REQUEST
    if error_type == "timeout":
        return HTTPStatus.GATEWAY_TIMEOUT
    if blocker in service_unavailable_blockers:
        return HTTPStatus.SERVICE_UNAVAILABLE
    if error_type == "api_error":
        return HTTPStatus.INTERNAL_SERVER_ERROR
    return HTTPStatus.BAD_REQUEST


def resolve_identity_multi_reference_status_code(
    *,
    error_type: str | None,
    blocker: str | None,
    reference_status_resolver: Callable[..., HTTPStatus],
) -> HTTPStatus:
    if blocker == "insufficient_multi_reference_images":
        return HTTPStatus.BAD_REQUEST
    if blocker in {
        "missing_multi_reference_file",
        "invalid_multi_reference_metadata",
        "invalid_multi_reference_image",
        "duplicate_multi_reference_slot",
    }:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    return reference_status_resolver(error_type=error_type, blocker=blocker)


def resolve_identity_transfer_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    if blocker in {"missing_identity_head_reference", "missing_target_body_image"}:
        return HTTPStatus.BAD_REQUEST
    if blocker in {
        "identity_transfer_store_unavailable",
        "missing_identity_transfer_file",
        "invalid_identity_transfer_metadata",
        "invalid_identity_transfer_image",
    }:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    if error_type == "invalid_request":
        return HTTPStatus.BAD_REQUEST
    return HTTPStatus.INTERNAL_SERVER_ERROR


def resolve_identity_transfer_generate_status_code(
    *,
    error_type: str | None,
    blocker: str | None,
    reference_status_resolver: Callable[..., HTTPStatus],
) -> HTTPStatus:
    if blocker in {"missing_identity_head_reference", "missing_target_body_image"}:
        return HTTPStatus.BAD_REQUEST
    if blocker in {
        "identity_transfer_store_unavailable",
        "missing_identity_transfer_file",
        "invalid_identity_transfer_metadata",
        "invalid_identity_transfer_image",
    }:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    return reference_status_resolver(error_type=error_type, blocker=blocker)


def resolve_identity_readiness_http_status(
    readiness_state: Mapping[str, object] | None,
    *,
    status_code_resolver: Callable[..., HTTPStatus],
) -> HTTPStatus:
    state = readiness_state if isinstance(readiness_state, Mapping) else {}
    if state.get("ok") is True:
        return HTTPStatus.OK
    error_type = state.get("error_type") if isinstance(state.get("error_type"), str) else None
    blocker = state.get("blocker") if isinstance(state.get("blocker"), str) else None
    return status_code_resolver(error_type=error_type, blocker=blocker)


def build_identity_transfer_status_payload(
    *,
    roles: tuple[str, ...] | list[str],
    required_roles: tuple[str, ...] | list[str],
    role_dir_state_resolver: Callable[[str], tuple[bool, str | None]],
    role_image_state_resolver: Callable[[str], dict | None],
) -> dict:
    required_role_set = set(required_roles)
    roles_payload: list[dict] = []
    blockers: list[str] = []
    occupied_count = 0
    for role in roles:
        dir_accessible, dir_error = role_dir_state_resolver(role)
        current_item = role_image_state_resolver(role)
        required = role in required_role_set
        occupied = dir_accessible and current_item is not None
        if not dir_accessible:
            blockers.append(dir_error or f"{role}_dir_not_accessible")
        if occupied:
            occupied_count += 1
        elif required:
            blockers.append(f"missing_{role}")
        roles_payload.append(
            {
                "role": role,
                "required": required,
                "occupied": occupied,
                "dir_accessible": dir_accessible,
                "dir_error": None if dir_accessible else (dir_error or f"{role}_dir_not_accessible"),
                "image": current_item,
            }
        )

    return {
        "status": "ok",
        "v6_3_transfer_ready": not blockers,
        "required_roles": list(required_roles),
        "optional_roles": [role for role in roles if role not in required_role_set],
        "occupied_role_count": occupied_count,
        "roles": roles_payload,
        "blockers": blockers,
    }
