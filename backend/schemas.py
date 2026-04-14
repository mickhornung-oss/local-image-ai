from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


WorkMode = Literal["python_task", "rewrite", "explain"]


class AssistRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=6000)
    mode: WorkMode = "python_task"
    current_file_path: str | None = None
    current_file_text: str | None = None
    selected_text: str | None = None
    workspace_root: str | None = None
    traceback_text: str | None = None


class AssistResponse(BaseModel):
    status: Literal["ok"]
    mode: WorkMode
    answer: str
    duration_seconds: float
    model_path: str
    model_loaded: bool
    context_summary: dict


class ErrorResponse(BaseModel):
    status: Literal["error"]
    blocker: str
    message: str

