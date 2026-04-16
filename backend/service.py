from __future__ import annotations

import time

from backend.config import AppConfig
from backend.context_builder import build_user_prompt
from backend.model_runtime import ModelRuntime
from backend.prompting import build_messages
from backend.schemas import AssistRequest


def run_assist(
    request: AssistRequest, *, config: AppConfig, runtime: ModelRuntime
) -> dict:
    user_prompt, context_summary = build_user_prompt(request, config)
    messages = build_messages(request, user_prompt)
    started_at = time.perf_counter()
    answer = runtime.complete(messages)
    duration = round(time.perf_counter() - started_at, 3)
    return {
        "status": "ok",
        "mode": request.mode,
        "answer": answer,
        "duration_seconds": duration,
        "model_path": runtime.resolved_model_path,
        "model_loaded": True,
        "context_summary": {
            "current_file_path": context_summary["current_file_path"],
            "workspace_root": context_summary["workspace_root"],
            "has_file_context": context_summary["has_file_context"],
            "has_selection": context_summary["has_selection"],
            "has_traceback": context_summary["has_traceback"],
            "file_chars": context_summary["file_chars"],
            "selection_chars": context_summary["selection_chars"],
            "traceback_chars": context_summary["traceback_chars"],
        },
    }
