from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as email_policy_default
from http import HTTPStatus
from pathlib import Path
import tempfile


DEFAULT_SPEECH_LANGUAGE = "de"
DEFAULT_OPENAI_WHISPER_MODEL = "base"
DEFAULT_FASTER_WHISPER_MODEL = "small"
DEFAULT_FASTER_WHISPER_DEVICE = "cpu"
DEFAULT_FASTER_WHISPER_COMPUTE_TYPE = "int8"
MAX_AUDIO_BYTES = 16 * 1024 * 1024
SUPPORTED_AUDIO_EXTENSIONS = frozenset({".webm", ".wav", ".ogg", ".m4a", ".mp3", ".flac"})


class SpeechTranscriptionError(Exception):
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


@dataclass(frozen=True)
class SpeechRuntimeState:
    available: bool
    backend: str | None
    message: str


_MODEL_CACHE_LOCK = threading.Lock()
_MODEL_CACHE: dict[str, object] = {}


def sanitize_file_name(filename: str | None) -> str:
    normalized = Path(str(filename or "speech-input.webm")).name.replace("\x00", "").strip()
    return normalized or "speech-input.webm"


def _normalize_language(value: object) -> str:
    if not isinstance(value, str):
        return DEFAULT_SPEECH_LANGUAGE
    normalized = value.strip().lower()
    if not normalized:
        return DEFAULT_SPEECH_LANGUAGE
    if len(normalized) > 12:
        return DEFAULT_SPEECH_LANGUAGE
    if any(ch for ch in normalized if not (ch.isalpha() or ch in {"-", "_"})):
        return DEFAULT_SPEECH_LANGUAGE
    return normalized


def parse_multipart_audio(content_type: str, body: bytes) -> tuple[str, bytes, str]:
    message = BytesParser(policy=email_policy_default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    )
    if not message.is_multipart():
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_multipart",
            message="Upload request must be multipart/form-data.",
        )

    file_parts: list[tuple[str, bytes]] = []
    language = DEFAULT_SPEECH_LANGUAGE
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = str(part.get_param("name", header="content-disposition") or "").strip().lower()
        filename = part.get_filename()
        if not filename:
            if field_name == "language":
                language = _normalize_language(part.get_content())
            continue
        payload = part.get_payload(decode=True) or b""
        file_parts.append((filename, payload))

    if not file_parts:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="missing_audio",
            message="No audio file was provided.",
        )
    if len(file_parts) > 1:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="multiple_files_not_supported",
            message="Exactly one audio file is supported.",
        )

    original_name, payload = file_parts[0]
    return sanitize_file_name(original_name), payload, language


def _validate_audio_payload(file_name: str, payload: bytes) -> tuple[str, str]:
    if not payload:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_upload",
            blocker="empty_audio",
            message="Audio payload is empty.",
        )
    if len(payload) > MAX_AUDIO_BYTES:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            error_type="invalid_upload",
            blocker="audio_too_large",
            message="Audio payload exceeds the maximum size.",
        )
    extension = Path(file_name).suffix.lower()
    if extension not in SUPPORTED_AUDIO_EXTENSIONS:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            error_type="invalid_upload",
            blocker="unsupported_audio_format",
            message="Supported formats: .webm .wav .ogg .m4a .mp3 .flac",
        )
    return file_name, extension


def _detect_backend() -> SpeechRuntimeState:
    try:
        import faster_whisper  # noqa: F401

        return SpeechRuntimeState(
            available=True,
            backend="faster_whisper",
            message="Lokale Transkription bereit.",
        )
    except Exception:
        pass

    try:
        import whisper  # noqa: F401

        return SpeechRuntimeState(
            available=True,
            backend="openai_whisper",
            message="Lokale Transkription bereit.",
        )
    except Exception:
        pass

    return SpeechRuntimeState(
        available=False,
        backend=None,
        message="Lokale Transkription fehlt. Installiere `faster-whisper` oder `openai-whisper` in der Projekt-venv.",
    )


