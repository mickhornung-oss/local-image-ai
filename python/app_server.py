import argparse
import base64
import binascii
import itertools
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
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
try:
    import text_chat_store as chat_store
except ModuleNotFoundError:
    from python import text_chat_store as chat_store

try:
    import text_chat_payloads as chat_payloads
except ModuleNotFoundError:
    from python import text_chat_payloads as chat_payloads

try:
    import text_chat_requests as chat_requests
except ModuleNotFoundError:
    from python import text_chat_requests as chat_requests

try:
    import text_chat_responses as chat_responses
except ModuleNotFoundError:
    from python import text_chat_responses as chat_responses

try:
    import text_chat_service_orchestration as chat_text_service
except ModuleNotFoundError:
    from python import text_chat_service_orchestration as chat_text_service

try:
    import app_status
except ModuleNotFoundError:
    from python import app_status

try:
    import multi_reference_status
except ModuleNotFoundError:
    from python import multi_reference_status

try:
    import identity_status
except ModuleNotFoundError:
    from python import identity_status

try:
    import identity_generate_flow
except ModuleNotFoundError:
    from python import identity_generate_flow

try:
    import identity_generate_results
except ModuleNotFoundError:
    from python import identity_generate_results

try:
    import image_input_validation
except ModuleNotFoundError:
    from python import image_input_validation

try:
    import upload_store
except ModuleNotFoundError:
    from python import upload_store

try:
    import result_output
except ModuleNotFoundError:
    from python import result_output

try:
    import generate_endpoint_flow
except ModuleNotFoundError:
    from python import generate_endpoint_flow

try:
    import general_generate_flow
except ModuleNotFoundError:
    from python import general_generate_flow

try:
    import app_paths
except ModuleNotFoundError:
    from python import app_paths

try:
    import app_request_utils
except ModuleNotFoundError:
    from python import app_request_utils
