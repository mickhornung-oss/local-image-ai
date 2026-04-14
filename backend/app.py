from __future__ import annotations

from fastapi import FastAPI, HTTPException

from backend.config import load_config
from backend.model_runtime import ModelRuntime
from backend.schemas import AssistRequest
from backend.service import run_assist


CONFIG = load_config()
RUNTIME = ModelRuntime(CONFIG)
app = FastAPI(title="Code KI", version="1.0.0")


@app.get("/health")
def health() -> dict:
    payload = RUNTIME.health_payload()
    payload["service"] = "code-ki-backend"
    payload["host"] = CONFIG.host
    payload["port"] = CONFIG.port
    return payload


@app.post("/assist")
def assist(request: AssistRequest) -> dict:
    try:
        return run_assist(request, config=CONFIG, runtime=RUNTIME)
    except RuntimeError as exc:
        blocker = str(exc)
        status_code = 503 if blocker == "model_path_missing" else 500
        raise HTTPException(
            status_code=status_code,
            detail={
                "status": "error",
                "blocker": blocker,
                "message": "Lokale Code-KI konnte den Auftrag nicht verarbeiten.",
            },
        ) from exc
