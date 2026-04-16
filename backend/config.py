from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "app_config.json"
LOCAL_CONFIG_PATH = CONFIG_DIR / "app_config.local.json"


@dataclass(slots=True)
class AppConfig:
    host: str
    port: int
    model_path: str
    model_alias: str
    n_ctx: int
    max_tokens: int
    temperature: float
    top_p: float
    file_context_max_chars: int
    selection_max_chars: int
    traceback_max_chars: int


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_model_path(config_payload: dict) -> str:
    env_override = os.environ.get("CODE_KI_MODEL_PATH", "").strip()
    if env_override:
        return env_override

    configured = str(config_payload.get("model_path") or "").strip()
    if configured and Path(configured).exists():
        return configured

    candidate_paths = [
        REPO_ROOT / "models" / "qwen2.5-7b-instruct-q4_k_m.gguf",
        Path(
            r"C:\Users\mickh\Desktop\Py Mick\vendor\text_models\qwen2.5-7b-instruct-q4_k_m.gguf"
        ),
    ]
    for candidate in candidate_paths:
        if candidate.exists() and candidate.is_file():
            return str(candidate.resolve())
    return configured


def load_config() -> AppConfig:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = _read_json(CONFIG_PATH)
    payload.update(_read_json(LOCAL_CONFIG_PATH))

    return AppConfig(
        host=str(payload.get("host") or "127.0.0.1"),
        port=int(payload.get("port") or 8787),
        model_path=_resolve_model_path(payload),
        model_alias=str(payload.get("model_alias") or "local-python-assistant"),
        n_ctx=int(payload.get("n_ctx") or 4096),
        max_tokens=int(payload.get("max_tokens") or 700),
        temperature=float(payload.get("temperature") or 0.2),
        top_p=float(payload.get("top_p") or 0.95),
        file_context_max_chars=int(payload.get("file_context_max_chars") or 24000),
        selection_max_chars=int(payload.get("selection_max_chars") or 12000),
        traceback_max_chars=int(payload.get("traceback_max_chars") or 8000),
    )
