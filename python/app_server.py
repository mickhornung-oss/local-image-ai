import argparse
import base64
import binascii
import itertools
import json
import mimetypes
import os
import secrets
import shutil
import sys
import threading
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_policy_default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import parse_qs, quote, unquote, urlparse

import checkpoint_inventory
from comfy_client import ComfyClient, ComfyClientError
from identity_transfer_adapter import build_identity_transfer_adapter_state
from multi_reference_adapter import build_multi_reference_adapter_state
from PIL import Image, UnidentifiedImageError
from render_identity_transfer import (
    IDENTITY_TRANSFER_MODE,
    build_identity_transfer_runtime_state,
    run_identity_transfer,
)
from render_text2img import (
    DEFAULT_BASE_URL,
    DEFAULT_DENOISE_STRENGTH,
    MAX_DENOISE_STRENGTH,
    MIN_DENOISE_STRENGTH,
    INPUT_IMAGE_EXTENSIONS,
    MINIMAL_WORKFLOW_NAME,
    PLACEHOLDER_WORKFLOW_NAME,
    comfy_output_dir,
    repo_root,
    run_render,
)
from render_identity_reference import (
    IDENTITY_REFERENCE_MODE,
    build_identity_runtime_state,
    run_identity_reference,
)
from render_identity_multi_reference import (
    IDENTITY_MULTI_REFERENCE_MODE,
    build_identity_multi_reference_runtime_state,
    run_identity_multi_reference,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8090
VALID_MODES = {"auto", "sdxl", "placeholder"}
VALID_RUNNER_STATUSES = {"started", "already_running", "busy", "error"}
RUNNER_STATUS_PATH = repo_root() / "vendor" / "ComfyUI" / "logs" / "run_comfyui.status.json"
OUTPUT_ROUTE_PREFIX = "/output/"
INPUT_ROUTE_PREFIX = "/input/"
REFERENCE_ROUTE_PREFIX = "/reference/"
MASK_ROUTE_PREFIX = "/mask/"
MULTI_REFERENCE_ROUTE_PREFIX = "/multi-reference/"
IDENTITY_TRANSFER_ROUTE_PREFIX = "/identity-transfer/"
RESULT_FILE_ROUTE_PREFIX = "/results/files/"
RESULT_DOWNLOAD_ROUTE_PREFIX = "/results/download/"
RESULT_LIST_PATH = "/results"
INPUT_IMAGE_UPLOAD_PATH = "/input-image"
INPUT_IMAGE_RESET_PATH = "/input-image/current"
REFERENCE_IMAGE_UPLOAD_PATH = "/identity-reference-image"
REFERENCE_IMAGE_RESET_PATH = "/identity-reference-image/current"
MULTI_REFERENCE_IMAGE_UPLOAD_PATH = "/identity-multi-reference-image"
MULTI_REFERENCE_IMAGES_RESET_PATH = "/identity-multi-reference-images/current"
MULTI_REFERENCE_IMAGE_SLOT_RESET_PREFIX = "/identity-multi-reference-image/slot/"
MULTI_REFERENCE_STATUS_PATH = "/identity-multi-reference/status"
MULTI_REFERENCE_READINESS_PATH = "/identity-multi-reference/readiness"
IDENTITY_TRANSFER_ROLE_UPLOAD_PATH = "/identity-transfer-role-image"
IDENTITY_TRANSFER_ROLES_RESET_PATH = "/identity-transfer-role-images/current"
IDENTITY_TRANSFER_ROLE_RESET_PREFIX = "/identity-transfer-role-image/"
IDENTITY_TRANSFER_STATUS_PATH = "/identity-transfer/status"
IDENTITY_TRANSFER_READINESS_PATH = "/identity-transfer/readiness"
IDENTITY_TRANSFER_GENERATE_PATH = "/identity-transfer/generate"
IDENTITY_MULTI_REFERENCE_GENERATE_PATH = "/identity-multi-reference/generate"
IDENTITY_REFERENCE_GENERATE_PATH = "/identity-reference/generate"
IDENTITY_REFERENCE_READINESS_PATH = "/identity-reference/readiness"
MASK_IMAGE_RESET_PATH = "/mask-image/current"
MASK_IMAGE_EDITOR_PATH = "/mask-image/editor"
TEXT_SERVICE_PROMPT_TEST_PATH = "/text-service/prompt-test"
UPLOAD_MAX_BYTES = 25 * 1024 * 1024
RESULTS_DEFAULT_LIMIT = 20
RESULTS_MAX_LIMIT = 100
RESULT_RETENTION_DEFAULT = 50
RESULT_RETENTION_ENV_VAR = "LOCAL_IMAGE_APP_RESULT_RETENTION"
TEXT_SERVICE_CONFIG_PATH = repo_root() / "config" / "text_service.json"
TEXT_SERVICE_PROBE_TIMEOUT = 2.0
TEXT_SERVICE_PROMPT_TIMEOUT = 60.0
TEXT_SERVICE_PROMPT_MAX_LENGTH = 2000
VALID_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VALID_UPLOAD_FORMATS = {
    "PNG": (".png", "image/png"),
    "JPEG": (".jpg", "image/jpeg"),
    "WEBP": (".webp", "image/webp"),
}
MAX_MULTI_REFERENCE_SLOTS = 3
IDENTITY_TRANSFER_ROLES = (
    "identity_head_reference",
    "target_body_image",
    "pose_reference",
    "transfer_mask",
)
IDENTITY_TRANSFER_REQUIRED_ROLES = (
    "identity_head_reference",
    "target_body_image",
)
IDENTITY_TRANSFER_ROLE_SET = set(IDENTITY_TRANSFER_ROLES)
VALID_UPLOAD_MIME_TYPES = {mime_type for _, mime_type in VALID_UPLOAD_FORMATS.values()}
VALID_UPLOAD_SOURCE_TYPES = {"file", "clipboard", "mask"}
IDENTITY_REFERENCE_SERVICE_UNAVAILABLE_BLOCKERS = {
    "identity_workflow_missing",
    "identity_workflow_invalid",
    "identity_models_missing",
    "identity_runtime_unavailable",
    "identity_runtime_version_unsupported",
    "identity_runtime_invalid",
    "identity_nodes_unreachable",
    "identity_nodes_invalid",
    "identity_nodes_missing",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def app_root() -> Path:
    return repo_root() / "web"


def output_root() -> Path:
    return comfy_output_dir().resolve()


def input_root() -> Path:
    return (repo_root() / "data" / "input_images").resolve()


def reference_root() -> Path:
    return (repo_root() / "data" / "reference_images").resolve()


def multi_reference_root() -> Path:
    return (repo_root() / "data" / "multi_reference_images").resolve()


def mask_root() -> Path:
    return (repo_root() / "data" / "mask_images").resolve()


def identity_transfer_root() -> Path:
    return (repo_root() / "data" / "identity_transfer_roles").resolve()


def identity_transfer_role_root(role: str) -> Path:
    return (identity_transfer_root() / role).resolve()


def result_root() -> Path:
    return (repo_root() / "data" / "results").resolve()


class UploadRequestError(Exception):
    def __init__(
        self,
        *,
        status_code: HTTPStatus,
        error_type: str,
        blocker: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.blocker = blocker
        self.message = message


class ResultStoreError(Exception):
    def __init__(
        self,
        *,
        status_code: HTTPStatus,
        error_type: str,
        blocker: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.blocker = blocker
        self.message = message


def read_json_file_detail(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, "missing"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "invalid_json"
    except OSError:
        return None, "read_failed"

    if not isinstance(payload, dict):
        return None, "invalid_payload"
    return payload, None


def fetch_json_detail(url: str, *, timeout: float) -> tuple[dict | None, str | None]:
    try:
        with urllib_request.urlopen(url, timeout=timeout) as response:
            if response.status != HTTPStatus.OK:
                return None, f"http_{response.status}"
            raw_body = response.read()
    except urllib_error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except urllib_error.URLError:
        return None, "unreachable"
    except TimeoutError:
        return None, "timeout"
    except OSError:
        return None, "unreachable"

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "invalid_json"

    if not isinstance(payload, dict):
        return None, "invalid_payload"
    return payload, None


def post_json_detail(url: str, *, timeout: float, payload: dict) -> tuple[dict | None, str | None, int | None]:
    data = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read()
            status_code = response.status
    except urllib_error.HTTPError as exc:
        status_code = exc.code
        raw_body = exc.read()
    except urllib_error.URLError:
        return None, "unreachable", None
    except TimeoutError:
        return None, "timeout", None
    except OSError:
        return None, "unreachable", None

    try:
        decoded_payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "invalid_json", status_code

    if not isinstance(decoded_payload, dict):
        return None, "invalid_payload", status_code
    return decoded_payload, None, status_code


def load_text_service_config_state() -> tuple[bool, dict | None, str | None]:
    payload, error = read_json_file_detail(TEXT_SERVICE_CONFIG_PATH)
    if error is not None:
        return False, None, None if error == "missing" else "config_unreadable"

    enabled = payload.get("enabled")
    host = payload.get("host")
    port = payload.get("port")
    service_name = payload.get("service_name")
    model_status = payload.get("model_status")
    runner_type = payload.get("runner_type")
    model_path = payload.get("model_path")

    if enabled is not True:
        return False, None, None
    if not isinstance(host, str) or host.strip() != "127.0.0.1":
        return False, None, "config_invalid"
    if not isinstance(port, int) or port < 1 or port > 65535:
        return False, None, "config_invalid"

    return True, {
        "host": "127.0.0.1",
        "port": port,
        "service_name": service_name.strip() if isinstance(service_name, str) and service_name.strip() else None,
        "model_status": model_status.strip() if isinstance(model_status, str) and model_status.strip() else None,
        "runner_type": runner_type.strip() if isinstance(runner_type, str) and runner_type.strip() else None,
        "model_configured": isinstance(model_path, str) and bool(model_path.strip()),
    }, None


def collect_text_service_state() -> dict:
    configured, config, config_error = load_text_service_config_state()
    state = {
        "text_service_configured": configured,
        "text_service_reachable": False,
        "text_service_error": config_error,
        "text_service": {
            "service_name": None,
            "service_mode": None,
            "runner_type": None,
            "runner_present": None,
            "runner_reachable": None,
            "runner_startable": None,
            "stub_mode": None,
            "inference_available": None,
            "model_status": None,
            "model_configured": None,
            "model_present": None,
        },
    }

    if not configured or config is None:
        return state

    base_url = f"http://{config['host']}:{config['port']}"
    health_payload, health_error = fetch_json_detail(f"{base_url}/health", timeout=TEXT_SERVICE_PROBE_TIMEOUT)
    if health_error is not None or health_payload is None:
        state["text_service_error"] = "unreachable" if health_error in {"unreachable", "timeout"} else "invalid_health"
        state["text_service"]["service_name"] = config["service_name"]
        state["text_service"]["runner_type"] = config["runner_type"]
        state["text_service"]["model_status"] = config["model_status"]
        state["text_service"]["model_configured"] = config["model_configured"]
        return state

    service_name = health_payload.get("service")
    if not isinstance(service_name, str) or not service_name.strip():
        state["text_service_error"] = "invalid_health"
        return state

    expected_service_name = config["service_name"]
    if expected_service_name and service_name.strip() != expected_service_name:
        state["text_service_error"] = "unexpected_service"
        return state

    state["text_service_reachable"] = True
    state["text_service_error"] = None
    state["text_service"] = {
        "service_name": service_name.strip(),
        "service_mode": health_payload.get("service_mode") if isinstance(health_payload.get("service_mode"), str) else None,
        "runner_type": health_payload.get("runner_type") if isinstance(health_payload.get("runner_type"), str) else config["runner_type"],
        "runner_present": health_payload.get("runner_present") if isinstance(health_payload.get("runner_present"), bool) else None,
        "runner_reachable": health_payload.get("runner_reachable") if isinstance(health_payload.get("runner_reachable"), bool) else None,
        "runner_startable": health_payload.get("runner_startable") if isinstance(health_payload.get("runner_startable"), bool) else None,
        "stub_mode": health_payload.get("stub_mode") is True,
        "inference_available": health_payload.get("inference_available") if isinstance(health_payload.get("inference_available"), bool) else None,
        "model_status": health_payload.get("model_status") if isinstance(health_payload.get("model_status"), str) else config["model_status"],
        "model_configured": health_payload.get("model_configured") if isinstance(health_payload.get("model_configured"), bool) else config["model_configured"],
        "model_present": health_payload.get("model_present") if isinstance(health_payload.get("model_present"), bool) else None,
    }

    info_payload, info_error = fetch_json_detail(f"{base_url}/info", timeout=TEXT_SERVICE_PROBE_TIMEOUT)
    if info_error is None and info_payload is not None:
        if isinstance(info_payload.get("service_mode"), str) and info_payload.get("service_mode").strip():
            state["text_service"]["service_mode"] = info_payload.get("service_mode").strip()
        if isinstance(info_payload.get("runner_type"), str) and info_payload.get("runner_type").strip():
            state["text_service"]["runner_type"] = info_payload.get("runner_type").strip()
        if isinstance(info_payload.get("runner_present"), bool):
            state["text_service"]["runner_present"] = info_payload.get("runner_present")
        if isinstance(info_payload.get("runner_reachable"), bool):
            state["text_service"]["runner_reachable"] = info_payload.get("runner_reachable")
        if isinstance(info_payload.get("runner_startable"), bool):
            state["text_service"]["runner_startable"] = info_payload.get("runner_startable")
        state["text_service"]["stub_mode"] = info_payload.get("stub_mode") is True
        if isinstance(info_payload.get("inference_available"), bool):
            state["text_service"]["inference_available"] = info_payload.get("inference_available")
        if isinstance(info_payload.get("model_status"), str) and info_payload.get("model_status").strip():
            state["text_service"]["model_status"] = info_payload.get("model_status").strip()
        if isinstance(info_payload.get("model_configured"), bool):
            state["text_service"]["model_configured"] = info_payload.get("model_configured")
        if isinstance(info_payload.get("model_present"), bool):
            state["text_service"]["model_present"] = info_payload.get("model_present")
    elif info_error is not None:
        state["text_service_error"] = "info_unavailable"

    return state


def normalize_text_service_prompt(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, "prompt_not_string"

    normalized_prompt = value.strip()
    if not normalized_prompt:
        return None, "empty_prompt"

    if len(normalized_prompt) > TEXT_SERVICE_PROMPT_MAX_LENGTH:
        return None, "prompt_too_long"

    return normalized_prompt, None


def build_text_service_prompt_test_response(
    *,
    ok: bool,
    text_service_reachable: bool,
    stub: bool | None,
    response_text: str | None,
    error: str | None,
    error_message: str | None,
    service_name: str | None,
    model_status: str | None,
) -> dict:
    return {
        "ok": ok,
        "text_service_reachable": text_service_reachable,
        "stub": stub,
        "response_text": response_text,
        "error": error,
        "error_message": error_message,
        "service": service_name,
        "model_status": model_status,
    }


def probe_comfyui() -> tuple[bool, str | None]:
    try:
        ComfyClient(base_url=DEFAULT_BASE_URL, timeout=5).health_check()
        return True, None
    except ComfyClientError as exc:
        return False, str(exc)


def resolve_identity_reference_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    if error_type == "invalid_request":
        return HTTPStatus.BAD_REQUEST
    if error_type == "timeout":
        return HTTPStatus.GATEWAY_TIMEOUT
    if blocker in IDENTITY_REFERENCE_SERVICE_UNAVAILABLE_BLOCKERS:
        return HTTPStatus.SERVICE_UNAVAILABLE
    if error_type == "api_error":
        return HTTPStatus.INTERNAL_SERVER_ERROR
    return HTTPStatus.BAD_REQUEST


def resolve_identity_multi_reference_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    if blocker == "insufficient_multi_reference_images":
        return HTTPStatus.BAD_REQUEST
    if blocker in {"missing_multi_reference_file", "invalid_multi_reference_metadata", "invalid_multi_reference_image", "duplicate_multi_reference_slot"}:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    return resolve_identity_reference_status_code(error_type=error_type, blocker=blocker)


def resolve_identity_transfer_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    if blocker in {"missing_identity_head_reference", "missing_target_body_image"}:
        return HTTPStatus.BAD_REQUEST
    if blocker in {"identity_transfer_store_unavailable", "missing_identity_transfer_file", "invalid_identity_transfer_metadata", "invalid_identity_transfer_image"}:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    if error_type == "invalid_request":
        return HTTPStatus.BAD_REQUEST
    return HTTPStatus.INTERNAL_SERVER_ERROR


def resolve_identity_transfer_generate_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    if blocker in {"missing_identity_head_reference", "missing_target_body_image"}:
        return HTTPStatus.BAD_REQUEST
    if blocker in {"identity_transfer_store_unavailable", "missing_identity_transfer_file", "invalid_identity_transfer_metadata", "invalid_identity_transfer_image"}:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    return resolve_identity_reference_status_code(error_type=error_type, blocker=blocker)


def build_generate_response(
    *,
    status: str,
    mode: str | None,
    output_file: str | None,
    error_type: str | None,
    blocker: str | None,
    prompt_id: str | None,
    request_id: str | None,
) -> dict:
    return {
        "status": status,
        "mode": mode,
        "output_file": output_file,
        "error_type": error_type,
        "blocker": blocker,
        "prompt_id": prompt_id,
        "request_id": request_id,
    }


def build_error_response(
    *,
    mode: str | None,
    error_type: str,
    blocker: str,
    prompt_id: str | None = None,
    request_id: str | None = None,
) -> dict:
    return build_generate_response(
        status="error",
        mode=mode,
        output_file=None,
        error_type=error_type,
        blocker=blocker,
        prompt_id=prompt_id,
        request_id=request_id,
    )


def build_busy_response(*, request_id: str | None) -> dict:
    return build_generate_response(
        status="busy",
        mode=None,
        output_file=None,
        error_type="busy",
        blocker="render_in_progress",
        prompt_id=None,
        request_id=request_id,
    )


def build_upload_success_response(payload: dict) -> dict:
    return {
        "status": "ok",
        "ok": True,
        "image_id": payload["image_id"],
        "source_type": payload["source_type"],
        "original_name": payload["original_name"],
        "stored_name": payload["stored_name"],
        "mime_type": payload["mime_type"],
        "size_bytes": payload["size_bytes"],
        "width": payload["width"],
        "height": payload["height"],
        "preview_url": payload["preview_url"],
    }


def build_multi_reference_upload_success_response(payload: dict) -> dict:
    response_payload = build_upload_success_response(payload)
    response_payload["slot_index"] = payload["slot_index"]
    response_payload["created_at"] = payload.get("created_at")
    return response_payload


def build_identity_transfer_upload_success_response(payload: dict) -> dict:
    response_payload = build_upload_success_response(payload)
    response_payload["role"] = payload["role"]
    response_payload["created_at"] = payload.get("created_at")
    return response_payload


def build_upload_error_response(*, error_type: str, blocker: str, message: str) -> dict:
    return {
        "status": "error",
        "ok": False,
        "error_type": error_type,
        "blocker": blocker,
        "message": message,
    }


def build_results_error_response(*, error_type: str, blocker: str, message: str) -> dict:
    return {
        "status": "error",
        "error_type": error_type,
        "blocker": blocker,
        "message": message,
    }


def output_dir_access_state() -> tuple[bool, str | None]:
    root = output_root()
    if not root.exists():
        return False, "output_dir_missing"
    if not root.is_dir():
        return False, "output_dir_not_directory"
    if not os.access(root, os.R_OK | os.X_OK):
        return False, "output_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def input_dir_access_state() -> tuple[bool, str | None]:
    root = input_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, "input_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "input_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def reference_dir_access_state() -> tuple[bool, str | None]:
    root = reference_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, "reference_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "reference_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def multi_reference_dir_access_state() -> tuple[bool, str | None]:
    root = multi_reference_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, "multi_reference_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "multi_reference_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def mask_dir_access_state() -> tuple[bool, str | None]:
    root = mask_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, "mask_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "mask_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def identity_transfer_dir_access_state(role: str) -> tuple[bool, str | None]:
    root = identity_transfer_role_root(role)
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, "identity_transfer_role_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "identity_transfer_role_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def results_dir_access_state() -> tuple[bool, str | None]:
    root = result_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)

    if not root.is_dir():
        return False, "results_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "results_dir_not_accessible"
    try:
        next(root.iterdir(), None)
    except OSError as exc:
        return False, str(exc)
    return True, None


def resolve_internal_output_path(output_file: str | Path | None) -> tuple[Path | None, str | None]:
    if output_file is None:
        return None, "generated_file_not_accessible"

    candidate = Path(output_file)
    if not candidate.is_absolute():
        candidate = output_root() / candidate

    resolved_output = candidate.resolve()
    try:
        resolved_output.relative_to(output_root())
    except ValueError:
        return None, "generated_file_not_accessible"
    return resolved_output, None


def is_accessible_output_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except OSError:
        return False
    return True


def output_path_to_web_path(path: Path) -> str:
    relative = path.relative_to(output_root())
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{OUTPUT_ROUTE_PREFIX}{encoded}"


def input_path_to_web_path(path: Path) -> str:
    relative = path.relative_to(input_root())
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{INPUT_ROUTE_PREFIX}{encoded}"


def reference_path_to_web_path(path: Path) -> str:
    relative = path.relative_to(reference_root())
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{REFERENCE_ROUTE_PREFIX}{encoded}"


def multi_reference_path_to_web_path(path: Path) -> str:
    relative = path.relative_to(multi_reference_root())
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{MULTI_REFERENCE_ROUTE_PREFIX}{encoded}"


def mask_path_to_web_path(path: Path) -> str:
    relative = path.relative_to(mask_root())
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{MASK_ROUTE_PREFIX}{encoded}"


def identity_transfer_path_to_web_path(path: Path, role: str) -> str:
    relative = path.relative_to(identity_transfer_role_root(role))
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{IDENTITY_TRANSFER_ROUTE_PREFIX}{quote(role)}/{encoded}"


def result_path_to_web_path(path: Path) -> str:
    relative = path.relative_to(result_root())
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{RESULT_FILE_ROUTE_PREFIX}{encoded}"


def result_id_to_download_url(result_id: str) -> str:
    return f"{RESULT_DOWNLOAD_ROUTE_PREFIX}{quote(result_id)}"


def map_internal_output_to_web_path(output_file: str | Path | None) -> tuple[str | None, str | None]:
    resolved_output, error = resolve_internal_output_path(output_file)
    if resolved_output is None:
        return None, error
    if not is_accessible_output_file(resolved_output):
        return None, "generated_file_not_accessible"
    return output_path_to_web_path(resolved_output), None


def resolve_output_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(OUTPUT_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(OUTPUT_ROUTE_PREFIX))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = output_root().joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(output_root())
    except ValueError:
        return None
    return candidate


def resolve_input_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(INPUT_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(INPUT_ROUTE_PREFIX))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = input_root().joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(input_root())
    except ValueError:
        return None
    return candidate


def resolve_reference_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(REFERENCE_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(REFERENCE_ROUTE_PREFIX))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = reference_root().joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(reference_root())
    except ValueError:
        return None
    return candidate


def resolve_multi_reference_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(MULTI_REFERENCE_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(MULTI_REFERENCE_ROUTE_PREFIX))
    if not relative:
        return None

    normalized_parts = PurePosixPath(relative).parts
    if not normalized_parts:
        return None
    if any(part in {"", ".", ".."} for part in normalized_parts):
        return None

    candidate = (multi_reference_root() / Path(*normalized_parts)).resolve()
    try:
        candidate.relative_to(multi_reference_root())
    except ValueError:
        return None
    return candidate


def resolve_mask_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(MASK_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(MASK_ROUTE_PREFIX))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = mask_root().joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(mask_root())
    except ValueError:
        return None
    return candidate


def resolve_identity_transfer_role_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(IDENTITY_TRANSFER_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(IDENTITY_TRANSFER_ROUTE_PREFIX))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) < 2:
        return None

    role = str(pure_path.parts[0]).strip()
    if role not in IDENTITY_TRANSFER_ROLE_SET:
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts[1:]:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = identity_transfer_role_root(role).joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(identity_transfer_role_root(role))
    except ValueError:
        return None
    return candidate


def resolve_result_request_path(request_path: str) -> Path | None:
    if not request_path.startswith(RESULT_FILE_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(RESULT_FILE_ROUTE_PREFIX))
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    safe_parts: list[str] = []
    for part in pure_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            return None
        safe_parts.append(part)

    if not safe_parts:
        return None

    candidate = result_root().joinpath(*safe_parts).resolve()
    try:
        candidate.relative_to(result_root())
    except ValueError:
        return None
    return candidate


def resolve_result_download_request_id(request_path: str) -> str | None:
    if not request_path.startswith(RESULT_DOWNLOAD_ROUTE_PREFIX):
        return None

    relative = unquote(request_path.removeprefix(RESULT_DOWNLOAD_ROUTE_PREFIX)).strip()
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute():
        return None

    if len(pure_path.parts) != 1:
        return None

    result_id = pure_path.parts[0].strip()
    if not result_id or result_id in {".", ".."} or Path(result_id).name != result_id:
        return None
    return result_id


def resolve_multi_reference_slot_reset_index(request_path: str) -> int | None:
    if not request_path.startswith(MULTI_REFERENCE_IMAGE_SLOT_RESET_PREFIX):
        return None
    relative = unquote(request_path.removeprefix(MULTI_REFERENCE_IMAGE_SLOT_RESET_PREFIX)).strip()
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) != 1:
        return None
    try:
        return parse_required_multi_reference_slot_index(pure_path.parts[0])
    except ValueError:
        return None


def parse_results_limit(query_string: str) -> int:
    parsed = parse_qs(query_string or "", keep_blank_values=False)
    raw_value = parsed.get("limit", [str(RESULTS_DEFAULT_LIMIT)])[0]
    try:
        numeric_value = int(str(raw_value).strip())
    except ValueError as exc:
        raise ValueError("invalid_results_limit") from exc

    if numeric_value <= 0:
        raise ValueError("invalid_results_limit")
    return min(RESULTS_MAX_LIMIT, numeric_value)


def decode_data_url_image(data_url: object) -> tuple[str, bytes]:
    if not isinstance(data_url, str) or not data_url.strip():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_mask_data",
            message="Mask data is missing.",
        )

    raw_value = data_url.strip()
    if "," not in raw_value:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mask_data",
            message="Mask data URL is invalid.",
        )

    header, encoded = raw_value.split(",", 1)
    if not header.lower().startswith("data:") or ";base64" not in header.lower():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mask_data",
            message="Mask data URL is invalid.",
        )

    mime_type = header[5:].split(";", 1)[0].strip().lower()
    if mime_type not in VALID_UPLOAD_MIME_TYPES:
        raise UploadRequestError(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="invalid_file_type",
            message="Supported formats: .png .jpg .jpeg .webp",
        )

    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mask_data",
            message="Mask data URL is invalid.",
        ) from exc

    if not payload:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_mask_data",
            message="Mask payload is empty.",
        )

    return mime_type, payload


