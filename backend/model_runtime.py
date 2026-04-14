from __future__ import annotations

from pathlib import Path
from threading import Lock

from llama_cpp import Llama

from backend.config import AppConfig


class ModelRuntime:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._llm: Llama | None = None
        self._lock = Lock()

    @property
    def resolved_model_path(self) -> str:
        return str(Path(self._config.model_path).resolve()) if self._config.model_path else ""

    def health_payload(self) -> dict:
        model_path = self.resolved_model_path
        available = bool(model_path) and Path(model_path).exists()
        return {
            "status": "ok",
            "model_alias": self._config.model_alias,
            "model_path": model_path or None,
            "model_available": available,
            "model_loaded": self._llm is not None,
            "backend": "llama_cpp_python",
        }

    def _ensure_loaded(self) -> Llama:
        model_path = self.resolved_model_path
        if not model_path or not Path(model_path).exists():
            raise RuntimeError("model_path_missing")
        with self._lock:
            if self._llm is None:
                self._llm = Llama(
                    model_path=model_path,
                    n_ctx=self._config.n_ctx,
                    n_gpu_layers=0,
                    verbose=False,
                )
        return self._llm

    def complete(self, messages: list[dict]) -> str:
        llm = self._ensure_loaded()
        response = llm.create_chat_completion(
            messages=messages,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            max_tokens=self._config.max_tokens,
        )
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("invalid_model_response")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise RuntimeError("invalid_model_response")
        content = str(message.get("content") or "").strip()
        if not content:
            raise RuntimeError("empty_model_response")
        return content