def build_runtime_state_payload() -> dict:
    state = _detect_backend()
    return {
        "status": "ok",
        "ok": state.available,
        "available": state.available,
        "backend": state.backend,
        "message": state.message,
        "default_language": DEFAULT_SPEECH_LANGUAGE,
        "max_audio_bytes": MAX_AUDIO_BYTES,
        "supported_extensions": sorted(SUPPORTED_AUDIO_EXTENSIONS),
    }


def _load_cached_model(cache_key: str, loader):
    with _MODEL_CACHE_LOCK:
        cached = _MODEL_CACHE.get(cache_key)
        if cached is not None:
            return cached
        model = loader()
        _MODEL_CACHE[cache_key] = model
        return model


def _transcribe_with_faster_whisper(audio_path: Path, language: str) -> str:
    from faster_whisper import WhisperModel

    model_name = str(os.environ.get("STORYFORGE_STT_MODEL") or DEFAULT_FASTER_WHISPER_MODEL).strip()
    device = str(os.environ.get("STORYFORGE_STT_DEVICE") or DEFAULT_FASTER_WHISPER_DEVICE).strip()
    compute_type = str(os.environ.get("STORYFORGE_STT_COMPUTE_TYPE") or DEFAULT_FASTER_WHISPER_COMPUTE_TYPE).strip()
    cache_key = f"faster_whisper::{model_name}::{device}::{compute_type}"
    model = _load_cached_model(
        cache_key,
        lambda: WhisperModel(model_name, device=device, compute_type=compute_type),
    )
    segments, _ = model.transcribe(str(audio_path), language=language or None, vad_filter=True)
    return " ".join(str(segment.text or "").strip() for segment in segments if str(segment.text or "").strip()).strip()


def _transcribe_with_openai_whisper(audio_path: Path, language: str) -> str:
    import whisper

    model_name = str(os.environ.get("STORYFORGE_STT_MODEL") or DEFAULT_OPENAI_WHISPER_MODEL).strip()
    cache_key = f"openai_whisper::{model_name}"
    model = _load_cached_model(cache_key, lambda: whisper.load_model(model_name))
    result = model.transcribe(str(audio_path), language=language or None, fp16=False)
    return str(result.get("text") or "").strip()


def transcribe_audio_payload(
    *,
    original_name: str,
    payload: bytes,
    language: str | None = None,
    temp_root: Path | None = None,
) -> dict:
    normalized_name, extension = _validate_audio_payload(sanitize_file_name(original_name), payload)
    normalized_language = _normalize_language(language)
    state = _detect_backend()
    if not state.available or not state.backend:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_type="speech_unavailable",
            blocker="speech_backend_unavailable",
            message=state.message,
        )

    working_root = Path(temp_root) if temp_root is not None else Path(tempfile.gettempdir())
    working_root.mkdir(parents=True, exist_ok=True)

    temp_file_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=extension,
            prefix="speech-",
            dir=str(working_root),
        ) as temp_file:
            temp_file.write(payload)
            temp_file_path = Path(temp_file.name)

        if state.backend == "faster_whisper":
            transcript = _transcribe_with_faster_whisper(temp_file_path, normalized_language)
        elif state.backend == "openai_whisper":
            transcript = _transcribe_with_openai_whisper(temp_file_path, normalized_language)
        else:
            transcript = ""

        if not transcript:
            raise SpeechTranscriptionError(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                error_type="speech_error",
                blocker="empty_transcript",
                message="Kein Text erkannt.",
            )

        return {
            "status": "ok",
            "ok": True,
            "text": transcript,
            "backend": state.backend,
            "language": normalized_language,
            "source_file_name": normalized_name,
        }
    except SpeechTranscriptionError:
        raise
    except Exception as exc:
        raise SpeechTranscriptionError(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_type="speech_error",
            blocker="speech_transcription_failed",
            message="Transkription fehlgeschlagen.",
        ) from exc
    finally:
        if temp_file_path is not None:
            try:
                temp_file_path.unlink(missing_ok=True)
            except OSError:
                pass