def validate_mode(value: object) -> str:
    normalized = str(value if value is not None else "auto").strip().lower()
    if normalized not in VALID_MODES:
        raise ValueError("invalid_mode")
    return normalized


def parse_boolean_flag(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    raise ValueError("invalid_use_input_image")


def normalize_denoise_strength_value(value: object) -> float:
    if value is None or value == "":
        return DEFAULT_DENOISE_STRENGTH
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_denoise_strength") from exc
    if not numeric_value == numeric_value:
        raise ValueError("invalid_denoise_strength")
    return max(MIN_DENOISE_STRENGTH, min(MAX_DENOISE_STRENGTH, numeric_value))


def sanitize_original_name(filename: str | None) -> str:
    if not isinstance(filename, str):
        return "upload"
    normalized = Path(filename).name.replace("\x00", "").strip()
    return normalized or "upload"


def normalize_upload_source_type(value: str | None) -> str:
    normalized = str(value or "file").strip().lower()
    if normalized not in VALID_UPLOAD_SOURCE_TYPES:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_source_type",
            message="Upload source_type must be file, clipboard, or mask.",
        )
    return normalized


def parse_multipart_image(content_type: str, body: bytes) -> tuple[str, bytes, str]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    source_type = "file"
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "source_type":
                source_type = normalize_upload_source_type(part.get_content())
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if not file_parts:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_file",
            message="No upload file was provided.",
        )
    if len(file_parts) > 1:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one image file is supported.",
        )
    original_name, payload = file_parts[0]
    return original_name, payload, source_type