from render_identity_transfer import (
    IDENTITY_TRANSFER_MODE,
    build_identity_transfer_runtime_state,
    run_identity_transfer,
)
from render_identity_transfer_mask_hybrid import (
    IDENTITY_TRANSFER_MASK_HYBRID_MODE,
    build_identity_transfer_mask_hybrid_runtime_state,
    run_identity_transfer_mask_hybrid,
)
from render_text2img import (
    DEFAULT_BASE_URL,
    DEFAULT_CFG,
    DEFAULT_DENOISE_STRENGTH,
    DEFAULT_NEGATIVE_PROMPT,
    DEFAULT_STEPS,
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
from render_identity_research import (
    IDENTITY_RESEARCH_DEFAULT_PROVIDER,
    IDENTITY_RESEARCH_MODE,
    build_identity_research_runtime_state,
    run_identity_research,
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
EXPORT_FILE_ROUTE_PREFIX = "/exports/files/"
RESULT_LIST_PATH = "/results"
RESULT_EXPORT_PATH = "/results/export"
RESULT_DELETE_PATH = "/results/delete"
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
IDENTITY_TRANSFER_MASK_HYBRID_READINESS_PATH = "/identity-transfer/mask-hybrid/readiness"
IDENTITY_TRANSFER_MASK_HYBRID_GENERATE_PATH = "/identity-transfer/mask-hybrid/generate"
IDENTITY_MULTI_REFERENCE_GENERATE_PATH = "/identity-multi-reference/generate"
IDENTITY_REFERENCE_GENERATE_PATH = "/identity-reference/generate"
IDENTITY_REFERENCE_READINESS_PATH = "/identity-reference/readiness"
IDENTITY_RESEARCH_GENERATE_PATH = "/experimental/identity-research/generate"
IDENTITY_RESEARCH_READINESS_PATH = "/experimental/identity-research/readiness"
MASK_IMAGE_RESET_PATH = "/mask-image/current"
MASK_IMAGE_EDITOR_PATH = "/mask-image/editor"
TEXT_SERVICE_PROMPT_TEST_PATH = "/text-service/prompt-test"
TEXT_CHAT_SLOTS_PATH = "/text-service/chats"
TEXT_CHAT_CREATE_PATH = "/text-service/chats/new"
UPLOAD_MAX_BYTES = 25 * 1024 * 1024
RESULTS_DEFAULT_LIMIT = 20
RESULTS_MAX_LIMIT = 100
RESULT_RETENTION_DEFAULT = 50
RESULT_RETENTION_ENV_VAR = "LOCAL_IMAGE_APP_RESULT_RETENTION"
RESULT_TEMP_STALE_SECONDS = 10 * 60
MANAGED_RESULT_ID_PATTERN = re.compile(r"^result-\d{14}-[0-9a-f]{8}$")
MANAGED_RESULT_TMP_FILE_PATTERN = re.compile(r"^\.result-\d{14}-[0-9a-f]{8}\.(png|jpg|jpeg|webp)\.tmp$")
TEXT_SERVICE_CONFIG_PATH = repo_root() / "config" / "text_service.json"
TEXT_MODEL_SWITCH_STATE_PATH = (repo_root() / "vendor" / "text_runner" / "logs" / "model_switch.state.json").resolve()
TEXT_SERVICE_PROBE_TIMEOUT = 2.0
TEXT_SERVICE_PROMPT_TIMEOUT = 720.0
TEXT_SERVICE_PROMPT_MAX_LENGTH = 2000
TEXT_RUNNER_START_TIMEOUT_SECONDS = 300.0
TEXT_RUNNER_STOP_TIMEOUT_SECONDS = 15.0
TEXT_RUNNER_CONTEXT_SIZE = 4096
TEXT_RUNNER_SCRIPT_PATH = (repo_root() / "scripts" / "run_text_runner.ps1").resolve()
TEXT_CHAT_SLOT_COUNT = 5
TEXT_CHAT_MAX_VISIBLE_MESSAGES = 80
TEXT_CHAT_CONTEXT_RECENT_MESSAGES = 6
TEXT_CHAT_SUMMARY_MAX_CHARACTERS = 900
TEXT_CHAT_TITLE_MAX_LENGTH = 80
TEXT_WORK_MODE_WRITING = "writing"
TEXT_WORK_MODE_REWRITE = "rewrite"
TEXT_WORK_MODE_IMAGE = "image_prompt"
VALID_TEXT_WORK_MODES = {
    TEXT_WORK_MODE_WRITING,
    TEXT_WORK_MODE_REWRITE,
    TEXT_WORK_MODE_IMAGE,
}
TEXT_MODEL_PROFILE_STANDARD = "standard"
TEXT_MODEL_PROFILE_STRONG_WRITING = "strong_writing"
TEXT_MODEL_PROFILE_MULTILINGUAL = "multilingual"
VALID_TEXT_MODEL_PROFILE_IDS = {
    TEXT_MODEL_PROFILE_STANDARD,
    TEXT_MODEL_PROFILE_STRONG_WRITING,
    TEXT_MODEL_PROFILE_MULTILINGUAL,
}
NEGATIVE_PROMPT_MAX_LENGTH = 2000
VALID_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VALID_UPLOAD_FORMATS = {
    "PNG": (".png", "image/png"),
    "JPEG": (".jpg", "image/jpeg"),
    "WEBP": (".webp", "image/webp"),
}
MAX_MULTI_REFERENCE_SLOTS = 3
ANIME_MOTIF_TUNING_CHECKPOINTS = {
    "anime_standard",
    "animagine-xl-4.0-opt.safetensors",
}
ANIME_MOTIF_TUNING_CFG = 6.2
ANIME_MOTIF_TUNING_STEPS = 24
ANIME_MOTIF_TUNING_NEGATIVE_SUFFIX = (
    "duplicate person, multiple characters, chaotic composition, distorted perspective, cluttered background"
)
PHOTO_INPAINT_CFG = 5.6
PHOTO_INPAINT_STEPS = 28
ANIME_INPAINT_CFG = 6.0
ANIME_INPAINT_STEPS = 28
PHOTO_INPAINT_CLOTHING_CFG = 5.1
PHOTO_INPAINT_CLOTHING_STEPS = 32
ANIME_INPAINT_CLOTHING_CFG = 5.8
ANIME_INPAINT_CLOTHING_STEPS = 32
PHOTO_INPAINT_CLOTHING_FORM_CFG = 4.8
PHOTO_INPAINT_CLOTHING_FORM_STEPS = 30
ANIME_INPAINT_CLOTHING_FORM_CFG = 5.5
ANIME_INPAINT_CLOTHING_FORM_STEPS = 30
INPAINT_CLOTHING_MASK_RATIO_THRESHOLD = 0.08
INPAINT_CLOTHING_DEFAULT_DENOISE = 0.64
INPAINT_CLOTHING_FORM_DEFAULT_DENOISE = 0.60
INPAINT_CLOTHING_GROW_MASK_BY = 0
INPAINT_LOCAL_EDIT_PROMPT_SUFFIX = (
    "precise local inpainting edit, only change inside the mask, keep unmasked areas unchanged, preserve the same person, same photo, same composition, same camera framing, preserve realistic texture and edges, make a clean detailed replacement inside the mask"
)
INPAINT_CLOTHING_EDIT_PROMPT_SUFFIX = (
    "the masked area is clothing or fabric, make a coherent garment replacement inside the mask, preserve the original garment shape, preserve the original neckline, preserve the original coverage and silhouette, preserve realistic folds, seams and fabric texture, change only the masked clothing region"
)
INPAINT_CLOTHING_FORM_EDIT_PROMPT_SUFFIX = (
    "the masked area is existing clothing, keep the same clothing shape, same neckline, same hemline, same coverage, same silhouette and same garment structure, only change color, material, surface finish or fabric texture inside the mask, preserve realistic folds, seams and edges"
)
EDIT_IMAGE_PRESERVATION_PROMPT_SUFFIX = (
    "image edit based on the provided source image, keep the same subject, same composition, same camera framing, preserve the original image structure unless the prompt asks for a small change"
)
EDIT_IMAGE_PRESERVATION_NEGATIVE_SUFFIX = (
    "different person, different face, different composition, different camera angle, different pose, full scene change, background replacement"
)
INPAINT_LOCALITY_NEGATIVE_SUFFIX = (
    "global scene change, different camera angle, different composition, full body replacement, background replacement, extra people, flat gray patch, blank masked area, amorphous blob, smeared clothing, melted object, broken edges"
)
INPAINT_CLOTHING_NEGATIVE_SUFFIX = (
    "scarf, bib, armor plate, floating fabric, detached collar, blanket shape, random cloth blob, melted neckline, warped torso, broken garment edges, turtleneck, high collar, chest plate"
)
INPAINT_CLOTHING_FORM_NEGATIVE_SUFFIX = (
    "new garment shape, different blouse shape, different neckline, different collar, scarf, bib, armor plate, apron shape, poncho shape, blanket shape, chest plate, detached fabric, folded bib, warped hemline"
)
EDIT_DENOISE_DEFAULT = 0.25
EDIT_DENOISE_MAX = 0.55
EDIT_STEPS = 16
EDIT_WAIT_TIMEOUT_SECONDS = 360
INPAINT_DENOISE_DEFAULT = 0.58
INPAINT_DENOISE_MAX = 0.80
MASK_BINARY_THRESHOLD = 96
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
    "pulid_v11_workflow_missing",
    "pulid_v11_workflow_invalid",
    "pulid_v11_custom_node_missing",
    "pulid_v11_models_missing",
    "pulid_v11_nodes_unreachable",
    "pulid_v11_nodes_invalid",
    "pulid_v11_nodes_missing",
}
TEXT_MODEL_SWITCH_LOCK = threading.Lock()


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


def export_root() -> Path:
    return (repo_root() / "data" / "exports").resolve()


def text_chat_db_path() -> Path:
    return (repo_root() / "data" / "text_chats.sqlite3").resolve()


def repo_relative_path(path: Path) -> str:
    return app_paths.repo_relative_path(path, repo_root=repo_root())


UploadRequestError = image_input_validation.UploadRequestError
ResultStoreError = result_output.ResultStoreError


def read_json_file_detail(path: Path) -> tuple[dict | None, str | None]:
    return app_request_utils.read_json_file_detail(path)


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
    runner_port = payload.get("runner_port")
    model_path = payload.get("model_path")

    if enabled is not True:
        return False, None, None
    if not isinstance(host, str) or host.strip() != "127.0.0.1":
        return False, None, "config_invalid"
    if not isinstance(port, int) or port < 1 or port > 65535:
        return False, None, "config_invalid"
    if not isinstance(runner_port, int) or runner_port < 1 or runner_port > 65535:
        return False, None, "config_invalid"

    return True, {
        "host": "127.0.0.1",
        "port": port,
        "runner_port": runner_port,
        "service_name": service_name.strip() if isinstance(service_name, str) and service_name.strip() else None,
        "model_status": model_status.strip() if isinstance(model_status, str) and model_status.strip() else None,
        "runner_type": runner_type.strip() if isinstance(runner_type, str) and runner_type.strip() else None,
        "model_configured": isinstance(model_path, str) and bool(model_path.strip()),
    }, None


def load_text_service_config_payload() -> tuple[dict | None, str | None]:
    payload, error = read_json_file_detail(TEXT_SERVICE_CONFIG_PATH)
    if error is not None:
        return None, error
    if not isinstance(payload, dict):
        return None, "invalid_payload"
    return payload, None


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(path)


def update_text_service_config_payload(*, model_path: str, model_status: str | None = None) -> dict:
    payload, payload_error = load_text_service_config_payload()
    if payload_error is not None or payload is None:
        raise OSError(f"text_service_config_unavailable:{payload_error or 'unknown'}")
    payload["model_path"] = model_path
    if isinstance(model_status, str) and model_status.strip():
        payload["model_status"] = model_status.strip()
    write_json_atomic(TEXT_SERVICE_CONFIG_PATH, payload)
    return payload


def read_text_model_switch_state() -> dict | None:
    payload, error = read_json_file_detail(TEXT_MODEL_SWITCH_STATE_PATH)
    if error is not None or payload is None:
        return None
    return payload


def write_text_model_switch_state(payload: dict) -> None:
    write_json_atomic(TEXT_MODEL_SWITCH_STATE_PATH, payload)


def clear_text_model_switch_state() -> None:
    try:
        if TEXT_MODEL_SWITCH_STATE_PATH.exists():
            TEXT_MODEL_SWITCH_STATE_PATH.unlink()
    except OSError:
        pass


def find_listener_pid(local_port: int) -> int | None:
    script = (
        f"$listener = Get-NetTCPConnection -LocalPort {int(local_port)} -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -First 1 -ExpandProperty OwningProcess; "
        "if ($null -ne $listener) { Write-Output $listener }"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or "").strip()
    if not output:
        return None
    try:
        return int(output.splitlines()[-1].strip())
    except (TypeError, ValueError):
        return None


def stop_text_runner_process(runner_port: int) -> tuple[bool, str | None]:
    pid = find_listener_pid(runner_port)
    if pid is None:
        return True, None
    try:
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if completed.returncode not in {0, 128}:
        stderr_text = (completed.stderr or completed.stdout or "").strip()
        return False, stderr_text or "taskkill_failed"
    deadline = time.time() + TEXT_RUNNER_STOP_TIMEOUT_SECONDS
    while time.time() < deadline:
        if find_listener_pid(runner_port) is None:
            return True, None
        time.sleep(0.5)
    return False, "runner_stop_timeout"


def start_text_runner_process() -> tuple[dict | None, str | None]:
    payload, payload_error = load_text_service_config_payload()
    if payload_error is not None or payload is None:
        return None, payload_error or "text_service_config_unavailable"

    runner_binary_value = payload.get("runner_binary_path")
    model_path_value = payload.get("model_path")
    runner_port = payload.get("runner_port")
    runner_host = payload.get("runner_host")

    if not isinstance(runner_binary_value, str) or not runner_binary_value.strip():
        return None, "runner_binary_missing"
    if not isinstance(model_path_value, str) or not model_path_value.strip():
        return None, "model_missing"
    if not isinstance(runner_port, int):
        return None, "runner_port_invalid"
    if not isinstance(runner_host, str) or not runner_host.strip():
        runner_host = "127.0.0.1"

    runner_binary_path = Path(runner_binary_value.strip())
    if not runner_binary_path.is_absolute():
        runner_binary_path = (repo_root() / runner_binary_path).resolve()
    model_path = Path(model_path_value.strip())
    if not model_path.is_absolute():
        model_path = (repo_root() / model_path).resolve()

    if not runner_binary_path.exists():
        return None, "runner_binary_missing"
    if not model_path.exists():
        return None, "model_missing"

    logs_root = (repo_root() / "vendor" / "text_runner" / "logs").resolve()
    logs_root.mkdir(parents=True, exist_ok=True)
    stdout_log_path = logs_root / "llama-server.stdout.log"
    stderr_log_path = logs_root / "llama-server.stderr.log"

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        stdout_handle = open(stdout_log_path, "a", encoding="utf-8")
        stderr_handle = open(stderr_log_path, "a", encoding="utf-8")
    except OSError as exc:
        return None, str(exc)

    try:
        process = subprocess.Popen(
            [
                str(runner_binary_path),
                "--model",
                str(model_path),
                "--host",
                runner_host.strip() or "127.0.0.1",
                "--port",
                str(runner_port),
                "--ctx-size",
                str(TEXT_RUNNER_CONTEXT_SIZE),
            ],
            stdout=stdout_handle,
            stderr=stderr_handle,
            creationflags=creationflags,
        )
    except OSError as exc:
        stdout_handle.close()
        stderr_handle.close()
        return None, str(exc)

    deadline = time.time() + TEXT_RUNNER_START_TIMEOUT_SECONDS
    while time.time() < deadline:
        runner_payload, runner_error = fetch_json_detail(
            f"http://127.0.0.1:{runner_port}/v1/models",
            timeout=TEXT_SERVICE_PROBE_TIMEOUT,
        )
        if runner_error is None and runner_payload is not None:
            stdout_handle.close()
            stderr_handle.close()
            return {
                "status": "started",
                "port": runner_port,
                "pid": process.pid,
                "url": f"http://127.0.0.1:{runner_port}",
                "runner_binary_path": str(runner_binary_path),
                "model_path": str(model_path),
            }, None
        if process.poll() is not None:
            stdout_handle.close()
            stderr_handle.close()
            return None, f"runner_exited_{process.returncode}"
        time.sleep(0.5)

    try:
        process.kill()
    except OSError:
        pass
    stdout_handle.close()
    stderr_handle.close()
    return None, "runner_start_timeout"


def collect_text_service_state() -> dict:
    configured, config, config_error = load_text_service_config_state()
    health_payload = None
    health_error = None
    info_payload = None
    info_error = None
    if configured and config is not None:
        base_url = f"http://{config['host']}:{config['port']}"
        health_payload, health_error = fetch_json_detail(f"{base_url}/health", timeout=TEXT_SERVICE_PROBE_TIMEOUT)
        if health_error is None and health_payload is not None:
            info_payload, info_error = fetch_json_detail(f"{base_url}/info", timeout=TEXT_SERVICE_PROBE_TIMEOUT)
    return app_status.build_text_service_state(
        configured=configured,
        config=config,
        config_error=config_error,
        model_switch_state=read_text_model_switch_state(),
        health_payload=health_payload,
        health_error=health_error,
        info_payload=info_payload,
        info_error=info_error,
    )


def normalize_text_service_prompt(value: object) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, "prompt_not_string"

    normalized_prompt = value.strip()
    if not normalized_prompt:
        return None, "empty_prompt"

    if len(normalized_prompt) > TEXT_SERVICE_PROMPT_MAX_LENGTH:
        return None, "prompt_too_long"

    return normalized_prompt, None


def normalize_text_work_mode(value: object) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "mode_not_string"
    normalized = value.strip().lower()
    if not normalized:
        return None, None
    if normalized not in VALID_TEXT_WORK_MODES:
        return None, "invalid_mode"
    return normalized, None


def normalize_text_model_profile(value: object) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "model_profile_not_string"
    normalized = value.strip().lower()
    if not normalized:
        return None, None
    if normalized not in VALID_TEXT_MODEL_PROFILE_IDS:
        return None, "invalid_model_profile"
    return normalized, None


def list_local_text_model_paths() -> list[Path]:
    root = (repo_root() / "vendor" / "text_models").resolve()
    if not root.exists() or not root.is_dir():
        return []
    try:
        return sorted((path.resolve() for path in root.glob("*.gguf") if path.is_file()), key=lambda item: item.name.lower())
    except OSError:
        return []


def model_path_matches_keywords(path: Path, keywords: tuple[str, ...]) -> bool:
    normalized_name = path.name.lower()
    return all(keyword in normalized_name for keyword in keywords)


def build_text_model_profiles_state() -> dict:
    payload, payload_error = load_text_service_config_payload()
    configured_model_path = None
    configured_model_name = None
    if payload_error is None and payload is not None:
        model_path_value = payload.get("model_path")
        if isinstance(model_path_value, str) and model_path_value.strip():
            candidate = repo_root() / model_path_value.strip() if not Path(model_path_value.strip()).is_absolute() else Path(model_path_value.strip())
            configured_model_path = candidate.resolve()
            configured_model_name = configured_model_path.name

    available_files = list_local_text_model_paths()
    text_service_state = collect_text_service_state()
    runtime_state = text_service_state.get("text_service") if isinstance(text_service_state, dict) else {}
    runtime_model_status = str(runtime_state.get("model_status") or "").strip().lower()
    runtime_ready = (
        text_service_state.get("text_service_reachable") is True
        and runtime_state.get("inference_available") is True
        and runtime_model_status == "ready"
    )
    switch_state = read_text_model_switch_state() or {}
    switch_phase = str(switch_state.get("phase") or "").strip().lower()
    switch_target_profile = str(switch_state.get("target_profile_id") or "").strip().lower() or None
    switch_error_message = str(switch_state.get("message") or "").strip() or None
    profile_specs = (
        {
            "id": TEXT_MODEL_PROFILE_STANDARD,
            "label": "Standard",
            "subtitle": "Schreiben / Prompt-Hilfe",
            "target_name": "Qwen3-8B",
            "keyword_groups": (
                ("qwen3", "8b"),
                ("qwen2.5", "7b"),
                ("qwen2_5", "7b"),
                ("qwen", "7b"),
            ),
            "fallback_to_configured": True,
        },
        {
            "id": TEXT_MODEL_PROFILE_STRONG_WRITING,
            "label": "Starkes Schreiben",
            "subtitle": "Langes Schreiben",
            "target_name": "Mistral Small 3.1 24B",
            "keyword_groups": (("mistral", "small", "24b"),),
            "fallback_to_configured": False,
        },
        {
            "id": TEXT_MODEL_PROFILE_MULTILINGUAL,
            "label": "Mehrsprachig",
            "subtitle": "Uebersetzen / Umformulieren",
            "target_name": "Gemma 3 12B",
            "keyword_groups": (("gemma", "3", "12b"),),
            "fallback_to_configured": False,
        },
    )

    direct_profile_matches: dict[str, Path | None] = {}
    non_fallback_matched_paths: set[Path] = set()
    for spec in profile_specs:
        keyword_groups = spec.get("keyword_groups") if isinstance(spec.get("keyword_groups"), tuple) else ()
        matched_path = None
        for keywords in keyword_groups:
            matched_path = next((path for path in available_files if model_path_matches_keywords(path, keywords)), None)
            if matched_path is not None:
                break
        direct_profile_matches[spec["id"]] = matched_path
        if matched_path is not None:
            non_fallback_matched_paths.add(matched_path)

    profiles: list[dict] = []
    current_profile_id = None
    for spec in profile_specs:
        resolved_path = direct_profile_matches.get(spec["id"])
        if (
            resolved_path is None
            and spec["fallback_to_configured"]
            and configured_model_path is not None
            and configured_model_path.exists()
            and configured_model_path not in non_fallback_matched_paths
        ):
            resolved_path = configured_model_path

        is_current = configured_model_path is not None and resolved_path is not None and configured_model_path == resolved_path
        status = "prepared"
        status_label = "Vorbereitet"
        selectable = True
        active_for_requests = False
        available = False
        if resolved_path is not None and resolved_path.exists():
            available = True
            if is_current and runtime_ready:
                status = "active"
                status_label = "Aktiv"
                active_for_requests = True
            elif switch_phase == "loading" and switch_target_profile == spec["id"]:
                status = "loading"
                status_label = "Laedt"
                selectable = False
            elif switch_phase == "error" and switch_target_profile == spec["id"]:
                status = "error"
                status_label = "Fehler"
            elif is_current:
                status = "error"
                status_label = "Fehler"
            else:
                status = "installed"
                status_label = "Installiert"
        elif switch_phase == "loading" and switch_target_profile == spec["id"]:
            status = "loading"
            status_label = "Laedt"
            selectable = False
        elif switch_phase == "error" and switch_target_profile == spec["id"]:
            status = "error"
            status_label = "Fehler"

        if is_current:
            current_profile_id = spec["id"]

        actual_model_name = resolved_path.name if resolved_path is not None and resolved_path.exists() else None
        profiles.append(
            {
                "id": spec["id"],
                "label": spec["label"],
                "subtitle": spec["subtitle"],
                "target_model_name": spec["target_name"],
                "actual_model_name": actual_model_name,
                "resolved_model_path": str(resolved_path) if resolved_path is not None and resolved_path.exists() else None,
                "available": available,
                "selectable": selectable,
                "active_for_requests": active_for_requests,
                "status": status,
                "status_label": status_label,
                "error_message": switch_error_message if status == "error" else None,
                "is_current": is_current,
            }
        )

    if current_profile_id is None:
        current_profile_id = TEXT_MODEL_PROFILE_STANDARD

    return {
        "profiles": profiles,
        "current_profile_id": current_profile_id,
        "current_model_name": configured_model_name,
        "switch_state": switch_state if switch_state else None,
    }


def get_text_model_profile(profile_id: str | None) -> dict:
    normalized_profile_id = profile_id if isinstance(profile_id, str) and profile_id in VALID_TEXT_MODEL_PROFILE_IDS else TEXT_MODEL_PROFILE_STANDARD
    profile_state = build_text_model_profiles_state()
    for profile in profile_state["profiles"]:
        if profile["id"] == normalized_profile_id:
            return profile
    return profile_state["profiles"][0]


def resolve_default_text_model_profile_id() -> str:
    return TEXT_MODEL_PROFILE_STANDARD


def ensure_text_model_profile_active(profile_id: str) -> dict:
    normalized_profile_id = profile_id if profile_id in VALID_TEXT_MODEL_PROFILE_IDS else TEXT_MODEL_PROFILE_STANDARD
    with TEXT_MODEL_SWITCH_LOCK:
        profile = get_text_model_profile(normalized_profile_id)
        if profile.get("available") is not True:
            return {
                "ok": False,
                "blocker": "text_model_profile_unavailable",
                "message": "Dieses Modellprofil ist lokal noch nicht verfuegbar.",
                "profile": profile,
            }

        target_model_path = profile.get("resolved_model_path")
        if not isinstance(target_model_path, str) or not target_model_path.strip():
            return {
                "ok": False,
                "blocker": "text_model_profile_unavailable",
                "message": "Kein lokaler Modellpfad fuer dieses Profil gefunden.",
                "profile": profile,
            }

        profile_state = build_text_model_profiles_state()
        current_profile_id = profile_state.get("current_profile_id")
        if profile.get("active_for_requests") is True and current_profile_id == normalized_profile_id:
            clear_text_model_switch_state()
            return {
                "ok": True,
                "changed": False,
                "profile": profile,
            }

        configured, config, config_error = load_text_service_config_state()
        if not configured or config is None:
            return {
                "ok": False,
                "blocker": config_error or "text_service_not_configured",
                "message": "Die Text-KI-Konfiguration ist nicht verfuegbar.",
                "profile": profile,
            }

        write_text_model_switch_state(
            {
                "phase": "loading",
                "target_profile_id": normalized_profile_id,
                "target_model_name": profile.get("actual_model_name") or profile.get("target_model_name"),
                "message": "Modell wird geladen.",
                "updated_at_utc": utc_now_iso(),
            }
        )

        try:
            update_text_service_config_payload(model_path=repo_relative_path(Path(target_model_path)), model_status="configured")
            stopped_ok, stop_error = stop_text_runner_process(int(config.get("runner_port", 8092)))
            if not stopped_ok:
                raise OSError(stop_error or "text_runner_stop_failed")
            start_payload, start_error = start_text_runner_process()
            if start_error is not None:
                raise OSError(start_error)
        except OSError as exc:
            write_text_model_switch_state(
                {
                    "phase": "error",
                    "target_profile_id": normalized_profile_id,
                    "target_model_name": profile.get("actual_model_name") or profile.get("target_model_name"),
                    "message": str(exc),
                    "updated_at_utc": utc_now_iso(),
                }
            )
            return {
                "ok": False,
                "blocker": "text_model_switch_failed",
                "message": str(exc),
                "profile": profile,
            }

        clear_text_model_switch_state()
        refreshed_profile = get_text_model_profile(normalized_profile_id)
        return {
            "ok": refreshed_profile.get("active_for_requests") is True,
            "changed": current_profile_id != normalized_profile_id or profile.get("active_for_requests") is not True,
            "profile": refreshed_profile,
            "runner_result": start_payload,
            "blocker": None if refreshed_profile.get("active_for_requests") is True else "text_model_switch_not_ready",
            "message": None if refreshed_profile.get("active_for_requests") is True else "Das Modellprofil konnte nicht aktiv geladen werden.",
        }


def request_text_service_prompt(
    prompt: str,
    *,
    mode: str | None = None,
    summary: str | None = None,
    recent_messages: list[dict[str, str]] | None = None,
) -> tuple[dict | None, str | None, int | None, str | None, str | None]:
    configured, config, config_error = load_text_service_config_state()
    if not configured or config is None:
        return None, config_error or "text_service_not_configured", None, None, None

    service_name = config["service_name"]
    model_status = config["model_status"]
    request_payload: dict[str, object] = {"prompt": prompt}
    if isinstance(mode, str) and mode.strip():
        request_payload["mode"] = mode.strip()
    if isinstance(summary, str) and summary.strip():
        request_payload["summary"] = summary.strip()
    if isinstance(recent_messages, list) and recent_messages:
        request_payload["recent_messages"] = recent_messages
    response_payload, response_error, response_status = post_json_detail(
        f"http://{config['host']}:{config['port']}/prompt",
        timeout=TEXT_SERVICE_PROMPT_TIMEOUT,
        payload=request_payload,
    )
    return response_payload, response_error, response_status, service_name, model_status


def should_retry_text_service_prompt_after_switch(
    *,
    switch_result: dict | None,
    response_error: str | None,
    response_status: int | None,
) -> bool:
    if not isinstance(switch_result, dict) or switch_result.get("changed") is not True:
        return False
    if response_error in {"unreachable", "timeout"}:
        return True
    if response_status in {HTTPStatus.BAD_GATEWAY, HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.GATEWAY_TIMEOUT}:
        return True
    return False


def normalize_optional_negative_prompt(value: object) -> tuple[str | None, str | None]:
    return image_input_validation.normalize_optional_negative_prompt(
        value,
        max_length=NEGATIVE_PROMPT_MAX_LENGTH,
    )


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
    return identity_status.resolve_identity_reference_status_code(
        error_type=error_type,
        blocker=blocker,
        service_unavailable_blockers=IDENTITY_REFERENCE_SERVICE_UNAVAILABLE_BLOCKERS,
    )


def resolve_identity_multi_reference_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    return identity_status.resolve_identity_multi_reference_status_code(
        error_type=error_type,
        blocker=blocker,
        reference_status_resolver=resolve_identity_reference_status_code,
    )


def resolve_identity_transfer_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    return identity_status.resolve_identity_transfer_status_code(
        error_type=error_type,
        blocker=blocker,
    )


def resolve_identity_transfer_generate_status_code(*, error_type: str | None, blocker: str | None) -> HTTPStatus:
    return identity_status.resolve_identity_transfer_generate_status_code(
        error_type=error_type,
        blocker=blocker,
        reference_status_resolver=resolve_identity_reference_status_code,
    )


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
    return upload_store.build_upload_success_response(payload)


def build_multi_reference_upload_success_response(payload: dict) -> dict:
    return upload_store.build_multi_reference_upload_success_response(payload)


def build_identity_transfer_upload_success_response(payload: dict) -> dict:
    return upload_store.build_identity_transfer_upload_success_response(payload)


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


def build_text_chat_error_response(*, error_type: str, blocker: str, message: str) -> dict:
    return {
        "status": "error",
        "ok": False,
        "error_type": error_type,
        "blocker": blocker,
        "message": message,
    }


def text_chat_dir_access_state() -> tuple[bool, str | None]:
    return chat_store.text_chat_dir_access_state(text_chat_db_path())


def text_chat_connection():
    return chat_store.text_chat_connection(text_chat_db_path())


def ensure_text_chat_store() -> None:
    chat_store.ensure_text_chat_store(text_chat_db_path(), slot_count=TEXT_CHAT_SLOT_COUNT)


def normalize_text_chat_slot_index(value: object) -> int:
    return chat_store.normalize_text_chat_slot_index(value, slot_count=TEXT_CHAT_SLOT_COUNT)


def normalize_text_chat_title(value: object) -> tuple[str | None, str | None]:
    return chat_store.normalize_text_chat_title(value, max_length=TEXT_CHAT_TITLE_MAX_LENGTH)


def build_default_text_chat_title(slot_index: int) -> str:
    return chat_store.build_default_text_chat_title(slot_index)


def excerpt_text(value: str, *, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 1)].rstrip()}…"