def parse_multipart_multi_reference_image(content_type: str, body: bytes) -> tuple[str, bytes, int | None]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    slot_index: int | None = None
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "slot_index":
                try:
                    slot_index = parse_optional_multi_reference_slot_index(part.get_content())
                except ValueError as exc:
                    raise UploadRequestError(
                        status_code=HTTPStatus.BAD_REQUEST,
                        error_type="invalid_request",
                        blocker=str(exc),
                        message="slot_index must be auto, empty, or 1-3.",
                    ) from exc
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if not file_parts:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_file",
            message="No upload file was provided.",
        )
    if len(file_parts) > 1:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one image file is supported.",
        )

    original_name, payload = file_parts[0]
    return original_name, payload, slot_index


def parse_multipart_identity_transfer_role_image(content_type: str, body: bytes) -> tuple[str, bytes, str]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    role: str | None = None
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "role":
                try:
                    role = parse_required_identity_transfer_role(part.get_content())
                except ValueError as exc:
                    raise UploadRequestError(
                        status_code=HTTPStatus.BAD_REQUEST,
                        error_type="invalid_request",
                        blocker=str(exc),
                        message="role must be one of the supported V6.3.1 transfer roles.",
                    ) from exc
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if role is None:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_identity_transfer_role",
            message="role must be one of the supported V6.3.1 transfer roles.",
        )
    if not file_parts:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_file",
            message="No upload file was provided.",
        )
    if len(file_parts) > 1:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one image file is supported.",
        )

    original_name, payload = file_parts[0]
    return original_name, payload, role


def inspect_image_upload(original_name: str, payload: bytes) -> dict:
    sanitized_name = sanitize_original_name(original_name)
    original_extension = Path(sanitized_name).suffix.lower()
    if original_extension not in VALID_UPLOAD_EXTENSIONS:
        raise UploadRequestError(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="invalid_file_type",
            message="Supported formats: .png .jpg .jpeg .webp",
        )
    if not payload:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_file",
            message="Uploaded file is empty.",
        )
    if len(payload) > UPLOAD_MAX_BYTES:
        raise UploadRequestError(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            error_type="invalid_upload",
            blocker="file_too_large",
            message="Uploaded file exceeds the size limit.",
        )

    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="invalid_image_data",
            message="Uploaded payload is not a supported image.",
        ) from exc

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        raise UploadRequestError(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="invalid_file_type",
            message="Supported formats: .png .jpg .jpeg .webp",
        )

    extension, mime_type = format_info
    return {
        "original_name": sanitized_name,
        "extension": extension,
        "mime_type": mime_type,
        "size_bytes": len(payload),
        "width": int(width),
        "height": int(height),
    }


def normalize_mask_upload_payload(payload: bytes) -> tuple[bytes, dict]:
    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            grayscale = image.convert("L")
            buffer = BytesIO()
            grayscale.save(buffer, format="PNG")
            normalized_payload = buffer.getvalue()
            width, height = grayscale.size
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="invalid_image_data",
            message="Uploaded payload is not a supported image.",
        ) from exc

    return normalized_payload, {
        "extension": ".png",
        "mime_type": "image/png",
        "size_bytes": len(normalized_payload),
        "width": int(width),
        "height": int(height),
    }


def validate_browser_mask_payload(payload: bytes, source_image_path: Path) -> None:
    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            grayscale = image.convert("L")
            mask_size = grayscale.size
            mask_bbox = grayscale.getbbox()
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="invalid_image_data",
            message="Uploaded payload is not a supported image.",
        ) from exc

    try:
        with Image.open(source_image_path) as source_image:
            source_image.load()
            source_size = source_image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_input_image",
            message="Source image is not readable.",
        ) from exc

    if mask_size != source_size:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="mask_size_mismatch",
            message="Mask dimensions must match the current source image.",
        )

    if mask_bbox is None:
        raise UploadRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_mask",
            message="Mask contains no painted area.",
        )


def clear_stored_images(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for child in root.iterdir():
        if child.is_file():
            child.unlink(missing_ok=True)


def clear_stored_input_images() -> None:
    clear_stored_images(input_root())


def clear_stored_mask_images() -> None:
    clear_stored_images(mask_root())


def clear_stored_reference_images() -> None:
    clear_stored_images(reference_root())


def clear_stored_identity_transfer_role_images(role: str | None = None) -> None:
    if role is None:
        root = identity_transfer_root()
        root.mkdir(parents=True, exist_ok=True)
        for current_role in IDENTITY_TRANSFER_ROLES:
            clear_stored_identity_transfer_role_images(current_role)
        return

    root = identity_transfer_role_root(role)
    clear_stored_images(root)


def parse_required_identity_transfer_role(value: object) -> str:
    normalized = str(value or "").strip()
    if normalized not in IDENTITY_TRANSFER_ROLE_SET:
        raise ValueError("invalid_identity_transfer_role")
    return normalized


def parse_optional_multi_reference_slot_index(value: object) -> int | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized or normalized == "auto":
        return None
    if not normalized.isdigit():
        raise ValueError("invalid_multi_reference_slot")
    parsed = int(normalized)
    if parsed < 1 or parsed > MAX_MULTI_REFERENCE_SLOTS:
        raise ValueError("invalid_multi_reference_slot")
    return parsed


def parse_required_multi_reference_slot_index(value: object) -> int:
    slot_index = parse_optional_multi_reference_slot_index(value)
    if slot_index is None:
        raise ValueError("invalid_multi_reference_slot")
    return slot_index


def resolve_identity_transfer_role_reset_name(request_path: str) -> str | None:
    if not request_path.startswith(IDENTITY_TRANSFER_ROLE_RESET_PREFIX):
        return None
    relative = unquote(request_path.removeprefix(IDENTITY_TRANSFER_ROLE_RESET_PREFIX)).strip()
    pure_path = PurePosixPath(relative)
    if relative == "" or pure_path.is_absolute() or len(pure_path.parts) != 1:
        return None
    try:
        return parse_required_identity_transfer_role(pure_path.parts[0])
    except ValueError:
        return None


def clear_stored_multi_reference_images(*, slot_index: int | None = None) -> None:
    root = multi_reference_root()
    root.mkdir(parents=True, exist_ok=True)

    if slot_index is None:
        clear_stored_images(root)
        return

    for child in root.iterdir():
        if not child.is_file() or child.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
            continue
        description = describe_stored_multi_reference_image(child)
        if description is None or int(description.get("slot_index") or 0) != slot_index:
            continue
        child.unlink(missing_ok=True)
        input_metadata_path(child).unlink(missing_ok=True)


def clear_current_identity_transfer_role(role: str) -> None:
    clear_stored_identity_transfer_role_images(role)


def clear_all_identity_transfer_roles() -> None:
    clear_stored_identity_transfer_role_images()


def input_metadata_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.json")


def write_input_metadata(path: Path, metadata: dict) -> None:
    metadata_path = input_metadata_path(path)
    temp_path = metadata_path.with_name(f"{metadata_path.name}.tmp")
    temp_path.write_text(json.dumps(metadata, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    temp_path.replace(metadata_path)


def read_input_metadata(path: Path) -> dict | None:
    metadata_path = input_metadata_path(path)
    if not metadata_path.exists() or not metadata_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def describe_stored_input_image(path: Path) -> dict | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        return None

    _, mime_type = format_info
    metadata = read_input_metadata(path) or {}
    source_type = str(metadata.get("source_type") or "file").strip().lower()
    if source_type not in VALID_UPLOAD_SOURCE_TYPES:
        source_type = "file"
    original_name = str(metadata.get("original_name") or path.name).strip() or path.name
    return {
        "image_id": path.stem,
        "source_type": source_type,
        "original_name": original_name,
        "stored_name": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
        "width": int(width),
        "height": int(height),
        "preview_url": input_path_to_web_path(path),
    }


def describe_stored_mask_image(path: Path) -> dict | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        return None

    _, mime_type = format_info
    metadata = read_input_metadata(path) or {}
    original_name = str(metadata.get("original_name") or path.name).strip() or path.name
    return {
        "image_id": path.stem,
        "source_type": "mask",
        "original_name": original_name,
        "stored_name": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
        "width": int(width),
        "height": int(height),
        "preview_url": mask_path_to_web_path(path),
    }


def describe_stored_reference_image(path: Path) -> dict | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        return None

    _, mime_type = format_info
    metadata = read_input_metadata(path) or {}
    original_name = str(metadata.get("original_name") or path.name).strip() or path.name
    return {
        "image_id": path.stem,
        "source_type": "reference",
        "original_name": original_name,
        "stored_name": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
        "width": int(width),
        "height": int(height),
        "preview_url": reference_path_to_web_path(path),
    }


def current_input_image_state() -> dict | None:
    root = input_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS
        )
    except OSError:
        return None

    for candidate in candidates:
        description = describe_stored_input_image(candidate)
        if description is not None:
            return description
    return None


def current_mask_image_state() -> dict | None:
    root = mask_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS
        )
    except OSError:
        return None

    for candidate in candidates:
        description = describe_stored_mask_image(candidate)
        if description is not None:
            return description
    return None


def current_reference_image_state() -> dict | None:
    root = reference_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS
        )
    except OSError:
        return None

    for candidate in candidates:
        description = describe_stored_reference_image(candidate)
        if description is not None:
            return description
    return None


def describe_stored_identity_transfer_role_image(path: Path, role: str) -> dict | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        return None

    _, mime_type = format_info
    metadata = read_input_metadata(path) or {}
    original_name = str(metadata.get("original_name") or path.name).strip() or path.name
    created_at = str(metadata.get("created_at") or "").strip()
    return {
        "image_id": path.stem,
        "source_type": "identity_transfer_role",
        "role": role,
        "original_name": original_name,
        "stored_name": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
        "width": int(width),
        "height": int(height),
        "preview_url": identity_transfer_path_to_web_path(path, role),
        "created_at": created_at or None,
    }


def current_identity_transfer_role_state(role: str) -> dict | None:
    root = identity_transfer_role_root(role)
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = sorted(
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS
        )
    except OSError:
        return None

    for candidate in candidates:
        description = describe_stored_identity_transfer_role_image(candidate, role)
        if description is not None:
            return description
    return None


def build_identity_transfer_status_payload() -> dict:
    roles_payload: list[dict] = []
    blockers: list[str] = []
    occupied_count = 0
    for role in IDENTITY_TRANSFER_ROLES:
        dir_accessible, dir_error = identity_transfer_dir_access_state(role)
        current_item = current_identity_transfer_role_state(role)
        required = role in IDENTITY_TRANSFER_REQUIRED_ROLES
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
        "required_roles": list(IDENTITY_TRANSFER_REQUIRED_ROLES),
        "optional_roles": [role for role in IDENTITY_TRANSFER_ROLES if role not in IDENTITY_TRANSFER_REQUIRED_ROLES],
        "occupied_role_count": occupied_count,
        "roles": roles_payload,
        "blockers": blockers,
    }


def list_stored_multi_reference_images() -> list[dict]:
    root = multi_reference_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        candidates = [
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in VALID_UPLOAD_EXTENSIONS
        ]
    except OSError:
        return []

    grouped: dict[int, list[dict]] = {}
    for candidate in candidates:
        description = describe_stored_multi_reference_image(candidate)
        if description is None:
            continue
        grouped.setdefault(int(description["slot_index"]), []).append(description)

    items: list[dict] = []
    for slot_index in sorted(grouped):
        slot_items = grouped[slot_index]
        slot_items.sort(
            key=lambda item: (
                str(item.get("created_at") or ""),
                str(item.get("image_id") or ""),
            ),
            reverse=True,
        )
        items.append(slot_items[0])
    return items


def build_multi_reference_status_payload() -> dict:
    items = list_stored_multi_reference_images()
    item_by_slot = {int(item["slot_index"]): item for item in items}
    slots: list[dict] = []
    for slot_index in range(1, MAX_MULTI_REFERENCE_SLOTS + 1):
        current_item = item_by_slot.get(slot_index)
        slots.append(
            {
                "slot_index": slot_index,
                "occupied": current_item is not None,
                "image": current_item,
            }
        )

    reference_count = len(items)
    return {
        "status": "ok",
        "max_slots": MAX_MULTI_REFERENCE_SLOTS,
        "reference_count": reference_count,
        "multi_reference_ready": reference_count >= 2,
        "slots": slots,
    }


def find_first_free_multi_reference_slot() -> int | None:
    for slot in build_multi_reference_status_payload()["slots"]:
        if slot["occupied"] is not True:
            return int(slot["slot_index"])
    return None


def store_uploaded_image(original_name: str, payload: bytes, source_type: str) -> dict:
    normalized_source_type = normalize_upload_source_type(source_type)
    is_mask_upload = normalized_source_type == "mask"
    root = mask_root() if is_mask_upload else input_root()
    access_state = mask_dir_access_state() if is_mask_upload else input_dir_access_state()
    dir_accessible, dir_error = access_state
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or ("mask_dir_not_accessible" if is_mask_upload else "input_dir_not_accessible"),
            message="Input directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    stored_payload = payload
    if is_mask_upload:
        normalized_payload, normalized_mask_info = normalize_mask_upload_payload(payload)
        stored_payload = normalized_payload
        image_info.update(normalized_mask_info)

    image_id = f"{'mask' if is_mask_upload else 'input'}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = root / stored_name
    temp_path = root / f".{stored_name}.tmp"

    try:
        if is_mask_upload:
            clear_stored_mask_images()
        else:
            clear_stored_input_images()
        temp_path.write_bytes(stored_payload)
        temp_path.replace(final_path)
        write_input_metadata(
            final_path,
            {
                "original_name": image_info["original_name"],
                "source_type": normalized_source_type,
            },
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="input_storage_error",
            message="Uploaded image could not be stored.",
        ) from exc

    stored_image = describe_stored_mask_image(final_path) if is_mask_upload else describe_stored_input_image(final_path)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_image_not_accessible",
            message="Stored image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = normalized_source_type
    return stored_image


def store_reference_image(original_name: str, payload: bytes) -> dict:
    dir_accessible, dir_error = reference_dir_access_state()
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or "reference_dir_not_accessible",
            message="Reference directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    image_id = f"reference-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = reference_root() / stored_name
    temp_path = reference_root() / f".{stored_name}.tmp"

    try:
        clear_stored_reference_images()
        temp_path.write_bytes(payload)
        temp_path.replace(final_path)
        write_input_metadata(
            final_path,
            {
                "original_name": image_info["original_name"],
                "source_type": "reference",
            },
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="reference_storage_error",
            message="Uploaded reference image could not be stored.",
        ) from exc

    stored_image = describe_stored_reference_image(final_path)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_reference_not_accessible",
            message="Stored reference image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = "reference"
    return stored_image


def store_multi_reference_image(original_name: str, payload: bytes, *, slot_index: int | None) -> dict:
    dir_accessible, dir_error = multi_reference_dir_access_state()
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or "multi_reference_dir_not_accessible",
            message="Multi-reference directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    resolved_slot_index = slot_index if slot_index is not None else find_first_free_multi_reference_slot()
    if resolved_slot_index is None:
        raise UploadRequestError(
            status_code=HTTPStatus.CONFLICT,
            error_type="invalid_request",
            blocker="multi_reference_slots_full",
            message="All multi-reference slots are occupied. Choose a slot to replace.",
        )

    created_at = utc_now_iso()
    image_id = f"multi-reference-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = multi_reference_root() / stored_name
    temp_path = multi_reference_root() / f".{stored_name}.tmp"

    try:
        clear_stored_multi_reference_images(slot_index=resolved_slot_index)
        temp_path.write_bytes(payload)
        temp_path.replace(final_path)
        write_input_metadata(
            final_path,
            {
                "original_name": image_info["original_name"],
                "source_type": "multi_reference",
                "slot_index": resolved_slot_index,
                "created_at": created_at,
            },
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="multi_reference_storage_error",
            message="Uploaded multi-reference image could not be stored.",
        ) from exc

    stored_image = describe_stored_multi_reference_image(final_path)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_multi_reference_not_accessible",
            message="Stored multi-reference image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = "multi_reference"
    stored_image["slot_index"] = resolved_slot_index
    stored_image["created_at"] = created_at
    return stored_image


def store_identity_transfer_role_image(original_name: str, payload: bytes, *, role: str) -> dict:
    dir_accessible, dir_error = identity_transfer_dir_access_state(role)
    if not dir_accessible:
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker=dir_error or "identity_transfer_role_dir_not_accessible",
            message="Identity transfer role directory is not writable.",
        )

    image_info = inspect_image_upload(original_name, payload)
    created_at = utc_now_iso()
    image_id = f"{role}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    stored_name = f"{image_id}{image_info['extension']}"
    final_path = identity_transfer_role_root(role) / stored_name
    temp_path = identity_transfer_role_root(role) / f".{stored_name}.tmp"

    try:
        clear_stored_identity_transfer_role_images(role)
        temp_path.write_bytes(payload)
        temp_path.replace(final_path)
        write_input_metadata(
            final_path,
            {
                "original_name": image_info["original_name"],
                "source_type": "identity_transfer_role",
                "role": role,
                "created_at": created_at,
            },
        )
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="identity_transfer_role_storage_error",
            message="Uploaded identity transfer role image could not be stored.",
        ) from exc

    stored_image = describe_stored_identity_transfer_role_image(final_path, role)
    if stored_image is None or not is_accessible_output_file(final_path):
        final_path.unlink(missing_ok=True)
        input_metadata_path(final_path).unlink(missing_ok=True)
        raise UploadRequestError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="upload_error",
            blocker="stored_identity_transfer_role_not_accessible",
            message="Stored identity transfer role image is not accessible.",
        )

    stored_image["original_name"] = image_info["original_name"]
    stored_image["source_type"] = "identity_transfer_role"
    stored_image["role"] = role
    stored_image["created_at"] = created_at
    return stored_image


def describe_stored_multi_reference_image(path: Path) -> dict | None:
    if not path.exists() or not path.is_file() or path.suffix.lower() not in VALID_UPLOAD_EXTENSIONS:
        return None
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        return None

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    if format_info is None:
        return None

    _, mime_type = format_info
    metadata = read_input_metadata(path) or {}
    try:
        slot_index = parse_required_multi_reference_slot_index(metadata.get("slot_index"))
    except ValueError:
        return None
    original_name = str(metadata.get("original_name") or path.name).strip() or path.name
    created_at = str(metadata.get("created_at") or "").strip()
    return {
        "image_id": path.stem,
        "source_type": "multi_reference",
        "slot_index": slot_index,
        "original_name": original_name,
        "stored_name": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
        "width": int(width),
        "height": int(height),
        "preview_url": multi_reference_path_to_web_path(path),
        "created_at": created_at or None,
    }


def clear_current_input_image() -> None:
    clear_stored_input_images()


def clear_current_reference_image() -> None:
    clear_stored_reference_images()


def clear_all_multi_reference_images() -> None:
    clear_stored_multi_reference_images()


def clear_multi_reference_slot(slot_index: int) -> None:
    clear_stored_multi_reference_images(slot_index=slot_index)


def clear_current_mask_image() -> None:
    clear_stored_mask_images()


def inspect_result_image(path: Path) -> dict:
    try:
        with Image.open(path) as image:
            image.load()
            format_name = str(image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="output_file_missing",
            blocker="generated_file_not_accessible",
            message="Generated result image is not readable.",
        ) from exc

    format_info = VALID_UPLOAD_FORMATS.get(format_name)
    extension = path.suffix.lower()
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if format_info is not None:
        extension, mime_type = format_info

    return {
        "extension": extension if extension in VALID_UPLOAD_EXTENSIONS else ".png",
        "mime_type": mime_type,
        "width": int(width),
        "height": int(height),
        "size_bytes": path.stat().st_size,
    }


def write_result_metadata(path: Path, metadata: dict) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(json.dumps(metadata, ensure_ascii=True, separators=(",", ":")), encoding="utf-8")
    temp_path.replace(path)


def get_result_retention_limit() -> int:
    raw_value = os.environ.get(RESULT_RETENTION_ENV_VAR)
    if raw_value is None:
        return RESULT_RETENTION_DEFAULT

    normalized_value = raw_value.strip()
    if not normalized_value:
        return RESULT_RETENTION_DEFAULT

    try:
        parsed_value = int(normalized_value)
    except ValueError:
        return RESULT_RETENTION_DEFAULT

    return parsed_value if parsed_value >= 1 else RESULT_RETENTION_DEFAULT


def resolve_result_mode_name(render_mode: object, *, use_input_image: bool, use_inpainting: bool) -> str:
    normalized_mode = str(render_mode or "").strip().lower()
    if normalized_mode == "placeholder":
        return "placeholder"
    if normalized_mode == IDENTITY_REFERENCE_MODE:
        return IDENTITY_REFERENCE_MODE
    if normalized_mode == IDENTITY_MULTI_REFERENCE_MODE:
        return IDENTITY_MULTI_REFERENCE_MODE
    if normalized_mode == IDENTITY_TRANSFER_MODE:
        return IDENTITY_TRANSFER_MODE
    if use_inpainting:
        return "inpainting"
    if use_input_image:
        return "img2img"
    return "txt2img"