def infer_text_chat_language_from_text(value: str) -> str:
    sample = f" {str(value or '').lower()} "
    german_score = 0
    english_score = 0
    german_tokens = (" der ", " die ", " das ", " und ", " nicht ", " bitte ", " fuer ", " für ", " mit ", " ich ")
    english_tokens = (" the ", " and ", " please ", " with ", " this ", " that ", " write ", " prompt ", " image ")
    if re.search(r"[äöüß]", sample):
        german_score += 2
    german_score += sum(1 for token in german_tokens if token in sample)
    english_score += sum(1 for token in english_tokens if token in sample)
    return "en" if english_score > german_score else "de"


def resolve_text_chat_model_label() -> str | None:
    configured, config, _ = load_text_service_config_state()
    if not configured or config is None:
        return None
    payload, error = read_json_file_detail(TEXT_SERVICE_CONFIG_PATH)
    if error is None and payload is not None:
        model_path_value = payload.get("model_path")
        if isinstance(model_path_value, str) and model_path_value.strip():
            return Path(model_path_value.strip()).name
    return config.get("model_status")


def get_active_text_chat_slot_index() -> int:
    return chat_store.get_active_text_chat_slot_index(
        text_chat_db_path(),
        slot_count=TEXT_CHAT_SLOT_COUNT,
    )


def set_active_text_chat_slot_index(slot_index: int) -> None:
    chat_store.set_active_text_chat_slot_index(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
    )


def list_text_chat_messages(slot_index: int, *, limit: int = TEXT_CHAT_MAX_VISIBLE_MESSAGES) -> list[dict]:
    return chat_store.list_text_chat_messages(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
        limit=limit,
    )


def build_text_chat_summary(messages: list[dict]) -> str | None:
    return chat_store.build_text_chat_summary(
        messages,
        recent_messages_count=TEXT_CHAT_CONTEXT_RECENT_MESSAGES,
        summary_max_characters=TEXT_CHAT_SUMMARY_MAX_CHARACTERS,
    )


def update_text_chat_slot_metadata(
    slot_index: int,
    *,
    title: str | None = None,
    summary: str | None = None,
    language: str | None = None,
    model_profile: str | None = None,
    model: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> None:
    chat_store.update_text_chat_slot_metadata(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
        title=title,
        summary=summary,
        language=language,
        model_profile=model_profile,
        model=model,
        created_at=created_at,
        updated_at=updated_at,
    )


def clear_text_chat_slot(slot_index: int) -> None:
    chat_store.clear_text_chat_slot(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
    )


def create_text_chat_in_slot(slot_index: int, *, title: str | None = None) -> dict:
    normalized_title = title or build_default_text_chat_title(slot_index)
    default_profile_id = TEXT_MODEL_PROFILE_STANDARD
    default_profile = get_text_model_profile(default_profile_id)
    return chat_store.create_text_chat_in_slot(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
        title=normalized_title,
        now_iso=utc_now_iso(),
        default_model_profile=default_profile_id,
        default_model_label=default_profile.get("actual_model_name") or resolve_text_chat_model_label(),
        default_visible_messages_limit=TEXT_CHAT_MAX_VISIBLE_MESSAGES,
    )


def create_text_chat_in_first_empty_slot(*, title: str | None = None) -> dict | None:
    default_profile_id = TEXT_MODEL_PROFILE_STANDARD
    default_profile = get_text_model_profile(default_profile_id)
    return chat_store.create_text_chat_in_first_empty_slot(
        text_chat_db_path(),
        slot_count=TEXT_CHAT_SLOT_COUNT,
        title=title,
        now_iso=utc_now_iso(),
        default_model_profile=default_profile_id,
        default_model_label=default_profile.get("actual_model_name") or resolve_text_chat_model_label(),
        default_visible_messages_limit=TEXT_CHAT_MAX_VISIBLE_MESSAGES,
    )


def append_text_chat_message(slot_index: int, *, role: str, content: str) -> None:
    chat_store.append_text_chat_message(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
        role=role,
        content=content,
        now_iso=utc_now_iso(),
    )


def get_text_chat_slot(slot_index: int) -> dict:
    slot_data = chat_store.get_text_chat_slot(
        text_chat_db_path(),
        slot_index,
        slot_count=TEXT_CHAT_SLOT_COUNT,
        default_model_profile=TEXT_MODEL_PROFILE_STANDARD,
        visible_messages_limit=TEXT_CHAT_MAX_VISIBLE_MESSAGES,
    )
    return chat_payloads.build_text_chat_active_chat_payload(
        slot_index,
        slot_data,
        default_title=build_default_text_chat_title(slot_index),
        default_model_profile=TEXT_MODEL_PROFILE_STANDARD,
    )


def list_text_chat_slots() -> list[dict]:
    slot_data = chat_store.list_text_chat_slots(
        text_chat_db_path(),
        slot_count=TEXT_CHAT_SLOT_COUNT,
        default_model_profile=TEXT_MODEL_PROFILE_STANDARD,
        visible_messages_limit=TEXT_CHAT_MAX_VISIBLE_MESSAGES,
    )
    return [
        chat_payloads.build_text_chat_slot_overview_payload(
            int(slot.get("slot_index") or slot_index),
            slot,
            default_title=build_default_text_chat_title(int(slot.get("slot_index") or slot_index)),
            default_model_profile=TEXT_MODEL_PROFILE_STANDARD,
            preview_limit=100,
        )
        for slot_index, slot in enumerate(slot_data, start=1)
    ]


def build_text_chat_prompt(current_prompt: str, *, summary: str | None, recent_messages: list[dict]) -> str:
    return current_prompt.strip()


def build_text_chat_overview_payload() -> dict:
    active_slot_index = get_active_text_chat_slot_index()
    active_chat = get_text_chat_slot(active_slot_index)
    profile_state = build_text_model_profiles_state()
    return chat_payloads.build_text_chat_overview_payload(
        slot_count=TEXT_CHAT_SLOT_COUNT,
        active_slot_index=active_slot_index,
        active_chat=active_chat,
        slots=list_text_chat_slots(),
        profile_state=profile_state,
    )


def resolve_text_chat_slot_request_path(request_path: str) -> tuple[int, str | None] | None:
    return chat_requests.resolve_text_chat_slot_request_path(
        request_path,
        slots_path=TEXT_CHAT_SLOTS_PATH,
        slot_index_normalizer=normalize_text_chat_slot_index,
    )

def output_dir_access_state() -> tuple[bool, str | None]:
    root = output_root()
    if not root.exists():
        return False, "output_dir_missing"
    return app_paths.dir_access_state(
        root,
        not_directory_blocker="output_dir_not_directory",
        not_accessible_blocker="output_dir_not_accessible",
    )


def input_dir_access_state() -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        input_root(),
        not_directory_blocker="input_dir_not_directory",
        not_accessible_blocker="input_dir_not_accessible",
    )


def reference_dir_access_state() -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        reference_root(),
        not_directory_blocker="reference_dir_not_directory",
        not_accessible_blocker="reference_dir_not_accessible",
    )


def multi_reference_dir_access_state() -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        multi_reference_root(),
        not_directory_blocker="multi_reference_dir_not_directory",
        not_accessible_blocker="multi_reference_dir_not_accessible",
    )


def mask_dir_access_state() -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        mask_root(),
        not_directory_blocker="mask_dir_not_directory",
        not_accessible_blocker="mask_dir_not_accessible",
    )


def identity_transfer_dir_access_state(role: str) -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        identity_transfer_role_root(role),
        not_directory_blocker="identity_transfer_role_dir_not_directory",
        not_accessible_blocker="identity_transfer_role_dir_not_accessible",
    )


def results_dir_access_state() -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        result_root(),
        not_directory_blocker="results_dir_not_directory",
        not_accessible_blocker="results_dir_not_accessible",
    )


def exports_dir_access_state() -> tuple[bool, str | None]:
    return app_paths.dir_access_state(
        export_root(),
        not_directory_blocker="exports_dir_not_directory",
        not_accessible_blocker="exports_dir_not_accessible",
    )


def resolve_internal_output_path(output_file: str | Path | None) -> tuple[Path | None, str | None]:
    return app_paths.resolve_internal_output_path(output_file, output_root=output_root())


def is_accessible_output_file(path: Path) -> bool:
    return app_paths.is_accessible_output_file(path)


def output_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=output_root(), route_prefix=OUTPUT_ROUTE_PREFIX)


def input_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=input_root(), route_prefix=INPUT_ROUTE_PREFIX)


def reference_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=reference_root(), route_prefix=REFERENCE_ROUTE_PREFIX)


def multi_reference_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=multi_reference_root(), route_prefix=MULTI_REFERENCE_ROUTE_PREFIX)


def mask_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=mask_root(), route_prefix=MASK_ROUTE_PREFIX)


def identity_transfer_path_to_web_path(path: Path, role: str) -> str:
    return app_paths.identity_transfer_path_to_web_path(
        path,
        role=role,
        role_root=identity_transfer_role_root(role),
        route_prefix=IDENTITY_TRANSFER_ROUTE_PREFIX,
    )


def result_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=result_root(), route_prefix=RESULT_FILE_ROUTE_PREFIX)


def export_path_to_web_path(path: Path) -> str:
    return app_paths.path_to_web_path(path, root=export_root(), route_prefix=EXPORT_FILE_ROUTE_PREFIX)


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
    return app_paths.resolve_request_path(request_path, route_prefix=OUTPUT_ROUTE_PREFIX, root=output_root())


def resolve_input_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_request_path(request_path, route_prefix=INPUT_ROUTE_PREFIX, root=input_root())


def resolve_reference_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_request_path(request_path, route_prefix=REFERENCE_ROUTE_PREFIX, root=reference_root())


def resolve_multi_reference_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_multi_reference_request_path(
        request_path,
        route_prefix=MULTI_REFERENCE_ROUTE_PREFIX,
        root=multi_reference_root(),
    )


def resolve_mask_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_request_path(request_path, route_prefix=MASK_ROUTE_PREFIX, root=mask_root())


def resolve_identity_transfer_role_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_identity_transfer_role_request_path(
        request_path,
        route_prefix=IDENTITY_TRANSFER_ROUTE_PREFIX,
        allowed_roles=IDENTITY_TRANSFER_ROLE_SET,
        role_root_builder=identity_transfer_role_root,
    )


def resolve_result_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_request_path(request_path, route_prefix=RESULT_FILE_ROUTE_PREFIX, root=result_root())


def resolve_export_request_path(request_path: str) -> Path | None:
    return app_paths.resolve_request_path(request_path, route_prefix=EXPORT_FILE_ROUTE_PREFIX, root=export_root())


def resolve_result_download_request_id(request_path: str) -> str | None:
    return app_paths.resolve_result_download_request_id(
        request_path,
        route_prefix=RESULT_DOWNLOAD_ROUTE_PREFIX,
    )


def resolve_multi_reference_slot_reset_index(request_path: str) -> int | None:
    return app_paths.resolve_multi_reference_slot_reset_index(
        request_path,
        route_prefix=MULTI_REFERENCE_IMAGE_SLOT_RESET_PREFIX,
        slot_parser=parse_required_multi_reference_slot_index,
    )


def parse_results_limit(query_string: str) -> int:
    return app_request_utils.parse_results_limit(
        query_string,
        default_limit=RESULTS_DEFAULT_LIMIT,
        max_limit=RESULTS_MAX_LIMIT,
    )


def decode_data_url_image(data_url: object) -> tuple[str, bytes]:
    return app_request_utils.decode_data_url_image(
        data_url,
        valid_upload_mime_types=VALID_UPLOAD_MIME_TYPES,
        upload_error_cls=UploadRequestError,
    )


def validate_mode(value: object) -> str:
    return app_request_utils.validate_mode(value, valid_modes=VALID_MODES)


def parse_boolean_flag(value: object, *, default: bool = False) -> bool:
    return app_request_utils.parse_boolean_flag(value, default=default)


def normalize_denoise_strength_value(
    value: object,
    *,
    for_inpainting: bool = False,
    for_edit: bool = False,
) -> float:
    if for_inpainting:
        default_value = INPAINT_DENOISE_DEFAULT
        max_value = INPAINT_DENOISE_MAX
    elif for_edit:
        default_value = EDIT_DENOISE_DEFAULT
        max_value = EDIT_DENOISE_MAX
    else:
        default_value = DEFAULT_DENOISE_STRENGTH
        max_value = MAX_DENOISE_STRENGTH
    if value is None or value == "":
        return default_value
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_denoise_strength") from exc
    if not numeric_value == numeric_value:
        raise ValueError("invalid_denoise_strength")
    return max(MIN_DENOISE_STRENGTH, min(max_value, numeric_value))


def analyze_mask_characteristics(mask_image_path: Path | None) -> dict:
    if mask_image_path is None:
        return {
            "area_ratio": 0.0,
            "bbox": None,
        }

    try:
        with Image.open(mask_image_path) as raw_mask:
            grayscale = raw_mask.convert("L")
            binary_mask = grayscale.point(lambda value: 255 if value >= MASK_BINARY_THRESHOLD else 0, mode="L")
            bbox = binary_mask.getbbox()
            width, height = binary_mask.size
            total_pixels = max(1, width * height)
            painted_pixels = sum(1 for value in binary_mask.getdata() if value > 0)
    except OSError:
        return {
            "area_ratio": 0.0,
            "bbox": None,
        }

    return {
        "area_ratio": painted_pixels / total_pixels,
        "bbox": bbox,
    }


def prompt_targets_clothing_edit(prompt: str) -> bool:
    normalized = str(prompt or "").strip().lower()
    if not normalized:
        return False
    keyword_groups = (
        ("dress",),
        ("shirt",),
        ("top",),
        ("blouse",),
        ("jacket",),
        ("coat",),
        ("hoodie",),
        ("sweater",),
        ("skirt",),
        ("pants",),
        ("trousers",),
        ("jeans",),
        ("fabric",),
        ("garment",),
        ("clothing",),
        ("outfit",),
        ("satin",),
        ("silk",),
        ("cotton",),
        ("leather",),
        ("color", "shirt"),
        ("color", "dress"),
        ("farbe",),
        ("kleid",),
        ("bluse",),
        ("jacke",),
        ("stoff",),
        ("kleidung",),
        ("oberteil",),
        ("rock",),
        ("hose",),
    )
    for keywords in keyword_groups:
        if all(keyword in normalized for keyword in keywords):
            return True
    return False


def prompt_targets_clothing_appearance_change(prompt: str) -> bool:
    normalized = str(prompt or "").strip().lower()
    if not normalized:
        return False
    keywords = (
        "color",
        "colour",
        "farbe",
        "fabric",
        "stoff",
        "texture",
        "textur",
        "material",
        "surface",
        "finish",
        "silk",
        "satin",
        "linen",
        "cotton",
        "leather",
        "matte",
        "glossy",
        "emerald",
        "green",
        "blue",
        "navy",
        "red",
        "black",
        "white",
        "gold",
    )
    return any(keyword in normalized for keyword in keywords)


def resolve_inpainting_tuning(
    *,
    prompt: str,
    checkpoint: str | None,
    mask_image_path: Path | None,
    requested_denoise_strength: object,
) -> dict:
    mask_info = analyze_mask_characteristics(mask_image_path)
    area_ratio = float(mask_info.get("area_ratio") or 0.0)
    large_mask = area_ratio >= INPAINT_CLOTHING_MASK_RATIO_THRESHOLD
    clothing_edit = prompt_targets_clothing_edit(prompt)
    clothing_appearance_change = prompt_targets_clothing_appearance_change(prompt)
    apply_clothing_profile = large_mask and clothing_edit
    checkpoint_is_anime = checkpoint_token(checkpoint) in ANIME_MOTIF_TUNING_CHECKPOINTS
    denoise_missing = requested_denoise_strength is None or requested_denoise_strength == ""

    if apply_clothing_profile:
        form_preserving_profile = clothing_appearance_change
        return {
            "apply_clothing_profile": True,
            "cfg": (
                ANIME_INPAINT_CLOTHING_FORM_CFG if checkpoint_is_anime else PHOTO_INPAINT_CLOTHING_FORM_CFG
            ) if form_preserving_profile else (
                ANIME_INPAINT_CLOTHING_CFG if checkpoint_is_anime else PHOTO_INPAINT_CLOTHING_CFG
            ),
            "steps": (
                ANIME_INPAINT_CLOTHING_FORM_STEPS if checkpoint_is_anime else PHOTO_INPAINT_CLOTHING_FORM_STEPS
            ) if form_preserving_profile else (
                ANIME_INPAINT_CLOTHING_STEPS if checkpoint_is_anime else PHOTO_INPAINT_CLOTHING_STEPS
            ),
            "prompt_suffix": INPAINT_CLOTHING_FORM_EDIT_PROMPT_SUFFIX if form_preserving_profile else INPAINT_CLOTHING_EDIT_PROMPT_SUFFIX,
            "negative_suffix": INPAINT_CLOTHING_FORM_NEGATIVE_SUFFIX if form_preserving_profile else INPAINT_CLOTHING_NEGATIVE_SUFFIX,
            "denoise_strength": (
                INPAINT_CLOTHING_FORM_DEFAULT_DENOISE if form_preserving_profile else INPAINT_CLOTHING_DEFAULT_DENOISE
            ) if denoise_missing else None,
            "grow_mask_by": INPAINT_CLOTHING_GROW_MASK_BY,
            "mask_area_ratio": area_ratio,
            "form_preserving_profile": form_preserving_profile,
        }

    return {
        "apply_clothing_profile": False,
        "cfg": None,
        "steps": None,
        "prompt_suffix": None,
        "negative_suffix": None,
        "denoise_strength": None,
        "grow_mask_by": None,
        "mask_area_ratio": area_ratio,
    }


def sanitize_original_name(filename: str | None) -> str:
    return image_input_validation.sanitize_original_name(filename)


def normalize_upload_source_type(value: str | None) -> str:
    return image_input_validation.normalize_upload_source_type(
        value,
        valid_source_types=VALID_UPLOAD_SOURCE_TYPES,
    )


def parse_multipart_image(content_type: str, body: bytes) -> tuple[str, bytes, str]:
    return image_input_validation.parse_multipart_image(
        content_type,
        body,
        source_type_normalizer=normalize_upload_source_type,
    )


def parse_multipart_multi_reference_image(content_type: str, body: bytes) -> tuple[str, bytes, int | None]:
    return image_input_validation.parse_multipart_multi_reference_image(
        content_type,
        body,
        slot_index_parser=parse_optional_multi_reference_slot_index,
    )


def parse_multipart_identity_transfer_role_image(content_type: str, body: bytes) -> tuple[str, bytes, str]:
    return image_input_validation.parse_multipart_identity_transfer_role_image(
        content_type,
        body,
        role_parser=parse_required_identity_transfer_role,
    )


def inspect_image_upload(original_name: str, payload: bytes) -> dict:
    return image_input_validation.inspect_image_upload(
        original_name,
        payload,
        valid_extensions=VALID_UPLOAD_EXTENSIONS,
        upload_max_bytes=UPLOAD_MAX_BYTES,
        valid_formats=VALID_UPLOAD_FORMATS,
    )


def normalize_mask_upload_payload(payload: bytes) -> tuple[bytes, dict]:
    return image_input_validation.normalize_mask_upload_payload(
        payload,
        mask_binary_threshold=MASK_BINARY_THRESHOLD,
    )