def build_result_metadata_item(metadata_payload: dict, image_path: Path) -> dict | None:
    result_id = str(metadata_payload.get("result_id") or "").strip()
    file_name = str(metadata_payload.get("file_name") or "").strip()
    created_at = str(metadata_payload.get("created_at") or "").strip()
    if not result_id or not file_name or not created_at:
        return None

    candidate = (result_root() / Path(file_name).name).resolve()
    try:
        candidate.relative_to(result_root())
    except ValueError:
        return None

    if candidate != image_path.resolve():
        return None
    if not is_accessible_output_file(candidate):
        return None

    try:
        image_info = inspect_result_image(candidate)
    except ResultStoreError:
        return None
    return {
        "result_id": result_id,
        "created_at": created_at,
        "mode": str(metadata_payload.get("mode") or "txt2img").strip() or "txt2img",
        "prompt": str(metadata_payload.get("prompt") or "").strip(),
        "checkpoint": str(metadata_payload.get("checkpoint") or "").strip() or None,
        "width": image_info["width"],
        "height": image_info["height"],
        "file_name": candidate.name,
        "mime_type": image_info["mime_type"],
        "size_bytes": image_info["size_bytes"],
        "preview_url": result_path_to_web_path(candidate),
        "download_url": result_id_to_download_url(result_id),
        "reference_count": metadata_payload.get("reference_count") if isinstance(metadata_payload.get("reference_count"), int) else None,
        "reference_slots": metadata_payload.get("reference_slots") if isinstance(metadata_payload.get("reference_slots"), list) else None,
        "reference_image_ids": metadata_payload.get("reference_image_ids") if isinstance(metadata_payload.get("reference_image_ids"), list) else None,
        "multi_reference_strategy": str(metadata_payload.get("multi_reference_strategy") or "").strip() or None,
        "used_roles": metadata_payload.get("used_roles") if isinstance(metadata_payload.get("used_roles"), list) else None,
        "pose_reference_present": metadata_payload.get("pose_reference_present") if isinstance(metadata_payload.get("pose_reference_present"), bool) else None,
        "pose_reference_used": metadata_payload.get("pose_reference_used") if isinstance(metadata_payload.get("pose_reference_used"), bool) else None,
        "transfer_mask_present": metadata_payload.get("transfer_mask_present") if isinstance(metadata_payload.get("transfer_mask_present"), bool) else None,
        "transfer_mask_used": metadata_payload.get("transfer_mask_used") if isinstance(metadata_payload.get("transfer_mask_used"), bool) else None,
        "identity_head_reference_image_id": str(metadata_payload.get("identity_head_reference_image_id") or "").strip() or None,
        "target_body_image_id": str(metadata_payload.get("target_body_image_id") or "").strip() or None,
        "pose_reference_image_id": str(metadata_payload.get("pose_reference_image_id") or "").strip() or None,
        "transfer_mask_image_id": str(metadata_payload.get("transfer_mask_image_id") or "").strip() or None,
        "identity_transfer_strategy": str(metadata_payload.get("identity_transfer_strategy") or "").strip() or None,
    }


def list_result_store_records() -> list[dict]:
    root = result_root()
    root.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for metadata_path in root.iterdir():
        if not metadata_path.is_file() or metadata_path.suffix.lower() != ".json":
            continue

        payload, error = read_json_file_detail(metadata_path)
        if payload is None or error is not None:
            continue

        result_id = str(payload.get("result_id") or "").strip()
        file_name = str(payload.get("file_name") or "").strip()
        created_at = str(payload.get("created_at") or "").strip()
        if not result_id or not file_name or not created_at:
            continue

        image_path = (root / Path(file_name).name).resolve()
        try:
            image_path.relative_to(root)
        except ValueError:
            continue

        records.append(
            {
                "result_id": result_id,
                "created_at": created_at,
                "metadata_path": metadata_path.resolve(),
                "image_path": image_path,
            }
        )

    records.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("result_id") or ""),
        ),
        reverse=True,
    )
    return records


def enforce_result_retention(*, retain_count: int | None = None) -> None:
    effective_limit = retain_count if retain_count is not None else get_result_retention_limit()
    if effective_limit < 1:
        effective_limit = RESULT_RETENTION_DEFAULT

    stale_records = list_result_store_records()[effective_limit:]
    for record in stale_records:
        for target_path in (record["metadata_path"], record["image_path"]):
            try:
                target_path.unlink(missing_ok=True)
            except OSError as exc:
                print(
                    f"[result-retention] failed to remove {target_path.name}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )


def capture_generated_result(
    output_file: str | Path | None,
    *,
    render_mode: object,
    prompt: str,
    checkpoint: str | None,
    use_input_image: bool,
    use_inpainting: bool,
    extra_metadata: dict | None = None,
) -> dict:
    results_dir_accessible, results_dir_error = results_dir_access_state()
    if not results_dir_accessible:
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker=results_dir_error or "results_dir_not_accessible",
            message="Results directory is not accessible.",
        )

    source_output, output_error = resolve_internal_output_path(output_file)
    if source_output is None or not is_accessible_output_file(source_output):
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="output_file_missing",
            blocker=output_error or "generated_file_not_accessible",
            message="Generated result image is not accessible.",
        )

    image_info = inspect_result_image(source_output)
    result_id = f"result-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"
    file_name = f"{result_id}{image_info['extension']}"
    final_path = result_root() / file_name
    temp_path = result_root() / f".{file_name}.tmp"
    metadata_path = result_root() / f"{result_id}.json"
    created_at = utc_now_iso()
    metadata_payload = {
        "result_id": result_id,
        "created_at": created_at,
        "mode": resolve_result_mode_name(
            render_mode,
            use_input_image=use_input_image,
            use_inpainting=use_inpainting,
        ),
        "prompt": prompt,
        "checkpoint": checkpoint or None,
        "width": image_info["width"],
        "height": image_info["height"],
        "file_name": file_name,
    }
    if isinstance(extra_metadata, dict) and extra_metadata:
        metadata_payload.update(extra_metadata)

    try:
        shutil.copyfile(source_output, temp_path)
        temp_path.replace(final_path)
        write_result_metadata(metadata_path, metadata_payload)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker="results_storage_error",
            message="Generated result could not be stored.",
        ) from exc

    metadata_item = build_result_metadata_item(metadata_payload, final_path)
    if metadata_item is None:
        final_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise ResultStoreError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="api_error",
            blocker="results_metadata_invalid",
            message="Stored result metadata is invalid.",
        )

    enforce_result_retention()
    return metadata_item


def read_result_item(metadata_path: Path) -> dict | None:
    payload, error = read_json_file_detail(metadata_path)
    if payload is None or error is not None:
        return None

    file_name = str(payload.get("file_name") or "").strip()
    if not file_name:
        return None

    image_path = (result_root() / Path(file_name).name).resolve()
    try:
        image_path.relative_to(result_root())
    except ValueError:
        return None

    return build_result_metadata_item(payload, image_path)


def list_stored_results(*, limit: int = RESULTS_DEFAULT_LIMIT) -> list[dict]:
    root = result_root()
    root.mkdir(parents=True, exist_ok=True)
    metadata_paths = sorted(
        (
            path for path in root.iterdir()
            if path.is_file() and path.suffix.lower() == ".json"
        ),
        reverse=True,
    )

    items: list[dict] = []
    for metadata_path in metadata_paths:
        item = read_result_item(metadata_path)
        if item is None:
            continue
        items.append(item)

    items.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("result_id") or ""),
        ),
        reverse=True,
    )
    return items[:limit]


def resolve_result_download_item(result_id: str) -> tuple[dict | None, Path | None]:
    metadata_path = (result_root() / f"{Path(result_id).name}.json").resolve()
    try:
        metadata_path.relative_to(result_root())
    except ValueError:
        return None, None

    item = read_result_item(metadata_path)
    if item is None:
        return None, None

    image_path = (result_root() / item["file_name"]).resolve()
    try:
        image_path.relative_to(result_root())
    except ValueError:
        return None, None

    if not is_accessible_output_file(image_path):
        return None, None
    return item, image_path


def resolve_generation_request(
    payload: dict,
    *,
    use_input_image: bool = False,
    use_inpainting: bool = False,
) -> tuple[str, str | None, str | None]:
    inventory = checkpoint_inventory.build_checkpoint_inventory()
    selected_checkpoint = inventory.get("selected")
    sdxl_count = int(inventory.get("sdxl_count", 0))
    requested_mode = validate_mode(payload.get("mode", "auto"))

    if (use_input_image or use_inpainting) and requested_mode == "placeholder":
        raise ValueError("input_image_requires_sdxl")

    if requested_mode == "placeholder":
        return "placeholder", PLACEHOLDER_WORKFLOW_NAME, None

    if requested_mode == "sdxl":
        requested_checkpoint = payload.get("checkpoint")
        if isinstance(requested_checkpoint, str) and requested_checkpoint.strip():
            return "sdxl", None if (use_input_image or use_inpainting) else MINIMAL_WORKFLOW_NAME, requested_checkpoint.strip()
        return "sdxl", None if (use_input_image or use_inpainting) else MINIMAL_WORKFLOW_NAME, selected_checkpoint

    if sdxl_count >= 1 and isinstance(selected_checkpoint, str) and selected_checkpoint:
        return "sdxl", None if (use_input_image or use_inpainting) else MINIMAL_WORKFLOW_NAME, selected_checkpoint

    return "placeholder", PLACEHOLDER_WORKFLOW_NAME, None


def resolve_requested_input_image(image_id: object) -> tuple[dict, Path]:
    current_image = current_input_image_state()
    if not current_image:
        raise ValueError("missing_input_image")

    current_image_id = str(current_image.get("image_id") or "").strip()
    if not current_image_id:
        raise ValueError("missing_input_image")

    requested_image_id = str(image_id or "").strip()
    if requested_image_id and requested_image_id != current_image_id:
        raise ValueError("stale_input_image_reference")

    stored_name = str(current_image.get("stored_name") or "").strip()
    if not stored_name:
        raise ValueError("missing_input_image")

    candidate = (input_root() / Path(stored_name).name).resolve()
    try:
        candidate.relative_to(input_root())
    except ValueError as exc:
        raise ValueError("missing_input_image") from exc

    if not is_accessible_output_file(candidate):
        raise ValueError("missing_input_image")

    return current_image, candidate


def resolve_requested_reference_image(image_id: object) -> tuple[dict, Path]:
    current_reference = current_reference_image_state()
    if not current_reference:
        raise ValueError("missing_reference_image")

    current_reference_id = str(current_reference.get("image_id") or "").strip()
    if not current_reference_id:
        raise ValueError("missing_reference_image")

    requested_reference_id = str(image_id or "").strip()
    if requested_reference_id and requested_reference_id != current_reference_id:
        raise ValueError("stale_reference_image_reference")

    stored_name = str(current_reference.get("stored_name") or "").strip()
    if not stored_name:
        raise ValueError("missing_reference_image")

    candidate = (reference_root() / Path(stored_name).name).resolve()
    try:
        candidate.relative_to(reference_root())
    except ValueError as exc:
        raise ValueError("missing_reference_image") from exc

    if not is_accessible_output_file(candidate):
        raise ValueError("missing_reference_image")

    return current_reference, candidate


def resolve_requested_mask_image(image_id: object) -> tuple[dict, Path]:
    current_mask = current_mask_image_state()
    if not current_mask:
        raise ValueError("missing_mask_image")

    current_mask_id = str(current_mask.get("image_id") or "").strip()
    if not current_mask_id:
        raise ValueError("missing_mask_image")

    requested_mask_id = str(image_id or "").strip()
    if requested_mask_id and requested_mask_id != current_mask_id:
        raise ValueError("stale_mask_image_reference")

    stored_name = str(current_mask.get("stored_name") or "").strip()
    if not stored_name:
        raise ValueError("missing_mask_image")

    candidate = (mask_root() / Path(stored_name).name).resolve()
    try:
        candidate.relative_to(mask_root())
    except ValueError as exc:
        raise ValueError("missing_mask_image") from exc

    if not is_accessible_output_file(candidate):
        raise ValueError("missing_mask_image")

    return current_mask, candidate


def finalize_generate_result(
    result: dict,
    request_id: str,
    *,
    prompt: str,
    checkpoint: str | None,
    use_input_image: bool,
    use_inpainting: bool,
    extra_metadata: dict | None = None,
) -> tuple[HTTPStatus, dict]:
    mode = result.get("mode")
    prompt_id = result.get("prompt_id")
    status = str(result.get("status"))

    if status != "ok":
        return HTTPStatus.BAD_REQUEST, build_generate_response(
            status=status,
            mode=mode,
            output_file=None,
            error_type=result.get("error_type"),
            blocker=result.get("blocker"),
            prompt_id=prompt_id,
            request_id=request_id,
        )

    try:
        stored_result = capture_generated_result(
            result.get("output_file"),
            render_mode=mode,
            prompt=prompt,
            checkpoint=checkpoint,
            use_input_image=use_input_image,
            use_inpainting=use_inpainting,
            extra_metadata=extra_metadata,
        )
    except ResultStoreError as exc:
        return exc.status_code, build_error_response(
            mode=mode,
            error_type=exc.error_type,
            blocker=exc.blocker,
            prompt_id=prompt_id,
            request_id=request_id,
        )

    response_payload = build_generate_response(
        status="ok",
        mode=mode,
        output_file=stored_result["preview_url"],
        error_type=None,
        blocker=None,
        prompt_id=prompt_id,
        request_id=request_id,
    )
    response_payload["result_id"] = stored_result["result_id"]
    response_payload["download_url"] = stored_result["download_url"]
    return HTTPStatus.OK, response_payload


def resolve_runner_state(
    *,
    runner_payload: dict | None,
    runner_error: str | None,
    comfyui_reachable: bool,
) -> tuple[str, str | None]:
    raw_status = None
    if isinstance(runner_payload, dict):
        candidate = runner_payload.get("status")
        if isinstance(candidate, str) and candidate in VALID_RUNNER_STATUSES:
            raw_status = candidate

    if comfyui_reachable:
        if raw_status in {"started", "already_running", "busy"}:
            return raw_status, None
        return "already_running", None

    if runner_error == "missing":
        return "unknown", "runner_status_missing"
    if runner_error in {"invalid_json", "invalid_payload", "read_failed"}:
        return "unknown", "runner_status_unreadable"
    if raw_status in {"started", "already_running", "busy"}:
        return "unknown", "runner_state_invalid"
    if raw_status == "error":
        return "error", None
    return "unknown", "runner_status_unreadable"


class AppServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(server_address, handler_class)
        self._render_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._request_counter = itertools.count(1)
        self._server_render_status = "idle"
        self._server_render_started_at_utc: str | None = None
        self._server_render_request_id: str | None = None

    def next_request_id(self) -> str:
        with self._state_lock:
            counter = next(self._request_counter)
        return f"req-{counter:06d}"

    def try_begin_render(self, request_id: str) -> bool:
        if not self._render_lock.acquire(blocking=False):
            return False

        with self._state_lock:
            self._server_render_status = "running"
            self._server_render_started_at_utc = utc_now_iso()
            self._server_render_request_id = request_id
        return True

    def finish_render(self) -> None:
        with self._state_lock:
            self._server_render_status = "idle"
            self._server_render_started_at_utc = None
            self._server_render_request_id = None

        if self._render_lock.locked():
            self._render_lock.release()

    def render_state(self) -> dict:
        with self._state_lock:
            return {
                "server_render_status": self._server_render_status,
                "server_render_request_id": self._server_render_request_id,
                "server_render_started_at_utc": self._server_render_started_at_utc,
            }

    def collect_system_state(self) -> dict:
        inventory = checkpoint_inventory.build_checkpoint_inventory()
        runner_payload, runner_file_error = read_json_file_detail(RUNNER_STATUS_PATH)
        comfyui_reachable, comfyui_error = probe_comfyui()
        text_service_state = collect_text_service_state()
        output_dir_accessible, output_dir_error = output_dir_access_state()
        input_dir_accessible, input_dir_error = input_dir_access_state()
        reference_dir_accessible, reference_dir_error = reference_dir_access_state()
        mask_dir_accessible, mask_dir_error = mask_dir_access_state()
        results_dir_accessible, results_dir_error = results_dir_access_state()
        runner_status, runner_state_error = resolve_runner_state(
            runner_payload=runner_payload,
            runner_error=runner_file_error,
            comfyui_reachable=comfyui_reachable,
        )

        payload = {
            "service": "local-image-app",
            "status": "ok",
            "runner": runner_payload,
            "runner_status": runner_status,
            "runner_error": runner_state_error,
            "comfyui_reachable": comfyui_reachable,
            "comfyui_error": comfyui_error,
            "api_error": comfyui_error,
            "output_dir_accessible": output_dir_accessible,
            "output_dir_error": output_dir_error,
            "input_dir_accessible": input_dir_accessible,
            "input_dir_error": input_dir_error,
            "reference_dir_accessible": reference_dir_accessible,
            "reference_dir_error": reference_dir_error,
            "mask_dir_accessible": mask_dir_accessible,
            "mask_dir_error": mask_dir_error,
            "results_dir_accessible": results_dir_accessible,
            "results_dir_error": results_dir_error,
            "input_image": current_input_image_state(),
            "reference_image": current_reference_image_state(),
            "mask_image": current_mask_image_state(),
            "sdxl_available": inventory.get("sdxl_count", 0) >= 1,
            "selected_checkpoint": inventory.get("selected"),
            "inventory": inventory,
        }
        payload.update(text_service_state)
        payload.update(self.render_state())
        return payload