def validate_browser_mask_payload(payload: bytes, source_image_path: Path) -> None:
    image_input_validation.validate_browser_mask_payload(
        payload,
        source_image_path,
        mask_binary_threshold=MASK_BINARY_THRESHOLD,
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
    return image_input_validation.parse_required_identity_transfer_role(
        value,
        allowed_roles=IDENTITY_TRANSFER_ROLE_SET,
    )


def parse_optional_multi_reference_slot_index(value: object) -> int | None:
    return image_input_validation.parse_optional_multi_reference_slot_index(
        value,
        max_slots=MAX_MULTI_REFERENCE_SLOTS,
    )


def parse_required_multi_reference_slot_index(value: object) -> int:
    return image_input_validation.parse_required_multi_reference_slot_index(
        value,
        max_slots=MAX_MULTI_REFERENCE_SLOTS,
    )


def resolve_identity_transfer_role_reset_name(request_path: str) -> str | None:
    return app_paths.resolve_identity_transfer_role_reset_name(
        request_path,
        route_prefix=IDENTITY_TRANSFER_ROLE_RESET_PREFIX,
        role_parser=parse_required_identity_transfer_role,
    )


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
    return upload_store.input_metadata_path(path)


def write_input_metadata(path: Path, metadata: dict) -> None:
    upload_store.write_input_metadata(path, metadata)


def read_input_metadata(path: Path) -> dict | None:
    return upload_store.read_input_metadata(path)


def describe_stored_input_image(path: Path) -> dict | None:
    return upload_store.describe_stored_input_image(
        path,
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        valid_upload_formats=VALID_UPLOAD_FORMATS,
        valid_upload_source_types=VALID_UPLOAD_SOURCE_TYPES,
        preview_url_builder=input_path_to_web_path,
    )


def describe_stored_mask_image(path: Path) -> dict | None:
    return upload_store.describe_stored_mask_image(
        path,
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        valid_upload_formats=VALID_UPLOAD_FORMATS,
        preview_url_builder=mask_path_to_web_path,
    )


def describe_stored_reference_image(path: Path) -> dict | None:
    return upload_store.describe_stored_reference_image(
        path,
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        valid_upload_formats=VALID_UPLOAD_FORMATS,
        preview_url_builder=reference_path_to_web_path,
    )


def current_input_image_state() -> dict | None:
    return upload_store.current_input_image_state(
        input_root(),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        describe_callback=describe_stored_input_image,
    )


def current_mask_image_state() -> dict | None:
    return upload_store.current_mask_image_state(
        mask_root(),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        describe_callback=describe_stored_mask_image,
    )


def current_reference_image_state() -> dict | None:
    return upload_store.current_reference_image_state(
        reference_root(),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        describe_callback=describe_stored_reference_image,
    )


def describe_stored_identity_transfer_role_image(path: Path, role: str) -> dict | None:
    return upload_store.describe_stored_identity_transfer_role_image(
        path,
        role,
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        valid_upload_formats=VALID_UPLOAD_FORMATS,
        preview_url_builder=identity_transfer_path_to_web_path,
    )


def current_identity_transfer_role_state(role: str) -> dict | None:
    return upload_store.current_identity_transfer_role_state(
        identity_transfer_role_root(role),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        describe_callback=lambda path: describe_stored_identity_transfer_role_image(path, role),
    )


def build_identity_transfer_status_payload() -> dict:
    return identity_status.build_identity_transfer_status_payload(
        roles=IDENTITY_TRANSFER_ROLES,
        required_roles=IDENTITY_TRANSFER_REQUIRED_ROLES,
        role_dir_state_resolver=identity_transfer_dir_access_state,
        role_image_state_resolver=current_identity_transfer_role_state,
    )


def list_stored_multi_reference_images() -> list[dict]:
    return upload_store.list_stored_multi_reference_images(
        multi_reference_root(),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        describe_callback=describe_stored_multi_reference_image,
    )


def build_multi_reference_status_payload() -> dict:
    return multi_reference_status.build_multi_reference_status_payload(
        list_stored_multi_reference_images(),
        max_slots=MAX_MULTI_REFERENCE_SLOTS,
    )


def find_first_free_multi_reference_slot() -> int | None:
    return multi_reference_status.find_first_free_multi_reference_slot(
        build_multi_reference_status_payload()
    )


def store_uploaded_image(original_name: str, payload: bytes, source_type: str) -> dict:
    return upload_store.store_uploaded_image(
        original_name,
        payload,
        source_type,
        normalize_source_type=normalize_upload_source_type,
        mask_root=mask_root,
        input_root=input_root,
        mask_dir_access_state=mask_dir_access_state,
        input_dir_access_state=input_dir_access_state,
        inspect_image_upload=inspect_image_upload,
        normalize_mask_upload_payload=normalize_mask_upload_payload,
        clear_stored_mask_images=clear_stored_mask_images,
        clear_stored_input_images=clear_stored_input_images,
        describe_stored_mask_image=describe_stored_mask_image,
        describe_stored_input_image=describe_stored_input_image,
        is_accessible_output_file=is_accessible_output_file,
    )


def store_reference_image(original_name: str, payload: bytes) -> dict:
    return upload_store.store_reference_image(
        original_name,
        payload,
        reference_root=reference_root,
        reference_dir_access_state=reference_dir_access_state,
        inspect_image_upload=inspect_image_upload,
        clear_stored_reference_images=clear_stored_reference_images,
        describe_stored_reference_image=describe_stored_reference_image,
        is_accessible_output_file=is_accessible_output_file,
    )


def store_multi_reference_image(original_name: str, payload: bytes, *, slot_index: int | None) -> dict:
    return upload_store.store_multi_reference_image(
        original_name,
        payload,
        slot_index=slot_index,
        multi_reference_root=multi_reference_root,
        multi_reference_dir_access_state=multi_reference_dir_access_state,
        inspect_image_upload=inspect_image_upload,
        find_first_free_multi_reference_slot=find_first_free_multi_reference_slot,
        clear_stored_multi_reference_images=clear_stored_multi_reference_images,
        describe_stored_multi_reference_image=describe_stored_multi_reference_image,
        is_accessible_output_file=is_accessible_output_file,
        utc_now_iso=utc_now_iso,
    )


def store_identity_transfer_role_image(original_name: str, payload: bytes, *, role: str) -> dict:
    return upload_store.store_identity_transfer_role_image(
        original_name,
        payload,
        role=role,
        identity_transfer_role_root=identity_transfer_role_root,
        identity_transfer_dir_access_state=identity_transfer_dir_access_state,
        inspect_image_upload=inspect_image_upload,
        clear_stored_identity_transfer_role_images=clear_stored_identity_transfer_role_images,
        describe_stored_identity_transfer_role_image=describe_stored_identity_transfer_role_image,
        is_accessible_output_file=is_accessible_output_file,
        utc_now_iso=utc_now_iso,
    )


def describe_stored_multi_reference_image(path: Path) -> dict | None:
    return upload_store.describe_stored_multi_reference_image(
        path,
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        valid_upload_formats=VALID_UPLOAD_FORMATS,
        preview_url_builder=multi_reference_path_to_web_path,
        required_slot_index_parser=parse_required_multi_reference_slot_index,
    )


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
    return result_output.inspect_result_image(
        path,
        valid_upload_formats=VALID_UPLOAD_FORMATS,
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
    )


def write_result_metadata(path: Path, metadata: dict) -> None:
    result_output.write_result_metadata(path, metadata)


def get_result_retention_limit() -> int:
    return result_output.get_result_retention_limit(
        raw_value=os.environ.get(RESULT_RETENTION_ENV_VAR),
        default_limit=RESULT_RETENTION_DEFAULT,
    )


def is_managed_result_id(value: object) -> bool:
    return result_output.is_managed_result_id(value, pattern=MANAGED_RESULT_ID_PATTERN)


def resolve_result_mode_name(render_mode: object, *, use_input_image: bool, use_inpainting: bool) -> str:
    return result_output.resolve_result_mode_name(
        render_mode,
        use_input_image=use_input_image,
        use_inpainting=use_inpainting,
        identity_research_mode=IDENTITY_RESEARCH_MODE,
        identity_reference_mode=IDENTITY_REFERENCE_MODE,
        identity_multi_reference_mode=IDENTITY_MULTI_REFERENCE_MODE,
        identity_transfer_mode=IDENTITY_TRANSFER_MODE,
        identity_transfer_mask_hybrid_mode=IDENTITY_TRANSFER_MASK_HYBRID_MODE,
    )


def build_result_metadata_item(metadata_payload: dict, image_path: Path) -> dict | None:
    return result_output.build_result_metadata_item(
        metadata_payload,
        image_path,
        result_root=result_root(),
        is_accessible_output_file=is_accessible_output_file,
        inspect_result_image=inspect_result_image,
        retention_limit=get_result_retention_limit(),
        default_retention_limit=RESULT_RETENTION_DEFAULT,
        preview_url_builder=result_path_to_web_path,
        download_url_builder=result_id_to_download_url,
    )


def list_result_store_records() -> list[dict]:
    return result_output.list_result_store_records(
        result_root=result_root(),
        read_json_file_detail=read_json_file_detail,
        is_accessible_output_file=is_accessible_output_file,
    )


def cleanup_result_store_housekeeping(
    *,
    valid_result_ids: set[str] | None = None,
    stale_tmp_age_seconds: int = RESULT_TEMP_STALE_SECONDS,
) -> dict:
    return result_output.cleanup_result_store_housekeeping(
        result_root=result_root(),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
        is_managed_result_id=is_managed_result_id,
        managed_result_tmp_pattern=MANAGED_RESULT_TMP_FILE_PATTERN,
        valid_result_ids=valid_result_ids,
        stale_tmp_age_seconds=stale_tmp_age_seconds,
        error_logger=lambda message: print(message, file=sys.stderr, flush=True),
    )


def enforce_result_retention(*, retain_count: int | None = None) -> dict:
    return result_output.enforce_result_retention(
        retain_count=retain_count,
        default_retention_limit=RESULT_RETENTION_DEFAULT,
        list_result_store_records=list_result_store_records,
        is_managed_result_id=is_managed_result_id,
        cleanup_result_store_housekeeping=lambda valid_result_ids: cleanup_result_store_housekeeping(
            valid_result_ids=valid_result_ids
        ),
        error_logger=lambda message: print(message, file=sys.stderr, flush=True),
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
    return result_output.capture_generated_result(
        output_file,
        render_mode=render_mode,
        prompt=prompt,
        checkpoint=checkpoint,
        use_input_image=use_input_image,
        use_inpainting=use_inpainting,
        extra_metadata=extra_metadata,
        results_dir_access_state=results_dir_access_state,
        resolve_internal_output_path=resolve_internal_output_path,
        is_accessible_output_file=is_accessible_output_file,
        inspect_result_image=inspect_result_image,
        result_root=result_root(),
        utc_now_iso=utc_now_iso,
        write_result_metadata=write_result_metadata,
        build_result_metadata_item=build_result_metadata_item,
        resolve_result_mode_name=lambda render_mode, use_input_image, use_inpainting: resolve_result_mode_name(
            render_mode,
            use_input_image=use_input_image,
            use_inpainting=use_inpainting,
        ),
        enforce_result_retention=enforce_result_retention,
    )


def read_result_item(metadata_path: Path) -> dict | None:
    return result_output.read_result_item(
        metadata_path,
        read_json_file_detail=read_json_file_detail,
        result_root=result_root(),
        build_result_metadata_item=build_result_metadata_item,
    )


def list_stored_results(*, limit: int = RESULTS_DEFAULT_LIMIT) -> list[dict]:
    return result_output.list_stored_results(
        limit=limit,
        result_root=result_root(),
        read_result_item=read_result_item,
    )


def resolve_result_download_item(result_id: str) -> tuple[dict | None, Path | None]:
    return result_output.resolve_result_download_item(
        result_id,
        result_root=result_root(),
        read_result_item=read_result_item,
        is_accessible_output_file=is_accessible_output_file,
    )


def sanitize_export_token(value: object, *, fallback: str, max_length: int) -> str:
    return result_output.sanitize_export_token(value, fallback=fallback, max_length=max_length)


def count_export_store_files() -> int:
    return result_output.count_export_store_files(
        export_root=export_root(),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
    )


def reserve_export_target_path(base_file_name: str) -> Path:
    return result_output.reserve_export_target_path(base_file_name, export_root=export_root())


def build_result_export_file_name(result_item: dict) -> str:
    return result_output.build_result_export_file_name(
        result_item,
        sanitize_export_token=lambda value, fallback, max_length: sanitize_export_token(
            value,
            fallback=fallback,
            max_length=max_length,
        ),
        valid_upload_extensions=VALID_UPLOAD_EXTENSIONS,
    )


def build_results_storage_summary(*, app_results_count: int, cleanup_report: dict | None = None) -> dict:
    return result_output.build_results_storage_summary(
        app_results_count=app_results_count,
        cleanup_report=cleanup_report,
        retention_limit=get_result_retention_limit(),
        default_retention_limit=RESULT_RETENTION_DEFAULT,
        results_dir=repo_relative_path(result_root()),
        exports_dir=repo_relative_path(export_root()),
        exports_dir_access_state=exports_dir_access_state,
        count_export_store_files=count_export_store_files,
    )


def create_result_export(result_id: str) -> dict:
    return result_output.create_result_export(
        result_id,
        results_dir_access_state=results_dir_access_state,
        exports_dir_access_state=exports_dir_access_state,
        resolve_result_download_item=resolve_result_download_item,
        reserve_export_target_path=reserve_export_target_path,
        build_result_export_file_name=build_result_export_file_name,
        write_result_metadata=write_result_metadata,
        export_url_builder=export_path_to_web_path,
        utc_now_iso=utc_now_iso,
    )


def delete_stored_result(result_id: str) -> dict:
    return result_output.delete_stored_result(
        result_id,
        is_managed_result_id=is_managed_result_id,
        results_dir_access_state=results_dir_access_state,
        resolve_result_download_item=resolve_result_download_item,
        result_root=result_root(),
        list_result_store_records=list_result_store_records,
    )


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


def checkpoint_token(value: str | None) -> str:
    return str(value or "").strip().lower()


def resolve_general_generate_tuning(
    *,
    checkpoint: str | None,
    use_inpainting: bool = False,
    use_edit_image: bool = False,
    extra_negative_prompt: str | None = None,
    cfg_override: float | None = None,
    steps_override: int | None = None,
    inpaint_negative_suffix: str | None = None,
) -> tuple[float, int, str]:
    token = checkpoint_token(checkpoint)
    if token in ANIME_MOTIF_TUNING_CHECKPOINTS:
        cfg = ANIME_MOTIF_TUNING_CFG
        steps = ANIME_MOTIF_TUNING_STEPS
        negative_prompt = f"{DEFAULT_NEGATIVE_PROMPT}, {ANIME_MOTIF_TUNING_NEGATIVE_SUFFIX}"
    else:
        cfg = DEFAULT_CFG
        steps = DEFAULT_STEPS
        negative_prompt = DEFAULT_NEGATIVE_PROMPT

    if use_edit_image:
        steps = min(steps, EDIT_STEPS)

    if use_inpainting:
        if token in ANIME_MOTIF_TUNING_CHECKPOINTS:
            cfg = ANIME_INPAINT_CFG
            steps = ANIME_INPAINT_STEPS
        else:
            cfg = PHOTO_INPAINT_CFG
            steps = PHOTO_INPAINT_STEPS
        if isinstance(cfg_override, (int, float)):
            cfg = float(cfg_override)
        if isinstance(steps_override, int) and steps_override > 0:
            steps = steps_override
        effective_inpaint_negative_suffix = inpaint_negative_suffix.strip() if isinstance(inpaint_negative_suffix, str) and inpaint_negative_suffix.strip() else INPAINT_LOCALITY_NEGATIVE_SUFFIX
        negative_prompt = f"{negative_prompt}, {effective_inpaint_negative_suffix}"
    elif use_edit_image:
        negative_prompt = f"{negative_prompt}, {EDIT_IMAGE_PRESERVATION_NEGATIVE_SUFFIX}"

    if isinstance(extra_negative_prompt, str) and extra_negative_prompt.strip():
        negative_prompt = f"{negative_prompt}, {extra_negative_prompt.strip()}"

    return (
        cfg,
        steps,
        negative_prompt,
    )


def resolve_render_prompt(
    prompt: str,
    *,
    use_inpainting: bool = False,
    use_edit_image: bool = False,
    inpaint_prompt_suffix: str | None = None,
) -> str:
    normalized_prompt = str(prompt or "").strip()
    if use_inpainting:
        effective_suffix = inpaint_prompt_suffix.strip() if isinstance(inpaint_prompt_suffix, str) and inpaint_prompt_suffix.strip() else INPAINT_LOCAL_EDIT_PROMPT_SUFFIX
        return f"{normalized_prompt}, {effective_suffix}"
    if use_edit_image:
        return f"{normalized_prompt}, {EDIT_IMAGE_PRESERVATION_PROMPT_SUFFIX}"
    if not use_inpainting:
        return normalized_prompt
    return normalized_prompt


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
    return result_output.finalize_generate_result(
        result,
        request_id,
        prompt=prompt,
        checkpoint=checkpoint,
        use_input_image=use_input_image,
        use_inpainting=use_inpainting,
        extra_metadata=extra_metadata,
        capture_generated_result=capture_generated_result,
        build_generate_response=build_generate_response,
        build_error_response=build_error_response,
    )


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
        return app_status.build_system_state_payload(
            runner_payload=runner_payload,
            runner_status=runner_status,
            runner_error=runner_state_error,
            comfyui_reachable=comfyui_reachable,
            comfyui_error=comfyui_error,
            output_dir_accessible=output_dir_accessible,
            output_dir_error=output_dir_error,
            input_dir_accessible=input_dir_accessible,
            input_dir_error=input_dir_error,
            reference_dir_accessible=reference_dir_accessible,
            reference_dir_error=reference_dir_error,
            mask_dir_accessible=mask_dir_accessible,
            mask_dir_error=mask_dir_error,
            results_dir_accessible=results_dir_accessible,
            results_dir_error=results_dir_error,
            input_image=current_input_image_state(),
            reference_image=current_reference_image_state(),
            mask_image=current_mask_image_state(),
            inventory=inventory,
            text_service_state=text_service_state,
            render_state=self.render_state(),
        )


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
        if parsed.path == TEXT_CHAT_SLOTS_PATH:
            self.handle_text_chat_slots()
            return
        text_chat_slot_request = resolve_text_chat_slot_request_path(parsed.path)
        if text_chat_slot_request is not None and text_chat_slot_request[1] is None:
            self.handle_text_chat_slot_detail(text_chat_slot_request[0])
            return
        if parsed.path == IDENTITY_REFERENCE_READINESS_PATH:
            readiness_state = build_identity_runtime_state()
            self.send_json(
                identity_status.resolve_identity_readiness_http_status(
                    readiness_state,
                    status_code_resolver=resolve_identity_reference_status_code,
                ),
                readiness_state,
            )
            return
        if parsed.path == IDENTITY_RESEARCH_READINESS_PATH:
            provider_values = parse_qs(parsed.query).get("provider", [])
            provider = provider_values[0] if provider_values else None
            readiness_state = build_identity_research_runtime_state(provider=provider)
            if provider is None:
                self.send_json(HTTPStatus.OK, readiness_state)
                return
            self.send_json(
                identity_status.resolve_identity_readiness_http_status(
                    readiness_state,
                    status_code_resolver=resolve_identity_reference_status_code,
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
                multi_reference_status.resolve_multi_reference_readiness_http_status(
                    readiness_state,
                    status_code_resolver=resolve_identity_multi_reference_status_code,
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
                identity_status.resolve_identity_readiness_http_status(
                    readiness_state,
                    status_code_resolver=resolve_identity_transfer_generate_status_code,
                ),
                readiness_state,
            )
            return
        if parsed.path == IDENTITY_TRANSFER_MASK_HYBRID_READINESS_PATH:
            readiness_state = build_identity_transfer_mask_hybrid_runtime_state()
            self.send_json(
                identity_status.resolve_identity_readiness_http_status(
                    readiness_state,
                    status_code_resolver=resolve_identity_transfer_generate_status_code,
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
        if parsed.path.startswith(EXPORT_FILE_ROUTE_PREFIX):
            self.serve_export(parsed.path)
            return
        if parsed.path.startswith("/output/"):
            self.serve_output(parsed.path)
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == RESULT_DELETE_PATH:
            self.handle_result_delete()
            return
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
        if parsed.path == TEXT_CHAT_CREATE_PATH:
            self.handle_text_chat_create()
            return
        text_chat_slot_request = resolve_text_chat_slot_request_path(parsed.path)
        if text_chat_slot_request is not None:
            slot_index, action = text_chat_slot_request
            action = chat_requests.normalize_text_chat_slot_action(action)
            if action == "activate":
                self.handle_text_chat_activate(slot_index)
                return
            if action == "rename":
                self.handle_text_chat_rename(slot_index)
                return
            if action == "clear":
                self.handle_text_chat_clear(slot_index)
                return
            if action == "replace":
                self.handle_text_chat_replace(slot_index)
                return
            if action == "profile":
                self.handle_text_chat_profile(slot_index)
                return
            if action == "message":
                self.handle_text_chat_message(slot_index)
                return
        if parsed.path == TEXT_SERVICE_PROMPT_TEST_PATH:
            self.handle_text_service_prompt_test()
            return
        if parsed.path == RESULT_EXPORT_PATH:
            self.handle_result_export()
            return
        if parsed.path == IDENTITY_TRANSFER_GENERATE_PATH:
            self.handle_identity_transfer_generate()
            return
        if parsed.path == IDENTITY_TRANSFER_MASK_HYBRID_GENERATE_PATH:
            self.handle_identity_transfer_mask_hybrid_generate()
            return
        if parsed.path == IDENTITY_MULTI_REFERENCE_GENERATE_PATH:
            self.handle_identity_multi_reference_generate()
            return
        if parsed.path == IDENTITY_REFERENCE_GENERATE_PATH:
            self.handle_identity_reference_generate()
            return
        if parsed.path == IDENTITY_RESEARCH_GENERATE_PATH:
            self.handle_identity_research_generate()
            return
        if parsed.path != "/generate":
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return

        request_id = self.server.next_request_id()
        prepared, prepare_error = general_generate_flow.prepare_general_generate_request(
            self.read_json_body(),
            normalize_negative_prompt=normalize_optional_negative_prompt,
            parse_boolean_flag=lambda value: parse_boolean_flag(value, default=False),
            normalize_denoise_strength_value=normalize_denoise_strength_value,
            resolve_generation_request=resolve_generation_request,
            resolve_requested_input_image=resolve_requested_input_image,
            resolve_requested_mask_image=resolve_requested_mask_image,
            resolve_inpainting_tuning=resolve_inpainting_tuning,
        )
        if prepare_error is not None or prepared is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=None,
                    request_id=request_id,
                    failure=prepare_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="invalid_json",
                )
            )
            return

        mode = str(prepared["mode"])
        checkpoint = prepared["checkpoint"] if isinstance(prepared.get("checkpoint"), str) else None
        use_input_image = prepared["use_input_image"] is True
        use_inpainting = prepared["use_inpainting"] is True
        use_edit_image = prepared["use_edit_image"] is True
        denoise_strength = float(prepared["denoise_strength"])
        input_image_path = prepared.get("input_image_path")
        mask_image_path = prepared.get("mask_image_path")
        negative_prompt = prepared.get("negative_prompt") if isinstance(prepared.get("negative_prompt"), str) else None
        render_request = general_generate_flow.build_general_render_request(
            prepared,
            resolve_general_generate_tuning=resolve_general_generate_tuning,
            resolve_render_prompt=resolve_render_prompt,
            inpaint_locality_negative_suffix=INPAINT_LOCALITY_NEGATIVE_SUFFIX,
        )

        system_state = self.server.collect_system_state()
        system_error = general_generate_flow.build_general_generate_system_failure(system_state)
        if system_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=None,
                    request_id=request_id,
                    failure=system_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="comfyui_unreachable",
                )
            )
            return

        busy_response = generate_endpoint_flow.try_begin_generate_render(
            request_id=request_id,
            try_begin_render=self.server.try_begin_render,
            busy_response_builder=build_busy_response,
        )
        if busy_response is not None:
            self.send_json(*busy_response)
            return

        response_status, response_payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: run_render(
                prompt=str(render_request["render_prompt"]),
                mode=mode,
                workflow=str(prepared["workflow"]),
                checkpoint=checkpoint,
                negative_prompt=render_request["negative_prompt_value"] if isinstance(render_request.get("negative_prompt_value"), str) else None,
                steps=int(render_request["steps_value"]),
                cfg=float(render_request["cfg_value"]),
                use_input_image=use_input_image,
                input_image_path=input_image_path,
                use_inpainting=use_inpainting,
                mask_image_path=mask_image_path,
                denoise_strength=denoise_strength,
                grow_mask_by_override=render_request.get("grow_mask_by_override"),
                wait=True,
                wait_timeout=EDIT_WAIT_TIMEOUT_SECONDS if use_edit_image else 180,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            ),
            finalize_callable=lambda result: finalize_generate_result(
                result,
                request_id,
                prompt=str(render_request["prompt_text"]),
                checkpoint=checkpoint,
                use_input_image=use_input_image,
                use_inpainting=use_inpainting,
                extra_metadata={
                    "negative_prompt": negative_prompt,
                },
            ),
            server_error_callable=lambda: (
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_error_response(
                mode=mode,
                error_type="api_error",
                blocker="server_error",
                request_id=request_id,
                ),
            ),
            finish_render=self.server.finish_render,
        )

        self.send_json(response_status, response_payload)

    def handle_identity_reference_generate(self) -> None:
        request_id = self.server.next_request_id()
        prepared, prepare_error = identity_generate_flow.prepare_identity_reference_request(
            self.read_json_body(),
            resolve_reference_image=resolve_requested_reference_image,
        )
        if prepare_error is not None or prepared is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_REFERENCE_MODE,
                    request_id=request_id,
                    failure=prepare_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="invalid_json",
                )
            )
            return
        prompt = prepared["prompt"]
        checkpoint = prepared["checkpoint"]
        reference_image_path = prepared["reference_image_path"]

        system_state = self.server.collect_system_state()
        system_error = identity_generate_flow.build_system_preflight_failure(system_state)
        if system_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_REFERENCE_MODE,
                    request_id=request_id,
                    failure=system_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="comfyui_unreachable",
                )
            )
            return

        busy_response = generate_endpoint_flow.try_begin_generate_render(
            request_id=request_id,
            try_begin_render=self.server.try_begin_render,
            busy_response_builder=build_busy_response,
        )
        if busy_response is not None:
            self.send_json(*busy_response)
            return

        response_status, response_payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: run_identity_reference(
                prompt=prompt.strip(),
                reference_image_path=reference_image_path,
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            ),
            finalize_callable=lambda result: identity_generate_results.finalize_identity_generate_outcome(
                result,
                request_id=request_id,
                mode=IDENTITY_REFERENCE_MODE,
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                default_failed_blocker="identity_reference_failed",
                status_code_resolver=resolve_identity_reference_status_code,
                finalize_result=finalize_generate_result,
                error_response_builder=build_error_response,
            ),
            server_error_callable=lambda: identity_generate_results.build_identity_generate_server_error(
                mode=IDENTITY_REFERENCE_MODE,
                request_id=request_id,
                error_response_builder=build_error_response,
            ),
            finish_render=self.server.finish_render,
        )

        self.send_json(response_status, response_payload)

    def handle_identity_research_generate(self) -> None:
        request_id = self.server.next_request_id()
        prepared, prepare_error = identity_generate_flow.prepare_identity_research_request(
            self.read_json_body(),
            resolve_reference_image=resolve_requested_reference_image,
            normalize_negative_prompt=normalize_optional_negative_prompt,
            default_provider=IDENTITY_RESEARCH_DEFAULT_PROVIDER,
        )
        if prepare_error is not None or prepared is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_RESEARCH_MODE,
                    request_id=request_id,
                    failure=prepare_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="invalid_json",
                )
            )
            return
        prompt = prepared["prompt"]
        negative_prompt = prepared["negative_prompt"]
        provider = prepared["provider"]
        checkpoint = prepared["checkpoint"]
        reference_image_payload = prepared["reference_image_payload"]
        reference_image_path = prepared["reference_image_path"]

        runtime_state = build_identity_research_runtime_state(provider=provider)
        runtime_error = identity_generate_flow.build_runtime_preflight_failure(
            runtime_state,
            unavailable_blocker="identity_research_unavailable",
            status_code_resolver=resolve_identity_reference_status_code,
        )
        if runtime_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_RESEARCH_MODE,
                    request_id=request_id,
                    failure=runtime_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="identity_research_unavailable",
                )
            )
            return

        system_state = self.server.collect_system_state()
        system_error = identity_generate_flow.build_system_preflight_failure(system_state)
        if system_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_RESEARCH_MODE,
                    request_id=request_id,
                    failure=system_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="comfyui_unreachable",
                )
            )
            return

        busy_response = generate_endpoint_flow.try_begin_generate_render(
            request_id=request_id,
            try_begin_render=self.server.try_begin_render,
            busy_response_builder=build_busy_response,
        )
        if busy_response is not None:
            self.send_json(*busy_response)
            return

        response_status, response_payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: run_identity_research(
                prompt=prompt.strip(),
                negative_prompt=negative_prompt or "",
                reference_image_path=reference_image_path,
                provider=provider,
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            ),
            finalize_callable=lambda result: identity_generate_results.finalize_identity_generate_outcome(
                result,
                request_id=request_id,
                mode=IDENTITY_RESEARCH_MODE,
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                default_failed_blocker="identity_research_failed",
                status_code_resolver=resolve_identity_reference_status_code,
                finalize_result=finalize_generate_result,
                error_response_builder=build_error_response,
                extra_metadata={
                    "negative_prompt": negative_prompt,
                    "provider": provider,
                    "identity_research_provider": provider,
                    "identity_research_workflow": str(result.get("workflow_name") or "").strip() or None,
                    "identity_research_reference_image_id": str(reference_image_payload.get("image_id") or "").strip() or None,
                    "identity_research_reference_file_name": (
                        str(reference_image_payload.get("stored_name") or "").strip()
                        or str(reference_image_payload.get("original_name") or "").strip()
                        or None
                    ),
                    "reference_count": 1,
                    "reference_image_ids": [reference_image_payload["image_id"]] if isinstance(reference_image_payload.get("image_id"), str) and reference_image_payload.get("image_id") else [],
                    "store_scope": "app_results",
                    "cleanup_policy": "retention_limit",
                    "experimental": True,
                },
            ),
            server_error_callable=lambda: identity_generate_results.build_identity_generate_server_error(
                mode=IDENTITY_RESEARCH_MODE,
                request_id=request_id,
                error_response_builder=build_error_response,
            ),
            finish_render=self.server.finish_render,
        )

        self.send_json(response_status, response_payload)

    def handle_identity_transfer_generate(self) -> None:
        request_id = self.server.next_request_id()
        prepared, prepare_error = identity_generate_flow.prepare_identity_reference_request(
            self.read_json_body(),
            resolve_reference_image=lambda value: ({}, None),
        )
        if prepare_error is not None or prepared is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_TRANSFER_MODE,
                    request_id=request_id,
                    failure=prepare_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="invalid_json",
                )
            )
            return
        prompt = prepared["prompt"]
        checkpoint = prepared["checkpoint"]

        runtime_state = build_identity_transfer_runtime_state()
        runtime_error = identity_generate_flow.build_runtime_preflight_failure(
            runtime_state,
            unavailable_blocker="identity_transfer_unavailable",
            status_code_resolver=resolve_identity_transfer_generate_status_code,
        )
        if runtime_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_TRANSFER_MODE,
                    request_id=request_id,
                    failure=runtime_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="identity_transfer_unavailable",
                )
            )
            return

        system_state = self.server.collect_system_state()
        system_error = identity_generate_flow.build_system_preflight_failure(system_state)
        if system_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_TRANSFER_MODE,
                    request_id=request_id,
                    failure=system_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="comfyui_unreachable",
                )
            )
            return

        busy_response = generate_endpoint_flow.try_begin_generate_render(
            request_id=request_id,
            try_begin_render=self.server.try_begin_render,
            busy_response_builder=build_busy_response,
        )
        if busy_response is not None:
            self.send_json(*busy_response)
            return

        response_status, response_payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: run_identity_transfer(
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            ),
            finalize_callable=lambda result: identity_generate_results.finalize_identity_generate_outcome(
                result,
                request_id=request_id,
                mode=IDENTITY_TRANSFER_MODE,
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                default_failed_blocker="identity_transfer_failed",
                status_code_resolver=resolve_identity_transfer_generate_status_code,
                finalize_result=finalize_generate_result,
                error_response_builder=build_error_response,
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
            ),
            server_error_callable=lambda: identity_generate_results.build_identity_generate_server_error(
                mode=IDENTITY_TRANSFER_MODE,
                request_id=request_id,
                error_response_builder=build_error_response,
            ),
            finish_render=self.server.finish_render,
        )

        self.send_json(response_status, response_payload)

    def handle_identity_transfer_mask_hybrid_generate(self) -> None:
        request_id = self.server.next_request_id()
        prepared, prepare_error = identity_generate_flow.prepare_identity_reference_request(
            self.read_json_body(),
            resolve_reference_image=lambda value: ({}, None),
        )
        if prepare_error is not None or prepared is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_TRANSFER_MASK_HYBRID_MODE,
                    request_id=request_id,
                    failure=prepare_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="invalid_json",
                )
            )
            return
        prompt = prepared["prompt"]
        checkpoint = prepared["checkpoint"]

        runtime_state = build_identity_transfer_mask_hybrid_runtime_state()
        runtime_error = identity_generate_flow.build_runtime_preflight_failure(
            runtime_state,
            unavailable_blocker="identity_transfer_unavailable",
            status_code_resolver=resolve_identity_transfer_generate_status_code,
        )
        if runtime_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_TRANSFER_MASK_HYBRID_MODE,
                    request_id=request_id,
                    failure=runtime_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="identity_transfer_unavailable",
                )
            )
            return

        system_state = self.server.collect_system_state()
        system_error = identity_generate_flow.build_system_preflight_failure(system_state)
        if system_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_TRANSFER_MASK_HYBRID_MODE,
                    request_id=request_id,
                    failure=system_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="comfyui_unreachable",
                )
            )
            return

        busy_response = generate_endpoint_flow.try_begin_generate_render(
            request_id=request_id,
            try_begin_render=self.server.try_begin_render,
            busy_response_builder=build_busy_response,
        )
        if busy_response is not None:
            self.send_json(*busy_response)
            return

        response_status, response_payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: run_identity_transfer_mask_hybrid(
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            ),
            finalize_callable=lambda result: identity_generate_results.finalize_identity_generate_outcome(
                result,
                request_id=request_id,
                mode=IDENTITY_TRANSFER_MASK_HYBRID_MODE,
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                default_failed_blocker="identity_transfer_failed",
                status_code_resolver=resolve_identity_transfer_generate_status_code,
                finalize_result=finalize_generate_result,
                error_response_builder=build_error_response,
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
            ),
            server_error_callable=lambda: identity_generate_results.build_identity_generate_server_error(
                mode=IDENTITY_TRANSFER_MASK_HYBRID_MODE,
                request_id=request_id,
                error_response_builder=build_error_response,
            ),
            finish_render=self.server.finish_render,
        )

        self.send_json(response_status, response_payload)

    def handle_identity_multi_reference_generate(self) -> None:
        request_id = self.server.next_request_id()
        payload_dict, payload_error = identity_generate_flow.coerce_identity_generate_payload(self.read_json_body())
        if payload_error is not None or payload_dict is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    request_id=request_id,
                    failure=payload_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="invalid_json",
                )
            )
            return
        prepared, prepare_error = identity_generate_flow.normalize_identity_prompt_and_checkpoint(payload_dict)
        if prepare_error is not None or prepared is None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    request_id=request_id,
                    failure=prepare_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.BAD_REQUEST,
                    fallback_error_type="invalid_request",
                    fallback_blocker="empty_prompt",
                )
            )
            return
        prompt = prepared["prompt"]
        checkpoint = prepared["checkpoint"]

        adapter_state = build_multi_reference_adapter_state()
        runtime_state = build_identity_multi_reference_runtime_state(adapter_state=adapter_state)
        runtime_error = identity_generate_flow.build_runtime_preflight_failure(
            runtime_state,
            unavailable_blocker="identity_multi_reference_unavailable",
            status_code_resolver=resolve_identity_multi_reference_status_code,
        )
        if runtime_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    request_id=request_id,
                    failure=runtime_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="identity_multi_reference_unavailable",
                )
            )
            return

        system_state = self.server.collect_system_state()
        system_error = identity_generate_flow.build_system_preflight_failure(system_state)
        if system_error is not None:
            self.send_json(
                *generate_endpoint_flow.build_generate_endpoint_error(
                    mode=IDENTITY_MULTI_REFERENCE_MODE,
                    request_id=request_id,
                    failure=system_error,
                    error_response_builder=build_error_response,
                    fallback_http_status=HTTPStatus.SERVICE_UNAVAILABLE,
                    fallback_error_type="api_error",
                    fallback_blocker="comfyui_unreachable",
                )
            )
            return

        busy_response = generate_endpoint_flow.try_begin_generate_render(
            request_id=request_id,
            try_begin_render=self.server.try_begin_render,
            busy_response_builder=build_busy_response,
        )
        if busy_response is not None:
            self.send_json(*busy_response)
            return

        response_status, response_payload = generate_endpoint_flow.execute_generate_endpoint(
            render_callable=lambda: run_identity_multi_reference(
                prompt=prompt.strip(),
                adapter_state=identity_generate_flow.resolve_multi_reference_adapter_state(
                    runtime_state,
                    fallback_adapter_state=adapter_state,
                ),
                checkpoint=checkpoint,
                wait=True,
                output_dir=comfy_output_dir(),
                logger=None,
                error_logger=None,
            ),
            finalize_callable=lambda result: identity_generate_results.finalize_identity_generate_outcome(
                result,
                request_id=request_id,
                mode=IDENTITY_MULTI_REFERENCE_MODE,
                prompt=prompt.strip(),
                checkpoint=checkpoint,
                default_failed_blocker="identity_multi_reference_failed",
                status_code_resolver=resolve_identity_multi_reference_status_code,
                finalize_result=finalize_generate_result,
                error_response_builder=build_error_response,
                extra_metadata={
                    "reference_count": int(result.get("reference_count") or 0),
                    "reference_slots": result.get("reference_slots") if isinstance(result.get("reference_slots"), list) else [],
                    "reference_image_ids": result.get("reference_image_ids") if isinstance(result.get("reference_image_ids"), list) else [],
                    "multi_reference_strategy": str(result.get("multi_reference_strategy") or "").strip() or None,
                },
            ),
            server_error_callable=lambda: identity_generate_results.build_identity_generate_server_error(
                mode=IDENTITY_MULTI_REFERENCE_MODE,
                request_id=request_id,
                error_response_builder=build_error_response,
            ),
            finish_render=self.server.finish_render,
        )

        self.send_json(response_status, response_payload)

    def handle_text_chat_slots(self) -> None:
        try:
            payload = build_text_chat_overview_payload()
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, payload)

    def handle_text_chat_slot_detail(self, slot_index: int) -> None:
        try:
            slot = get_text_chat_slot(slot_index)
            profile_state = build_text_model_profiles_state()
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(
            HTTPStatus.OK,
            chat_responses.build_text_chat_slot_detail_response(
                slot=slot,
                profile_state=profile_state,
            ),
        )

    def handle_text_chat_create(self) -> None:
        payload, payload_error = chat_requests.coerce_optional_text_chat_payload(self.read_json_body())
        if payload_error is not None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=payload_error,
                    message="Chat request payload is invalid.",
                ),
            )
            return
        title, title_error = chat_requests.normalize_create_text_chat_title(
            payload.get("title"),
            title_normalizer=normalize_text_chat_title,
        )
        if title_error == "invalid_text_chat_title":
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=title_error,
                    message="Chat title must be a string.",
                ),
            )
            return
        if title_error == "empty_text_chat_title":
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=title_error,
                    message="Chat title must not be empty.",
                ),
            )
            return
        try:
            created = create_text_chat_in_first_empty_slot(title=title)
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        if created is None:
            self.send_json(
                HTTPStatus.CONFLICT,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker="text_chat_slots_full",
                    message="All five text chat slots are already occupied.",
                ),
            )
            return
        self.send_json(HTTPStatus.OK, build_text_chat_overview_payload())

    def handle_text_chat_activate(self, slot_index: int) -> None:
        try:
            set_active_text_chat_slot_index(slot_index)
            slot = get_text_chat_slot(slot_index)
            switch_notice = None
            if slot["occupied"] is True:
                profile_id = slot.get("model_profile") if isinstance(slot.get("model_profile"), str) else resolve_default_text_model_profile_id()
                switch_result = ensure_text_model_profile_active(profile_id)
                if switch_result.get("ok") is not True:
                    switch_notice = {
                        "blocker": switch_result.get("blocker"),
                        "message": switch_result.get("message"),
                    }
            payload = build_text_chat_overview_payload()
            if switch_notice is not None:
                payload["model_switch_notice"] = switch_notice
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, payload)

    def handle_text_chat_rename(self, slot_index: int) -> None:
        payload, payload_error = chat_requests.coerce_required_text_chat_payload(self.read_json_body())
        if payload_error is not None or payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=payload_error or "invalid_json",
                    message="Rename request payload is invalid.",
                ),
            )
            return
        title, title_error = chat_requests.normalize_required_text_chat_title(
            payload.get("title"),
            title_normalizer=normalize_text_chat_title,
        )
        if title_error is not None or title is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=title_error or "invalid_text_chat_title",
                    message="A non-empty chat title is required.",
                ),
            )
            return
        try:
            current_slot = get_text_chat_slot(slot_index)
            if current_slot["occupied"] is not True:
                self.send_json(
                    HTTPStatus.CONFLICT,
                    build_text_chat_error_response(
                        error_type="invalid_request",
                        blocker="text_chat_slot_empty",
                        message="The selected chat slot is empty.",
                    ),
                )
                return
            update_text_chat_slot_metadata(slot_index, title=title, updated_at=utc_now_iso())
            result_payload = build_text_chat_overview_payload()
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, result_payload)

    def handle_text_chat_clear(self, slot_index: int) -> None:
        try:
            clear_text_chat_slot(slot_index)
            if get_active_text_chat_slot_index() == slot_index:
                set_active_text_chat_slot_index(slot_index)
            payload = build_text_chat_overview_payload()
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, payload)

    def handle_text_chat_replace(self, slot_index: int) -> None:
        payload, payload_error = chat_requests.coerce_optional_text_chat_payload(self.read_json_body())
        if payload_error is not None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=payload_error,
                    message="Replace request payload is invalid.",
                ),
            )
            return
        title, title_error = chat_requests.normalize_optional_text_chat_title(
            payload.get("title"),
            title_normalizer=normalize_text_chat_title,
        )
        if title_error == "invalid_text_chat_title":
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=title_error,
                    message="Chat title must be a string.",
                ),
            )
            return
        try:
            create_text_chat_in_slot(slot_index, title=title)
            payload_out = build_text_chat_overview_payload()
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, payload_out)

    def handle_text_chat_profile(self, slot_index: int) -> None:
        payload, payload_error = chat_requests.coerce_required_text_chat_payload(self.read_json_body())
        if payload_error is not None or payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=payload_error or "invalid_json",
                    message="Profile request payload is invalid.",
                ),
            )
            return

        profile_id, profile_error = normalize_text_model_profile(payload.get("model_profile"))
        if profile_error is not None or profile_id is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=profile_error or "invalid_model_profile",
                    message="Text model profile must be standard, strong_writing or multilingual.",
                ),
            )
            return

        try:
            slot = get_text_chat_slot(slot_index)
            if slot["occupied"] is not True:
                self.send_json(
                    HTTPStatus.CONFLICT,
                    build_text_chat_error_response(
                        error_type="invalid_request",
                        blocker="text_chat_slot_empty",
                        message="Der gewaehlte Chat-Slot ist leer.",
                    ),
                )
                return
            switch_notice = None
            update_text_chat_slot_metadata(
                slot_index,
                model_profile=profile_id,
                model=slot.get("model"),
                updated_at=utc_now_iso(),
            )
            if get_active_text_chat_slot_index() == slot_index:
                switch_result = ensure_text_model_profile_active(profile_id)
                refreshed_profile = switch_result.get("profile") if isinstance(switch_result.get("profile"), dict) else get_text_model_profile(profile_id)
                update_text_chat_slot_metadata(
                    slot_index,
                    model=refreshed_profile.get("actual_model_name") or resolve_text_chat_model_label() or slot.get("model"),
                    updated_at=utc_now_iso(),
                )
                if switch_result.get("ok") is not True:
                    switch_notice = {
                        "blocker": switch_result.get("blocker"),
                        "message": switch_result.get("message"),
                    }
            payload_out = build_text_chat_overview_payload()
            if switch_notice is not None:
                payload_out["model_switch_notice"] = switch_notice
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, payload_out)

    def handle_text_chat_message(self, slot_index: int) -> None:
        payload, payload_error = chat_requests.coerce_required_text_chat_payload(self.read_json_body())
        if payload_error is not None or payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=payload_error or "invalid_json",
                    message="Message request payload is invalid.",
                ),
            )
            return

        prompt, prompt_error = normalize_text_service_prompt(payload.get("prompt"))
        if prompt_error is not None or prompt is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=prompt_error or "empty_prompt",
                    message="A valid prompt is required.",
                ),
            )
            return

        mode, mode_error = normalize_text_work_mode(payload.get("mode"))
        if mode_error is not None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=mode_error,
                    message="Text mode must be writing, rewrite or image_prompt.",
                ),
            )
            return

        title, title_error = chat_requests.normalize_optional_text_chat_title(
            payload.get("title"),
            title_normalizer=normalize_text_chat_title,
        )
        if title_error == "invalid_text_chat_title":
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_chat_error_response(
                    error_type="invalid_request",
                    blocker=title_error,
                    message="Chat title must be a string.",
                ),
            )
            return
        try:
            slot = get_text_chat_slot(slot_index)
            if slot["occupied"] is not True:
                slot = create_text_chat_in_slot(slot_index, title=title)
            else:
                set_active_text_chat_slot_index(slot_index)

            prepared_request = chat_text_service.prepare_text_chat_service_request(
                slot=slot,
                prompt=prompt,
                requested_title=title,
                default_title=build_default_text_chat_title(slot_index),
                default_profile_id=resolve_default_text_model_profile_id(),
                recent_messages_limit=TEXT_CHAT_CONTEXT_RECENT_MESSAGES,
                infer_language=infer_text_chat_language_from_text,
                compose_prompt=build_text_chat_prompt,
            )
            current_title = prepared_request["current_title"]
            inferred_language = prepared_request["inferred_language"]
            profile_id = prepared_request["profile_id"]
            switch_result = ensure_text_model_profile_active(profile_id)
            profile = switch_result.get("profile") if isinstance(switch_result.get("profile"), dict) else get_text_model_profile(profile_id)
            if switch_result.get("ok") is not True:
                self.send_json(
                    HTTPStatus.CONFLICT,
                    build_text_chat_error_response(
                        error_type="invalid_request",
                        blocker=str(switch_result.get("blocker") or "text_model_profile_unavailable"),
                        message=str(switch_result.get("message") or "Das fuer diesen Chat gespeicherte Modellprofil ist aktuell nicht lauffaehig."),
                    ),
                )
                return
            current_model = profile.get("actual_model_name") or resolve_text_chat_model_label()
            service_result = chat_text_service.execute_text_chat_service_request(
                request_callable=request_text_service_prompt,
                retry_predicate=should_retry_text_service_prompt_after_switch,
                sleep_callable=time.sleep,
                switch_result=switch_result,
                composed_prompt=prepared_request["composed_prompt"],
                mode=mode,
                summary=prepared_request["summary"],
                recent_messages=prepared_request["recent_messages"],
            )
            normalized_service_result = chat_text_service.normalize_text_chat_service_result(
                response_payload=service_result["response_payload"],
                response_error=service_result["response_error"],
                response_status=service_result["response_status"],
                service_name=service_result["service_name"],
                model_status=service_result["model_status"],
            )
            if normalized_service_result["ok"] is not True:
                self.send_json(
                    normalized_service_result["http_status"],
                    build_text_chat_error_response(
                        error_type="api_error",
                        blocker=str(normalized_service_result["blocker"]),
                        message=str(normalized_service_result["message"]),
                    ),
                )
                return

            normalized_response_text = str(normalized_service_result["response_text"])
            append_text_chat_message(slot_index, role="user", content=prompt)
            append_text_chat_message(slot_index, role="assistant", content=normalized_response_text)
            updated_slot = get_text_chat_slot(slot_index)
            post_response_state = chat_text_service.build_text_chat_post_response_state(
                updated_slot=updated_slot,
                slot_index=slot_index,
                current_title=current_title,
                prompt=prompt,
                default_title=build_default_text_chat_title(slot_index),
                excerpt_text=excerpt_text,
                build_summary=build_text_chat_summary,
            )
            update_text_chat_slot_metadata(
                slot_index,
                title=post_response_state["current_title"],
                summary=post_response_state["updated_summary"] or "",
                language=inferred_language,
                model_profile=profile_id,
                model=(
                    current_model
                    or normalized_service_result.get("service_name")
                    or normalized_service_result.get("model_status")
                ),
                updated_at=utc_now_iso(),
            )
            payload_out = build_text_chat_overview_payload()
            payload_out["last_response_text"] = normalized_response_text
            payload_out["active_mode"] = mode or TEXT_WORK_MODE_WRITING
            payload_out["active_model_profile"] = profile_id
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                build_text_chat_error_response(
                    error_type="api_error",
                    blocker="text_chat_storage_error",
                    message=str(exc),
                ),
            )
            return
        self.send_json(HTTPStatus.OK, payload_out)

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

        mode, mode_error = normalize_text_work_mode(payload.get("mode"))
        if mode_error is not None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=False,
                    stub=True,
                    response_text=None,
                    error=mode_error,
                    error_message="mode must be writing, rewrite or image_prompt.",
                    service_name=None,
                    model_status=None,
                ),
            )
            return

        profile_id, profile_error = normalize_text_model_profile(payload.get("model_profile"))
        if profile_error is not None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=False,
                    stub=True,
                    response_text=None,
                    error=profile_error,
                    error_message="model_profile must be standard, strong_writing or multilingual.",
                    service_name=None,
                    model_status=None,
                ),
            )
            return

        selected_profile_id = profile_id or resolve_default_text_model_profile_id()
        switch_result = ensure_text_model_profile_active(selected_profile_id)
        selected_profile = switch_result.get("profile") if isinstance(switch_result.get("profile"), dict) else get_text_model_profile(selected_profile_id)
        if switch_result.get("ok") is not True:
            self.send_json(
                HTTPStatus.CONFLICT,
                {
                    **build_text_service_prompt_test_response(
                        ok=False,
                        text_service_reachable=True,
                        stub=False,
                        response_text=None,
                        error=str(switch_result.get("blocker") or "text_model_profile_unavailable"),
                        error_message=str(switch_result.get("message") or "Dieses Modellprofil ist aktuell nicht lauffaehig."),
                        service_name=None,
                        model_status=None,
                    ),
                    "model_profile": selected_profile_id,
                    "model_profile_label": selected_profile.get("label"),
                },
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
            payload={"prompt": prompt, "mode": mode},
        )
        if should_retry_text_service_prompt_after_switch(
            switch_result=switch_result,
            response_error=response_error,
            response_status=response_status,
        ):
            time.sleep(5.0)
            response_payload, response_error, response_status = post_json_detail(
                f"http://{config['host']}:{config['port']}/prompt",
                timeout=TEXT_SERVICE_PROMPT_TIMEOUT,
                payload={"prompt": prompt, "mode": mode},
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
                {
                    **build_text_service_prompt_test_response(
                        ok=True,
                        text_service_reachable=True,
                        stub=upstream_stub,
                        response_text=response_payload.get("response_text") if isinstance(response_payload.get("response_text"), str) else None,
                        error=None,
                        error_message=None,
                        service_name=upstream_service,
                        model_status=upstream_model_status,
                    ),
                    "model_profile": selected_profile_id,
                    "model_profile_label": selected_profile.get("label"),
                },
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
            {
                **build_text_service_prompt_test_response(
                    ok=False,
                    text_service_reachable=True,
                    stub=upstream_stub,
                    response_text=None,
                    error=error_value,
                    error_message=error_message,
                    service_name=upstream_service,
                    model_status=upstream_model_status,
                ),
                "model_profile": selected_profile_id,
                "model_profile_label": selected_profile.get("label"),
            },
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

    def serve_export(self, request_path: str) -> None:
        target = resolve_export_request_path(request_path)
        if target is None:
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        if not is_accessible_output_file(target):
            self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})
            return
        self.serve_file(target, read_error_status=HTTPStatus.NOT_FOUND)

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

        cleanup_report = enforce_result_retention()
        store_records = list_result_store_records()
        items = list_stored_results(limit=limit)
        storage_summary = build_results_storage_summary(
            app_results_count=len(store_records),
            cleanup_report=cleanup_report,
        )
        self.send_json(
            HTTPStatus.OK,
            result_output.build_results_list_response(
                count=len(items),
                total_count=len(store_records),
                limit=limit,
                items=items,
                storage=storage_summary,
            ),
        )

    def handle_result_export(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_results_error_response(
                    error_type="invalid_request",
                    blocker="invalid_json",
                    message="Export request payload is invalid.",
                ),
            )
            return

        result_id = str(payload.get("result_id") or "").strip()
        if not result_id:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_results_error_response(
                    error_type="invalid_request",
                    blocker="missing_result_id",
                    message="result_id is required.",
                ),
            )
            return

        try:
            export_payload = create_result_export(result_id)
        except ResultStoreError as exc:
            self.send_json(
                exc.status_code,
                build_results_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return

        self.send_json(
            HTTPStatus.OK,
            result_output.build_result_export_success_response(export_payload),
        )

    def handle_result_delete(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_results_error_response(
                    error_type="invalid_request",
                    blocker="invalid_json",
                    message="Delete request payload is invalid.",
                ),
            )
            return

        result_id = str(payload.get("result_id") or "").strip()
        if not result_id:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                build_results_error_response(
                    error_type="invalid_request",
                    blocker="missing_result_id",
                    message="result_id is required.",
                ),
            )
            return

        try:
            delete_payload = delete_stored_result(result_id)
        except ResultStoreError as exc:
            self.send_json(
                exc.status_code,
                build_results_error_response(
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return

        self.send_json(
            HTTPStatus.OK,
            result_output.build_result_delete_success_response(delete_payload),
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

        try:
            image_input_validation.validate_multipart_content_type(content_type)
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

        try:
            image_input_validation.validate_multipart_content_type(content_type)
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

        try:
            image_input_validation.validate_multipart_content_type(content_type)
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

        try:
            image_input_validation.validate_multipart_content_type(content_type)
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