class AppRequestHandler(BaseHTTPRequestHandler):
    server: AppServer
    server_version = "LocalRenderHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self.serve_index()
            return
        if parsed.path == "/health":
            self.send_json(HTTPStatus.OK, self.server.collect_system_state())
            return
        if parsed.path == IDENTITY_REFERENCE_READINESS_PATH:
            readiness_state = build_identity_runtime_state()
            self.send_json(
                HTTPStatus.OK if readiness_state.get("ok") is True else resolve_identity_reference_status_code(
                    error_type=readiness_state.get("error_type") if isinstance(readiness_state.get("error_type"), str) else None,
                    blocker=readiness_state.get("blocker") if isinstance(readiness_state.get("blocker"), str) else None,
                ),
                readiness_state,
            )
            return
        if parsed.path == MULTI_REFERENCE_STATUS_PATH:
            multi_reference_dir_accessible, multi_reference_dir_error = multi_reference_dir_access_state()
            if not multi_reference_dir_accessible:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="api_error",
                        blocker=multi_reference_dir_error or "multi_reference_dir_not_accessible",
                        message="Multi-reference directory is not accessible.",
                    ),
                )
                return
            self.send_json(HTTPStatus.OK, build_multi_reference_status_payload())
            return
        if parsed.path == MULTI_REFERENCE_READINESS_PATH:
            readiness_state = build_identity_multi_reference_runtime_state()
            self.send_json(
                HTTPStatus.OK if readiness_state.get("ok") is True else resolve_identity_multi_reference_status_code(
                    error_type=readiness_state.get("error_type") if isinstance(readiness_state.get("error_type"), str) else None,
                    blocker=readiness_state.get("blocker") if isinstance(readiness_state.get("blocker"), str) else None,
                ),
                readiness_state,
            )
            return
        if parsed.path == IDENTITY_TRANSFER_STATUS_PATH:
            self.send_json(HTTPStatus.OK, build_identity_transfer_status_payload())
            return
        if parsed.path == IDENTITY_TRANSFER_READINESS_PATH:
            readiness_state = build_identity_transfer_runtime_state()
            self.send_json(
                HTTPStatus.OK if readiness_state.get("ok") is True else resolve_identity_transfer_generate_status_code(
                    error_type=readiness_state.get("error_type") if isinstance(readiness_state.get("error_type"), str) else None,
                    blocker=readiness_state.get("blocker") if isinstance(readiness_state.get("blocker"), str) else None,
                ),
                readiness_state,
            )
            return
        if parsed.path == "/checkpoints":
            self.send_json(HTTPStatus.OK, checkpoint_inventory.build_checkpoint_inventory())
            return
        if parsed.path == RESULT_LIST_PATH:
            self.handle_results_list(parsed.query)
            return
        if parsed.path.startswith(INPUT_ROUTE_PREFIX):
            self.serve_input(parsed.path)
            return
        if parsed.path.startswith(REFERENCE_ROUTE_PREFIX):
            self.serve_reference(parsed.path)
            return
        if parsed.path.startswith(MULTI_REFERENCE_ROUTE_PREFIX):
            self.serve_multi_reference(parsed.path)
            return
        if parsed.path.startswith(IDENTITY_TRANSFER_ROUTE_PREFIX):
            self.serve_identity_transfer(parsed.path)
            return
        if parsed.path.startswith(MASK_ROUTE_PREFIX):
            self.serve_mask(parsed.path)
            return
        if parsed.path.startswith(RESULT_DOWNLOAD_ROUTE_PREFIX):
            self.serve_result_download(parsed.path)
            return
        if parsed.path.startswith(RESULT_FILE_ROUTE_PREFIX):
            self.serve_result(parsed.path)
            return
        if parsed.path.startswith("/output/"):
            self.serve_output(parsed.path)
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == INPUT_IMAGE_RESET_PATH:
            try:
                clear_current_input_image()
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="input_storage_error",
                        message="Stored input image could not be cleared.",
                    ),
                )
                return

            self.send_json(HTTPStatus.OK, {"status": "ok", "ok": True, "cleared": True})
            return

        if parsed.path == REFERENCE_IMAGE_RESET_PATH:
            try:
                clear_current_reference_image()
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="reference_storage_error",
                        message="Stored reference image could not be cleared.",
                    ),
                )
                return

            self.send_json(HTTPStatus.OK, {"status": "ok", "ok": True, "cleared": True})
            return

        if parsed.path == MULTI_REFERENCE_IMAGES_RESET_PATH:
            try:
                clear_all_multi_reference_images()
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="multi_reference_storage_error",
                        message="Stored multi-reference images could not be cleared.",
                    ),
                )
                return

            self.send_json(HTTPStatus.OK, {"status": "ok", "ok": True, "cleared": True})
            return

        if parsed.path == IDENTITY_TRANSFER_ROLES_RESET_PATH:
            try:
                clear_all_identity_transfer_roles()
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="identity_transfer_role_storage_error",
                        message="Stored V6.3.1 role images could not be cleared.",
                    ),
                )
                return

            self.send_json(HTTPStatus.OK, {"status": "ok", "ok": True, "cleared": True})
            return

        multi_reference_slot_index = resolve_multi_reference_slot_reset_index(parsed.path)
        if multi_reference_slot_index is not None:
            try:
                clear_multi_reference_slot(multi_reference_slot_index)
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="multi_reference_storage_error",
                        message="Stored multi-reference slot could not be cleared.",
                    ),
                )
                return

            self.send_json(
                HTTPStatus.OK,
                {"status": "ok", "ok": True, "cleared": True, "slot_index": multi_reference_slot_index},
            )
            return
        if parsed.path.startswith(MULTI_REFERENCE_IMAGE_SLOT_RESET_PREFIX):
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_multi_reference_slot",
                    message="slot_index must be 1-3.",
                ),
            )
            return

        transfer_role = resolve_identity_transfer_role_reset_name(parsed.path)
        if transfer_role is not None:
            try:
                clear_current_identity_transfer_role(transfer_role)
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="identity_transfer_role_storage_error",
                        message="Stored V6.3.1 role image could not be cleared.",
                    ),
                )
                return

            self.send_json(
                HTTPStatus.OK,
                {"status": "ok", "ok": True, "cleared": True, "role": transfer_role},
            )
            return
        if parsed.path.startswith(IDENTITY_TRANSFER_ROLE_RESET_PREFIX):
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_identity_transfer_role",
                    message="role must be one of the supported V6.3.1 transfer roles.",
                ),
            )
            return

        if parsed.path == MASK_IMAGE_RESET_PATH:
            try:
                clear_current_mask_image()
            except OSError:
                self.send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    build_upload_error_response(
                        error_type="upload_error",
                        blocker="mask_storage_error",
                        message="Stored mask image could not be cleared.",
                    ),
                )
                return

            self.send_json(HTTPStatus.OK, {"status": "ok", "ok": True, "cleared": True})
            return

        if parsed.path != INPUT_IMAGE_RESET_PATH:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
        return

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == INPUT_IMAGE_UPLOAD_PATH:
            self.handle_input_image_upload()
            return
        if parsed.path == REFERENCE_IMAGE_UPLOAD_PATH:
            self.handle_reference_image_upload()
            return
        if parsed.path == MULTI_REFERENCE_IMAGE_UPLOAD_PATH:
            self.handle_multi_reference_image_upload()
            return
        if parsed.path == IDENTITY_TRANSFER_ROLE_UPLOAD_PATH:
            self.handle_identity_transfer_role_upload()
            return
        if parsed.path == MASK_IMAGE_EDITOR_PATH:
            self.handle_mask_editor_save()
            return
        if parsed.path == TEXT_SERVICE_PROMPT_TEST_PATH:
            self.handle_text_service_prompt_test()
            return
        if parsed.path == IDENTITY_TRANSFER_GENERATE_PATH:
            self.handle_identity_transfer_generate()
            return
        if parsed.path == IDENTITY_MULTI_REFERENCE_GENERATE_PATH:
            self.handle_identity_multi_reference_generate()
            return
        if parsed.path == IDENTITY_REFERENCE_GENERATE_PATH:
            self.handle_identity_reference_generate()
            return
        if parsed.path != "/generate":
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return

        request_id = self.server.next_request_id()
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=None,
                    error_type="invalid_request",
                    blocker="invalid_json",
                    request_id=request_id,
                ),
            )
            return

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=None,
                    error_type="invalid_request",
                    blocker="empty_prompt",
                    request_id=request_id,
                ),
            )
            return

        try:
            use_input_image = parse_boolean_flag(payload.get("use_input_image"), default=False)
        except ValueError as exc:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=None,
                    error_type="invalid_request",
                    blocker=str(exc),
                    request_id=request_id,
                ),
            )
            return

        try:
            use_inpainting = parse_boolean_flag(payload.get("use_inpainting"), default=False)
        except ValueError as exc:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=None,
                    error_type="invalid_request",
                    blocker=str(exc),
                    request_id=request_id,
                ),
            )
            return

        try:
            denoise_strength = normalize_denoise_strength_value(payload.get("denoise_strength"))
        except ValueError as exc:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=None,
                    error_type="invalid_request",
                    blocker=str(exc),
                    request_id=request_id,
                ),
            )
            return

        try:
            mode, workflow, checkpoint = resolve_generation_request(
                payload,
                use_input_image=use_input_image,
                use_inpainting=use_inpainting,
            )
        except ValueError as exc:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=None,
                    error_type="invalid_request",
                    blocker=str(exc),
                    request_id=request_id,
                ),
            )
            return

        input_image_path = None
        if use_input_image or use_inpainting:
            try:
                _, input_image_path = resolve_requested_input_image(payload.get("input_image_id"))
            except ValueError as exc:
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    build_error_response(
                        mode=mode,
                        error_type="invalid_request",
                        blocker=str(exc),
                        request_id=request_id,
                    ),
                )
                return

        mask_image_path = None
        if use_inpainting:
            try:
                _, mask_image_path = resolve_requested_mask_image(payload.get("mask_image_id"))
            except ValueError as exc:
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    build_error_response(
                        mode=mode,
                        error_type="invalid_request",
                        blocker=str(exc),
                        request_id=request_id,
                    ),
                )
                return

        system_state = self.server.collect_system_state()
        if not system_state["comfyui_reachable"]:
            blocker = "comfyui_unreachable"
            if system_state.get("runner_error") == "runner_state_invalid":
                blocker = "runner_state_invalid"
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=None,
                    error_type="api_error",
                    blocker=blocker,
                    request_id=request_id,
                ),
            )
            return

        if system_state.get("runner_status") == "unknown":
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=None,
                    error_type="api_error",
                    blocker="runner_state_invalid",
                    request_id=request_id,
                ),
            )
            return

        if not self.server.try_begin_render(request_id):
            self.send_json(HTTPStatus.CONFLICT, build_busy_response(request_id=request_id))
            return

        response_payload: dict
        response_status = HTTPStatus.OK
        try:
            result = run_render(
                prompt=prompt.strip(),
                mode=mode,
                workflow=workflow,
                checkpoint=checkpoint,
                use_input_image=use_input_image,
                input_image_path=input_image_path,
                use_inpainting=use_inpainting,
                mask_image_path=mask_image_path,
                denoise_strength=denoise_strength,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            )
            response_status, response_payload = finalize_generate_result(
                result,
                request_id,
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                use_input_image=use_input_image,
                use_inpainting=use_inpainting,
            )
        except Exception:
            response_payload = build_error_response(
                mode=mode,
                error_type="api_error",
                blocker="server_error",
                request_id=request_id,
            )
            response_status = HTTPStatus.INTERNAL_SERVER_ERROR
        finally:
            self.server.finish_render()

        self.send_json(response_status, response_payload)

    def handle_identity_reference_generate(self) -> None:
        request_id = self.server.next_request_id()
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_REFERENCE_MODE,
                    error_type="invalid_request",
                    blocker="invalid_json",
                    request_id=request_id,
                ),
            )
            return

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_REFERENCE_MODE,
                    error_type="invalid_request",
                    blocker="empty_prompt",
                    request_id=request_id,
                ),
            )
            return

        checkpoint = None
        if isinstance(payload.get("checkpoint"), str) and payload.get("checkpoint").strip():
            checkpoint = payload.get("checkpoint").strip()

        try:
            _, reference_image_path = resolve_requested_reference_image(payload.get("reference_image_id"))
        except ValueError as exc:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_REFERENCE_MODE,
                    error_type="invalid_request",
                    blocker=str(exc),
                    request_id=request_id,
                ),
            )
            return

        system_state = self.server.collect_system_state()
        if not system_state["comfyui_reachable"]:
            blocker = "comfyui_unreachable"
            if system_state.get("runner_error") == "runner_state_invalid":
                blocker = "runner_state_invalid"
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=IDENTITY_REFERENCE_MODE,
                    error_type="api_error",
                    blocker=blocker,
                    request_id=request_id,
                ),
            )
            return

        if system_state.get("runner_status") == "unknown":
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=IDENTITY_REFERENCE_MODE,
                    error_type="api_error",
                    blocker="runner_state_invalid",
                    request_id=request_id,
                ),
            )
            return

        if not self.server.try_begin_render(request_id):
            self.send_json(HTTPStatus.CONFLICT, build_busy_response(request_id=request_id))
            return

        response_payload: dict
        response_status = HTTPStatus.OK
        try:
            result = run_identity_reference(
                prompt=prompt.strip(),
                reference_image_path=reference_image_path,
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            )
            if result.get("status") == "ok":
                response_status, response_payload = finalize_generate_result(
                    result,
                    request_id,
                    prompt=prompt.strip(),
                    checkpoint=str(result.get("checkpoint") or checkpoint or ""),
                    use_input_image=False,
                    use_inpainting=False,
                )
            else:
                response_status = resolve_identity_reference_status_code(
                    error_type=str(result.get("error_type") or ""),
                    blocker=str(result.get("blocker") or ""),
                )
                response_payload = build_error_response(
                    mode=IDENTITY_REFERENCE_MODE,
                    error_type=str(result.get("error_type") or "api_error"),
                    blocker=str(result.get("blocker") or "identity_reference_failed"),
                    prompt_id=result.get("prompt_id") if isinstance(result.get("prompt_id"), str) else None,
                    request_id=request_id,
                )
        except Exception:
            response_payload = build_error_response(
                mode=IDENTITY_REFERENCE_MODE,
                error_type="api_error",
                blocker="server_error",
                request_id=request_id,
            )
            response_status = HTTPStatus.INTERNAL_SERVER_ERROR
        finally:
            self.server.finish_render()

        self.send_json(response_status, response_payload)

    def handle_identity_transfer_generate(self) -> None:
        request_id = self.server.next_request_id()
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_TRANSFER_MODE,
                    error_type="invalid_request",
                    blocker="invalid_json",
                    request_id=request_id,
                ),
            )
            return

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_TRANSFER_MODE,
                    error_type="invalid_request",
                    blocker="empty_prompt",
                    request_id=request_id,
                ),
            )
            return

        checkpoint = None
        if isinstance(payload.get("checkpoint"), str) and payload.get("checkpoint").strip():
            checkpoint = payload.get("checkpoint").strip()

        runtime_state = build_identity_transfer_runtime_state()
        if runtime_state.get("ok") is not True:
            blocker = str(runtime_state.get("blocker") or "identity_transfer_unavailable")
            error_type = str(runtime_state.get("error_type") or "api_error")
            self.send_json(
                resolve_identity_transfer_generate_status_code(error_type=error_type, blocker=blocker),
                build_error_response(
                    mode=IDENTITY_TRANSFER_MODE,
                    error_type=error_type,
                    blocker=blocker,
                    request_id=request_id,
                ),
            )
            return

        system_state = self.server.collect_system_state()
        if not system_state["comfyui_reachable"]:
            blocker = "comfyui_unreachable"
            if system_state.get("runner_error") == "runner_state_invalid":
                blocker = "runner_state_invalid"
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=IDENTITY_TRANSFER_MODE,
                    error_type="api_error",
                    blocker=blocker,
                    request_id=request_id,
                ),
            )
            return

        if system_state.get("runner_status") == "unknown":
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=IDENTITY_TRANSFER_MODE,
                    error_type="api_error",
                    blocker="runner_state_invalid",
                    request_id=request_id,
                ),
            )
            return

        if not self.server.try_begin_render(request_id):
            self.send_json(HTTPStatus.CONFLICT, build_busy_response(request_id=request_id))
            return

        response_payload: dict
        response_status = HTTPStatus.OK
        try:
            result = run_identity_transfer(
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            )
            if result.get("status") == "ok":
                response_status, response_payload = finalize_generate_result(
                    result,
                    request_id,
                    prompt=prompt.strip(),
                    checkpoint=str(result.get("checkpoint") or checkpoint or ""),
                    use_input_image=False,
                    use_inpainting=False,
                    extra_metadata={
                        "used_roles": result.get("used_roles") if isinstance(result.get("used_roles"), list) else [],
                        "pose_reference_present": bool(result.get("pose_reference_present")),
                        "pose_reference_used": bool(result.get("pose_reference_used")),
                        "transfer_mask_present": bool(result.get("transfer_mask_present")),
                        "transfer_mask_used": bool(result.get("transfer_mask_used")),
                        "identity_head_reference_image_id": str(result.get("identity_head_reference_image_id") or "").strip() or None,
                        "target_body_image_id": str(result.get("target_body_image_id") or "").strip() or None,
                        "pose_reference_image_id": str(result.get("pose_reference_image_id") or "").strip() or None,
                        "transfer_mask_image_id": str(result.get("transfer_mask_image_id") or "").strip() or None,
                        "identity_transfer_strategy": str(result.get("identity_transfer_strategy") or "").strip() or None,
                    },
                )
            else:
                response_status = resolve_identity_transfer_generate_status_code(
                    error_type=str(result.get("error_type") or ""),
                    blocker=str(result.get("blocker") or ""),
                )
                response_payload = build_error_response(
                    mode=IDENTITY_TRANSFER_MODE,
                    error_type=str(result.get("error_type") or "api_error"),
                    blocker=str(result.get("blocker") or "identity_transfer_failed"),
                    prompt_id=result.get("prompt_id") if isinstance(result.get("prompt_id"), str) else None,
                    request_id=request_id,
                )
        except Exception:
            response_payload = build_error_response(
                mode=IDENTITY_TRANSFER_MODE,
                error_type="api_error",
                blocker="server_error",
                request_id=request_id,
            )
            response_status = HTTPStatus.INTERNAL_SERVER_ERROR
        finally:
            self.server.finish_render()

        self.send_json(response_status, response_payload)

    def handle_identity_multi_reference_generate(self) -> None:
        request_id = self.server.next_request_id()
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    error_type="invalid_request",
                    blocker="invalid_json",
                    request_id=request_id,
                ),
            )
            return

        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_error_response(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    error_type="invalid_request",
                    blocker="empty_prompt",
                    request_id=request_id,
                ),
            )
            return

        checkpoint = None
        if isinstance(payload.get("checkpoint"), str) and payload.get("checkpoint").strip():
            checkpoint = payload.get("checkpoint").strip()

        adapter_state = build_multi_reference_adapter_state()
        runtime_state = build_identity_multi_reference_runtime_state(adapter_state=adapter_state)
        if runtime_state.get("ok") is not True:
            blocker = str(runtime_state.get("blocker") or "identity_multi_reference_unavailable")
            error_type = str(runtime_state.get("error_type") or "api_error")
            self.send_json(
                resolve_identity_multi_reference_status_code(error_type=error_type, blocker=blocker),
                build_error_response(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    error_type=error_type,
                    blocker=blocker,
                    request_id=request_id,
                ),
            )
            return

        system_state = self.server.collect_system_state()
        if not system_state["comfyui_reachable"]:
            blocker = "comfyui_unreachable"
            if system_state.get("runner_error") == "runner_state_invalid":
                blocker = "runner_state_invalid"
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    error_type="api_error",
                    blocker=blocker,
                    request_id=request_id,
                ),
            )
            return

        if system_state.get("runner_status") == "unknown":
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_error_response(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    error_type="api_error",
                    blocker="runner_state_invalid",
                    request_id=request_id,
                ),
            )
            return

        if not self.server.try_begin_render(request_id):
            self.send_json(HTTPStatus.CONFLICT, build_busy_response(request_id=request_id))
            return

        response_payload: dict
        response_status = HTTPStatus.OK
        try:
            result = run_identity_multi_reference(
                prompt=prompt.strip(),
                adapter_state=runtime_state.get("adapter_state") if isinstance(runtime_state.get("adapter_state"), dict) else adapter_state,
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            )
            if result.get("status") == "ok":
                response_status, response_payload = finalize_generate_result(
                    result,
                    request_id,
                    prompt=prompt.strip(),
                    checkpoint=str(result.get("checkpoint") or checkpoint or ""),
                    use_input_image=False,
                    use_inpainting=False,
                    extra_metadata={
                        "reference_count": int(result.get("reference_count") or 0),
                        "reference_slots": result.get("reference_slots") if isinstance(result.get("reference_slots"), list) else [],
                        "reference_image_ids": result.get("reference_image_ids") if isinstance(result.get("reference_image_ids"), list) else [],
                        "multi_reference_strategy": str(result.get("multi_reference_strategy") or "").strip() or None,
                    },
                )
            else:
                response_status = resolve_identity_multi_reference_status_code(
                    error_type=str(result.get("error_type") or ""),
                    blocker=str(result.get("blocker") or ""),
                )
                response_payload = build_error_response(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    error_type=str(result.get("error_type") or "api_error"),
                    blocker=str(result.get("blocker") or "identity_multi_reference_failed"),
                    prompt_id=result.get("prompt_id") if isinstance(result.get("prompt_id"), str) else None,
                    request_id=request_id,
                )
        except Exception:
            response_payload = build_error_response(
                mode=IDENTITY_MULTI_REFERENCE_MODE,
                error_type="api_error",
                blocker="server_error",
                request_id=request_id,
            )
            response_status = HTTPStatus.INTERNAL_SERVER_ERROR
        finally:
            self.server.finish_render()

        self.send_json(response_status, response_payload)

    def handle_text_service_prompt_test(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=False,
                    stub=True,
                    response_text=None,
                    error="invalid_json",
                    error_message="Valid JSON request body required.",
                    service_name=None,
                    model_status=None,
                ),
            )
            return

        prompt, prompt_error = normalize_text_service_prompt(payload.get("prompt"))
        if prompt_error is not None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=False,
                    stub=True,
                    response_text=None,
                    error=prompt_error,
                    error_message=(
                        "prompt must be a string."
                        if prompt_error == "prompt_not_string"
                        else (
                            "prompt must not be empty."
                            if prompt_error == "empty_prompt"
                            else f"prompt exceeds {TEXT_SERVICE_PROMPT_MAX_LENGTH} characters."
                        )
                    ),
                    service_name=None,
                    model_status=None,
                ),
            )
            return

        configured, config, config_error = load_text_service_config_state()
        if not configured or config is None:
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=False,
                    stub=True,
                    response_text=None,
                    error=config_error or "text_service_not_configured",
                    error_message=(
                        "Text service is not configured."
                        if config_error is None
                        else "Text service configuration is invalid."
                    ),
                    service_name=None,
                    model_status=None,
                ),
            )
            return

        service_name = config["service_name"]
        model_status = config["model_status"]
        response_payload, response_error, response_status = post_json_detail(
            f"http://{config['host']}:{config['port']}/prompt",
            timeout=TEXT_SERVICE_PROMPT_TIMEOUT,
            payload={"prompt": prompt},
        )

        if response_error is not None or response_status is None:
            blocker = "text_service_unreachable" if response_error in {"unreachable", "timeout"} else "text_service_invalid_response"
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=False,
                    stub=True,
                    response_text=None,
                    error=blocker,
                    error_message="Text service is not reachable." if blocker == "text_service_unreachable" else "Text service returned an invalid response.",
                    service_name=service_name,
                    model_status=model_status,
                ),
            )
            return

        upstream_service = response_payload.get("service") if isinstance(response_payload.get("service"), str) else service_name
        upstream_stub = response_payload.get("stub") is True
        upstream_model_status = response_payload.get("model_status") if isinstance(response_payload.get("model_status"), str) else model_status

        if response_status == HTTPStatus.OK and response_payload.get("ok") is True:
            self.send_json(
                HTTPStatus.OK,
                build_text_service_prompt_test_response(
                    ok=True,
                    text_service_reachable=True,
                    stub=upstream_stub,
                    response_text=response_payload.get("response_text") if isinstance(response_payload.get("response_text"), str) else None,
                    error=None,
                    error_message=None,
                    service_name=upstream_service,
                    model_status=upstream_model_status,
                ),
            )
            return

        error_value = None
        if isinstance(response_payload.get("blocker"), str) and response_payload.get("blocker").strip():
            error_value = response_payload.get("blocker").strip()
        elif isinstance(response_payload.get("error_type"), str) and response_payload.get("error_type").strip():
            error_value = response_payload.get("error_type").strip()
        else:
            error_value = "text_service_request_failed"

        error_message = response_payload.get("message") if isinstance(response_payload.get("message"), str) else "Text service request failed."
        try:
            status_code = HTTPStatus(response_status)
        except ValueError:
            status_code = HTTPStatus.BAD_GATEWAY

        self.send_json(
            status_code,
            build_text_service_prompt_test_response(
                ok=False,
                text_service_reachable=True,
                stub=upstream_stub,
                response_text=None,
                error=error_value,
                error_message=error_message,
                service_name=upstream_service,
                model_status=upstream_model_status,
            ),
        )

    def serve_index(self) -> None:
        self.serve_file(app_root() / "index.html")

    def serve_input(self, request_path: str) -> None:
        target = resolve_input_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def serve_reference(self, request_path: str) -> None:
        target = resolve_reference_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def serve_multi_reference(self, request_path: str) -> None:
        target = resolve_multi_reference_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def serve_identity_transfer(self, request_path: str) -> None:
        target = resolve_identity_transfer_role_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def serve_mask(self, request_path: str) -> None:
        target = resolve_mask_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def serve_result(self, request_path: str) -> None:
        target = resolve_result_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def serve_result_download(self, request_path: str) -> None:
        result_id = resolve_result_download_request_id(request_path)
        if result_id is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return

        item, target = resolve_result_download_item(result_id)
        if item is None or target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return

        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND, download_name=item["file_name"])

    def serve_output(self, request_path: str) -> None:
        target = resolve_output_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

    def handle_results_list(self, query_string: str) -> None:
        try:
            limit = parse_results_limit(query_string)
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_results_error_response(
                    error_type="invalid_request",
                    blocker="invalid_results_limit",
                    message="Results limit must be a positive integer.",
                ),
            )
            return

        results_dir_accessible, results_dir_error = results_dir_access_state()
        if not results_dir_accessible:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_results_error_response(
                    error_type="api_error",
                    blocker=results_dir_error or "results_dir_not_accessible",
                    message="Results directory is not accessible.",
                ),
            )
            return

        items = list_stored_results(limit=limit)
        self.send_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "count": len(items),
                "limit": limit,
                "items": items,
            },
        )

    def serve_file(
        self,
        path: Path,
        *,
        read_error_status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
        download_name: str | None = None,
    ) -> None:
        if not path.exists() or not path.is_file():
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        try:
            content = path.read_bytes()
        except OSError:
            self.send_json(read_error_status, {"status": "error", "reason": "not_found"})
            return

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if download_name:
            self.send_header("Content-Disposition", f'attachment; filename="{Path(download_name).name}"')
        self.end_headers()
        self.wfile.write(content)

    def handle_input_image_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type.lower():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_multipart",
                    message="Upload request must be multipart/form-data.",
                ),
            )
            return

        try:
            raw_body = self.read_body_bytes()
            original_name, payload, source_type = parse_multipart_image(content_type, raw_body)
            stored_payload = store_uploaded_image(original_name, payload, source_type)
        except UploadRequestError as exc:
            self.send_json(
                exc.status_code,
                build_upload_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_upload_body",
                    message="Upload request body is invalid.",
                ),
            )
            return
        except OSError:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_upload_error_response(
                    error_type="upload_error",
                    blocker="upload_read_failed",
                    message="Upload body could not be read.",
                ),
            )
            return

        self.send_json(HTTPStatus.OK, build_upload_success_response(stored_payload))

    def handle_reference_image_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type.lower():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_multipart",
                    message="Upload request must be multipart/form-data.",
                ),
            )
            return

        try:
            raw_body = self.read_body_bytes()
            original_name, payload, _ = parse_multipart_image(content_type, raw_body)
            stored_payload = store_reference_image(original_name, payload)
        except UploadRequestError as exc:
            self.send_json(
                exc.status_code,
                build_upload_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_upload_body",
                    message="Upload request body is invalid.",
                ),
            )
            return
        except OSError:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_upload_error_response(
                    error_type="upload_error",
                    blocker="upload_read_failed",
                    message="Upload body could not be read.",
                ),
            )
            return

        self.send_json(HTTPStatus.OK, build_upload_success_response(stored_payload))

    def handle_multi_reference_image_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type.lower():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_multipart",
                    message="Upload request must be multipart/form-data.",
                ),
            )
            return

        try:
            raw_body = self.read_body_bytes()
            original_name, payload, slot_index = parse_multipart_multi_reference_image(content_type, raw_body)
            stored_payload = store_multi_reference_image(original_name, payload, slot_index=slot_index)
        except UploadRequestError as exc:
            self.send_json(
                exc.status_code,
                build_upload_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_upload_body",
                    message="Upload request body is invalid.",
                ),
            )
            return
        except OSError:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_upload_error_response(
                    error_type="upload_error",
                    blocker="upload_read_failed",
                    message="Upload body could not be read.",
                ),
            )
            return

        self.send_json(HTTPStatus.OK, build_multi_reference_upload_success_response(stored_payload))

    def handle_identity_transfer_role_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type.lower():
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_multipart",
                    message="Upload request must be multipart/form-data.",
                ),
            )
            return

        try:
            raw_body = self.read_body_bytes()
            original_name, payload, role = parse_multipart_identity_transfer_role_image(content_type, raw_body)
            stored_payload = store_identity_transfer_role_image(original_name, payload, role=role)
        except UploadRequestError as exc:
            self.send_json(
                exc.status_code,
                build_upload_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_upload_body",
                    message="Upload request body is invalid.",
                ),
            )
            return
        except OSError:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_upload_error_response(
                    error_type="upload_error",
                    blocker="upload_read_failed",
                    message="Upload body could not be read.",
                ),
            )
            return

        self.send_json(HTTPStatus.OK, build_identity_transfer_upload_success_response(stored_payload))

    def handle_mask_editor_save(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker="invalid_json",
                    message="Mask editor request body is invalid.",
                ),
            )
            return

        try:
            _, source_image_path = resolve_requested_input_image(payload.get("source_image_id"))
            _, image_payload = decode_data_url_image(payload.get("mask_data_url"))
            validate_browser_mask_payload(image_payload, source_image_path)
            stored_payload = store_uploaded_image("browser-mask.png", image_payload, "mask")
        except UploadRequestError as exc:
            self.send_json(
                exc.status_code,
                build_upload_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return
        except ValueError as exc:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_upload_error_response(
                    error_type="invalid_request",
                    blocker=str(exc),
                    message="Mask editor request is invalid.",
                ),
            )
            return
        except OSError:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_upload_error_response(
                    error_type="upload_error",
                    blocker="upload_read_failed",
                    message="Mask editor payload could not be stored.",
                ),
            )
            return

        self.send_json(HTTPStatus.OK, build_upload_success_response(stored_payload))

    def read_json_body(self) -> dict | None:
        try:
            raw_body = self.read_body_bytes()
        except (OSError, ValueError):
            return None
        if not raw_body:
            return None
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if isinstance(payload, dict):
            return payload
        return None

    def read_body_bytes(self) -> bytes:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("invalid_content_length")
        if content_length <= 0:
            raise ValueError("empty_request_body")
        return self.rfile.read(content_length)

    def send_json(self, status_code: HTTPStatus, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal local HTTP bridge for ComfyUI renders.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    with AppServer((args.host, args.port), AppRequestHandler) as server:
        server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
