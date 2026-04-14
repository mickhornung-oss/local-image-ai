import argparse
import json
import re
import shutil
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

try:
    import text_prompting as tp
    from text_prompting import (
        DEFAULT_LONG_FORM_WORD_TARGET,
        MAX_LONG_FORM_WORD_TARGET,
        PROMPT_PROFILE_IMAGE,
        PROMPT_PROFILE_INFO,
        PROMPT_PROFILE_REWRITE,
        PROMPT_PROFILE_SHORT,
        PROMPT_PROFILE_WRITING,
        TEXT_WORK_MODE_IMAGE,
        TEXT_WORK_MODE_REWRITE,
        TEXT_WORK_MODE_WRITING,
    )
except ModuleNotFoundError:
    from python import text_prompting as tp
    from python.text_prompting import (
        DEFAULT_LONG_FORM_WORD_TARGET,
        MAX_LONG_FORM_WORD_TARGET,
        PROMPT_PROFILE_IMAGE,
        PROMPT_PROFILE_INFO,
        PROMPT_PROFILE_REWRITE,
        PROMPT_PROFILE_SHORT,
        PROMPT_PROFILE_WRITING,
        TEXT_WORK_MODE_IMAGE,
        TEXT_WORK_MODE_REWRITE,
        TEXT_WORK_MODE_WRITING,
    )


DEFAULT_SERVICE_NAME = "local-text-service"
DEFAULT_MODEL_STATUS = "not_configured"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
DEFAULT_RUNNER_TYPE = "llama_cpp_server"
DEFAULT_RUNNER_HOST = "127.0.0.1"
DEFAULT_RUNNER_PORT = 8092
DEFAULT_MODEL_FORMAT = "gguf"
DEFAULT_PROMPT_MODE = "echo_stub"
DEFAULT_RUNNER_PROMPT_MODE = "llama_cpp_server"
DEFAULT_RUNNER_BINARY_NAME = "llama-server.exe"
DEFAULT_RUNNER_BINARY_ALT_NAME = "llama-server"
DEFAULT_RESPONSE_PROFILE = "concise_help"
MAX_PROMPT_LENGTH = 2000
RUNNER_PROBE_TIMEOUT_SECONDS = 1.0
RUNNER_CONNECT_TIMEOUT_SECONDS = 0.25
RUNNER_PROMPT_TIMEOUT_SECONDS = 90.0
RUNNER_MAX_TOKENS = 220
RUNNER_TEMPERATURE = 0.1
RUNNER_TOP_P = 0.78
RUNNER_REPEAT_PENALTY = 1.18
RUNNER_STOP_SEQUENCES = ["\n\n\n", "\nUser:", "\nBenutzer:", "\nSystem:", "<|im_end|>"]
RUNNER_LONG_FORM_STOP_SEQUENCES = ["\nUser:", "\nBenutzer:", "\nSystem:", "<|im_end|>"]
RESPONSE_MAX_CHARACTERS = 320
IMAGE_PROMPT_MAX_CHARACTERS = 240
LONG_FORM_RESPONSE_MAX_CHARACTERS = 20000
MAX_VISIBLE_SENTENCES = 2
MIN_LONG_FORM_WORDS = 55
RUNNER_LONG_FORM_MIN_TOKENS = 220
RUNNER_LONG_FORM_MAX_TOKENS = 2800
RUNNER_CONTEXT_LIMIT_TOKENS = 4096
RUNNER_CONTINUATION_MAX_TOKENS = 480
CONTINUATION_CONTEXT_CHARACTERS = 1400
MAX_CONTINUATION_ATTEMPTS = 3
MAX_UNDERLENGTH_CONTINUATION_ATTEMPTS = 2
RUNNER_LONG_FORM_TIMEOUT_SECONDS = 600.0

VALID_TEXT_WORK_MODES = {
    TEXT_WORK_MODE_WRITING,
    TEXT_WORK_MODE_REWRITE,
    TEXT_WORK_MODE_IMAGE,
}


class TextServiceConfigError(Exception):
    pass


class TextServiceRequestError(Exception):
    def __init__(self, *, status_code: HTTPStatus, error_type: str, blocker: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.blocker = blocker
        self.message = message


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_config_path() -> Path:
    return repo_root() / "config" / "text_service.json"


def normalize_config(raw: object) -> dict:
    payload = raw if isinstance(raw, dict) else {}
    enabled = payload.get("enabled", True)
    host = str(payload.get("host", DEFAULT_HOST)).strip() or DEFAULT_HOST
    port = payload.get("port", DEFAULT_PORT)
    service_name = str(payload.get("service_name", DEFAULT_SERVICE_NAME)).strip() or DEFAULT_SERVICE_NAME
    model_status = str(payload.get("model_status", DEFAULT_MODEL_STATUS)).strip() or DEFAULT_MODEL_STATUS
    runner_type = str(payload.get("runner_type", DEFAULT_RUNNER_TYPE)).strip() or DEFAULT_RUNNER_TYPE
    runner_host = str(payload.get("runner_host", DEFAULT_RUNNER_HOST)).strip() or DEFAULT_RUNNER_HOST
    runner_port = payload.get("runner_port", DEFAULT_RUNNER_PORT)
    runner_binary_path_raw = payload.get("runner_binary_path", "")
    model_format = str(payload.get("model_format", DEFAULT_MODEL_FORMAT)).strip() or DEFAULT_MODEL_FORMAT
    model_path_raw = payload.get("model_path", "")

    if not isinstance(enabled, bool):
        raise TextServiceConfigError("enabled must be boolean")
    if host != DEFAULT_HOST:
        raise TextServiceConfigError("host must be 127.0.0.1")
    if not isinstance(port, int):
        raise TextServiceConfigError("port must be integer")
    if port < 1 or port > 65535:
        raise TextServiceConfigError("port out of range")
    if runner_type != DEFAULT_RUNNER_TYPE:
        raise TextServiceConfigError("runner_type must be llama_cpp_server")
    if runner_host != DEFAULT_RUNNER_HOST:
        raise TextServiceConfigError("runner_host must be 127.0.0.1")
    if not isinstance(runner_port, int):
        raise TextServiceConfigError("runner_port must be integer")
    if runner_port < 1 or runner_port > 65535:
        raise TextServiceConfigError("runner_port out of range")
    if runner_binary_path_raw is None:
        runner_binary_path = ""
    elif isinstance(runner_binary_path_raw, str):
        runner_binary_path = runner_binary_path_raw.strip()
    else:
        raise TextServiceConfigError("runner_binary_path must be string")
    if model_format != DEFAULT_MODEL_FORMAT:
        raise TextServiceConfigError("model_format must be gguf")
    if model_path_raw is None:
        model_path = ""
    elif isinstance(model_path_raw, str):
        model_path = model_path_raw.strip()
    else:
        raise TextServiceConfigError("model_path must be string")

    return {
        "enabled": enabled,
        "host": host,
        "port": port,
        "service_name": service_name,
        "model_status": model_status,
        "runner_type": runner_type,
        "runner_host": runner_host,
        "runner_port": runner_port,
        "runner_binary_path": runner_binary_path,
        "model_format": model_format,
        "model_path": model_path,
    }


def load_config(path: Path | None = None) -> dict:
    resolved_path = (path or default_config_path()).resolve()
    if not resolved_path.exists():
        raise TextServiceConfigError(f"config missing: {resolved_path}")

    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise TextServiceConfigError(f"config unreadable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TextServiceConfigError(f"config invalid json: {exc}") from exc

    config = normalize_config(payload)
    config["config_path"] = str(resolved_path)
    return config


def resolve_local_path(value: str) -> Path | None:
    normalized = value.strip()
    if not normalized:
        return None

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = repo_root() / candidate
    return candidate.resolve()


def resolve_model_path(model_path: str) -> Path | None:
    return resolve_local_path(model_path)


def resolve_runner_binary_path(runner_binary_path: str) -> Path | None:
    return resolve_local_path(runner_binary_path)


def discover_runner_binary(config: dict) -> tuple[Path | None, bool]:
    configured_binary = resolve_runner_binary_path(config.get("runner_binary_path", ""))
    if configured_binary is not None:
        return configured_binary, configured_binary.is_file()

    for candidate_name in (DEFAULT_RUNNER_BINARY_NAME, DEFAULT_RUNNER_BINARY_ALT_NAME):
        discovered = shutil.which(candidate_name)
        if discovered:
            path = Path(discovered).resolve()
            return path, path.is_file()

    return None, False


def is_runner_port_usable(host: str, port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind((host, port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def probe_runner_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=RUNNER_CONNECT_TIMEOUT_SECONDS):
            pass
    except OSError:
        return False

    endpoints = ("/v1/models", "/health")
    for endpoint in endpoints:
        request = urllib_request.Request(f"http://{host}:{port}{endpoint}", method="GET")
        try:
            with urllib_request.urlopen(request, timeout=RUNNER_PROBE_TIMEOUT_SECONDS) as response:
                if response.status == HTTPStatus.OK:
                    return True
        except urllib_error.HTTPError as exc:
            if exc.code == HTTPStatus.OK:
                return True
        except (urllib_error.URLError, TimeoutError, OSError):
            continue
    return False


def probe_runner_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=RUNNER_CONNECT_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False


def extract_runner_response_text(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
            text = first_choice.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    content = payload.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    text = payload.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    return None


def estimate_message_token_usage(messages: list[dict[str, str]]) -> int:
    estimated_tokens = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        content = str(message.get("content") or "")
        role = str(message.get("role") or "")
        estimated_tokens += max(12, len(content) // 2)
        estimated_tokens += max(2, len(role) // 4)
        estimated_tokens += 16
    return estimated_tokens + 48


def extract_requested_word_bounds(prompt: str) -> tuple[int, int] | None:
    return tp.extract_requested_word_bounds(prompt)
    range_match = re.search(
        r"\b(?:zwischen|between)?\s*(\d{2,4})\s*(?:-|–|—|bis|to|and|und)\s*(\d{2,4})\s*(?:woerter|woertern|worte|worten|w\u00f6rter|w\u00f6rtern|words)\b",
        prompt,
        flags=re.IGNORECASE,
    )
    if range_match:
        try:
            lower_target = int(range_match.group(1))
            upper_target = int(range_match.group(2))
        except ValueError:
            lower_target = 0
            upper_target = 0
        if lower_target > 0 and upper_target > 0:
            if lower_target > upper_target:
                lower_target, upper_target = upper_target, lower_target
            if upper_target < 40:
                return None
            lower_target = max(40, lower_target)
            upper_target = max(lower_target, min(MAX_LONG_FORM_WORD_TARGET, upper_target))
            return lower_target, upper_target

    match = re.search(
        r"\b(?:ca\.?|circa|etwa|ungefaehr|ungef\u00e4hr)?\s*(\d{2,4})\s*(?:woerter|woertern|worte|worten|w\u00f6rter|w\u00f6rtern|words)\b",
        prompt,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    try:
        target = int(match.group(1))
    except ValueError:
        return None

    if target < 40:
        return None
    target = min(MAX_LONG_FORM_WORD_TARGET, target)
    return build_word_target_window(target)


def extract_requested_word_target(prompt: str) -> int | None:
    return tp.extract_requested_word_target(prompt)
    bounds = extract_requested_word_bounds(prompt)
    if bounds is None:
        return None
    lower_bound, upper_bound = bounds
    return int(round((lower_bound + upper_bound) / 2))
def infer_requested_format(prompt: str) -> str | None:
    return tp.infer_requested_format(prompt)
    normalized = prompt.lower()
    if "brief" in normalized or "liebesbrief" in normalized:
        return "Brief"
    if "geburtstagskarte" in normalized or "karte" in normalized:
        return "Kartentext"
    if "mail" in normalized or "email" in normalized:
        return "E-Mail"
    if "gedicht" in normalized:
        return "Gedicht"
    if "abschnitt" in normalized:
        return "Abschnitt"
    if "text" in normalized:
        return "Text"
    return None


def extract_style_hints(prompt: str) -> list[str]:
    return tp.extract_style_hints(prompt)
    normalized = prompt.lower()
    style_markers = (
        ("liebevoll", "liebevoll"),
        ("herzlich", "herzlich"),
        ("freundlich", "freundlich"),
        ("warm", "warm"),
        ("klassisch", "klassisch"),
        ("goethe", "klassisch und leicht poetisch"),
        ("poetisch", "poetisch"),
        ("romantisch", "romantisch"),
        ("sachlich", "sachlich"),
        ("nuechtern", "nuechtern"),
        ("formell", "formell"),
        ("locker", "locker"),
    )
    hints: list[str] = []
    for marker, hint in style_markers:
        if marker in normalized and hint not in hints:
            hints.append(hint)
    return hints


def infer_prompt_language(prompt: str) -> str | None:
    return tp.infer_prompt_language(prompt)
    normalized = f" {prompt.lower()} "
    explicit_english_markers = (" in english ", " auf englisch ", " english ", " englisch ")
    explicit_spanish_markers = (" in spanish ", " auf spanisch ", " spanish ", " spanisch ", " espanol ", " español ")
    explicit_french_markers = (" in french ", " auf franzoesisch ", " french ", " francais ", " français ", " franzoesisch ")
    if any(marker in normalized for marker in explicit_english_markers):
        return "en"
    if any(marker in normalized for marker in explicit_spanish_markers):
        return "es"
    if any(marker in normalized for marker in explicit_french_markers):
        return "fr"
    english_markers = (" the ", " and ", " with ", " into ", " rewrite ", " draft ", " words ")
    spanish_markers = (" el ", " la ", " los ", " las ", " con ", " para ", " reescribe ", " palabras ")
    french_markers = (" le ", " la ", " les ", " avec ", " pour ", " réécris ", " mots ")
    german_markers = (" der ", " die ", " das ", " und ", " mit ", " fuer ", " woerter ", " überarbeite ")

    marker_sets = [
        ("en", english_markers),
        ("es", spanish_markers),
        ("fr", french_markers),
        ("de", german_markers),
    ]
    scores = []
    for language_code, markers in marker_sets:
        score = sum(marker in normalized for marker in markers)
        scores.append((language_code, score))
    best_language, best_score = max(scores, key=lambda entry: entry[1])
    if best_score < 2:
        return None
    return best_language


def build_explicit_language_instruction(language_code: str | None) -> str | None:
    return tp.build_explicit_language_instruction(language_code)
    if language_code == "en":
        return "Antworte vollstaendig auf Englisch. Verwende kein Deutsch."
    if language_code == "es":
        return "Antworte vollstaendig auf Spanisch. Verwende kein Deutsch."
    if language_code == "fr":
        return "Antworte vollstaendig auf Franzoesisch. Verwende kein Deutsch."
    if language_code == "de":
        return "Antworte vollstaendig auf Deutsch."
    return None


def is_translation_request(prompt: str) -> bool:
    normalized = f" {prompt.lower()} "
    markers = (
        " translate ",
        " translation ",
        " uebersetze ",
        " übersetze ",
        " ins englische ",
        " auf englisch ",
        " into english ",
        " in english ",
        " ins spanische ",
        " auf spanisch ",
        " into spanish ",
        " in spanish ",
        " ins franzoesische ",
        " auf franzoesisch ",
        " into french ",
        " in french ",
    )
    return any(marker in normalized for marker in markers)


def build_word_target_window(word_target: int) -> tuple[int, int]:
    return tp.build_word_target_window(word_target)
    tolerance = max(8, int(word_target * 0.1))
    minimum_words = max(40, word_target - tolerance)
    maximum_words = word_target + tolerance
    return minimum_words, maximum_words


def build_requested_format_instruction(requested_format: str | None) -> str | None:
    return tp.build_requested_format_instruction(requested_format)
    if requested_format == "Brief":
        return "Schreibe einen echten Brief mit Anrede, Hauptteil und Schlussformel in ganzen Saetzen."
    if requested_format == "Kartentext":
        return "Schreibe einen zusammenhaengenden Kartentext ohne Platzhalter wie [Name] und ohne Listen."
    if requested_format == "Gedicht":
        return "Schreibe ein kurzes zusammenhaengendes Gedicht ohne Erklaerung."
    if requested_format == "Abschnitt":
        return "Schreibe einen zusammenhaengenden Absatz."
    if requested_format == "Text":
        return "Schreibe einen zusammenhaengenden Text in ganzen Saetzen."
    return None


def build_word_target_instruction(
    word_target: int | None,
    *,
    retry: bool = False,
    word_bounds: tuple[int, int] | None = None,
) -> str:
    return tp.build_word_target_instruction(word_target, retry=retry, word_bounds=word_bounds)
    if word_target is None and word_bounds is None:
        return "Liefere einen kompakten, aber vollstaendigen Text."
    if word_bounds is None:
        if word_target is None:
            return "Liefere einen kompakten, aber vollstaendigen Text."
        minimum_words, maximum_words = build_word_target_window(word_target)
        target_text = f"ungefaehr {word_target} Woerter"
    else:
        minimum_words, maximum_words = word_bounds
        target_text = f"moeglichst zwischen {minimum_words} und {maximum_words} Woertern"
    if retry:
        return (
            f"Ziel: {target_text}. Schreibe mindestens {minimum_words} und hoechstens {maximum_words} Woerter. "
            "Halte die Wortspanne diesmal deutlich genauer ein und falle weder klar darunter noch deutlich darueber."
        )
    return (
        f"Ziel: {target_text}. "
        "Eine kleine Abweichung ist okay, aber bleibe moeglichst nah daran und vermeide klare Unter- oder Ueberschreitungen."
    )


def count_response_words(text: str) -> int:
    return tp.count_response_words(text)
    return len(re.findall(r"[A-Za-z0-9\u00c0-\u024f\u00df]+(?:['-][A-Za-z0-9\u00c0-\u024f\u00df]+)*", text))


def calculate_word_bounds_distance(word_bounds: tuple[int, int] | None, actual_words: int) -> int:
    return tp.calculate_word_bounds_distance(word_bounds, actual_words)
    if word_bounds is None:
        return 0
    minimum_words, maximum_words = word_bounds
    if actual_words < minimum_words:
        return minimum_words - actual_words
    if actual_words > maximum_words:
        return actual_words - maximum_words
    return 0


def should_prefer_retry_by_word_bounds(
    word_bounds: tuple[int, int] | None,
    *,
    first_words: int,
    retry_words: int,
) -> bool:
    return tp.should_prefer_retry_by_word_bounds(
        word_bounds,
        first_words=first_words,
        retry_words=retry_words,
    )
    if word_bounds is None:
        return retry_words >= first_words
    first_distance = calculate_word_bounds_distance(word_bounds, first_words)
    retry_distance = calculate_word_bounds_distance(word_bounds, retry_words)
    return retry_distance <= first_distance


def build_runner_request_settings(
    profile: str,
    prompt: str,
    *,
    retry: bool = False,
    previous_response: str | None = None,
) -> dict:
    word_target = extract_requested_word_target(prompt)
    word_bounds = extract_requested_word_bounds(prompt)
    max_tokens = RUNNER_MAX_TOKENS
    timeout_seconds = RUNNER_PROMPT_TIMEOUT_SECONDS

    if profile == PROMPT_PROFILE_REWRITE:
        if word_target is not None:
            target_words = word_target
            minimum_tokens = 320 if target_words <= 180 else 240
            _, maximum_words = word_bounds or build_word_target_window(target_words)
            multiplier = 1.7 if maximum_words <= 180 else 1.55
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(minimum_tokens, int(maximum_words * multiplier)))
            timeout_seconds = RUNNER_LONG_FORM_TIMEOUT_SECONDS
        elif len(prompt) > 700:
            max_tokens = 220
            timeout_seconds = 75.0
        else:
            max_tokens = 120
            timeout_seconds = 45.0
    elif profile == PROMPT_PROFILE_INFO:
        target_words = word_target or DEFAULT_LONG_FORM_WORD_TARGET
        if word_bounds is not None:
            _, maximum_words = word_bounds
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(RUNNER_LONG_FORM_MIN_TOKENS, int(maximum_words * 1.45)))
        else:
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(RUNNER_LONG_FORM_MIN_TOKENS, int(target_words * 1.8)))
        timeout_seconds = RUNNER_LONG_FORM_TIMEOUT_SECONDS if word_target else 45.0
    elif profile == PROMPT_PROFILE_WRITING:
        target_words = word_target or DEFAULT_LONG_FORM_WORD_TARGET
        if word_bounds is not None:
            _, maximum_words = word_bounds
            minimum_tokens = 320 if maximum_words <= 180 else RUNNER_LONG_FORM_MIN_TOKENS
            multiplier = 1.72 if maximum_words <= 180 else 1.52
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(minimum_tokens, int(maximum_words * multiplier)))
        else:
            minimum_tokens = 300 if word_target is not None and word_target <= 160 else RUNNER_LONG_FORM_MIN_TOKENS
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(minimum_tokens, int(target_words * 2.0)))
        timeout_seconds = RUNNER_LONG_FORM_TIMEOUT_SECONDS if word_target else 45.0

    if retry and profile == PROMPT_PROFILE_REWRITE:
        if word_target is not None or word_bounds is not None or len(prompt) > 700:
            previous_word_count = count_response_words(previous_response or "")
            previous_incomplete = has_incomplete_long_form_ending(previous_response or "")
            if word_bounds is not None and previous_word_count:
                minimum_words, maximum_words = word_bounds
                if previous_incomplete:
                    max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * 1.22))
                    timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 35.0)
                elif previous_word_count > maximum_words:
                    max_tokens = min(max_tokens, max(170, int(maximum_words * 1.35)))
                    timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 15.0)
                elif previous_word_count < minimum_words:
                    underlength_multiplier = 1.5 if maximum_words <= 180 else 1.24
                    if infer_prompt_language(prompt) in {"en", "es", "fr"}:
                        underlength_multiplier = max(underlength_multiplier, 1.28)
                    max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * underlength_multiplier))
                    timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 45.0)
            else:
                max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * 1.18))
                timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 45.0)
    elif retry and profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        previous_word_count = count_response_words(previous_response or "")
        word_bounds = extract_requested_word_bounds(prompt)
        if word_bounds is not None and previous_word_count:
            minimum_words, maximum_words = word_bounds
            if previous_word_count < minimum_words:
                underlength_multiplier = 1.42 if maximum_words <= 220 else 1.28
                max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * underlength_multiplier))
                timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 60.0)
        if has_incomplete_long_form_ending(previous_response or ""):
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * 1.24))
            timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 35.0)
        else:
            max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * 1.12))
            timeout_seconds = min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, timeout_seconds + 25.0)

    return {
        "max_tokens": int(max_tokens),
        "timeout_seconds": float(timeout_seconds),
        "stop_sequences": (
            RUNNER_LONG_FORM_STOP_SEQUENCES
            if profile in (PROMPT_PROFILE_REWRITE, PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING)
            else RUNNER_STOP_SEQUENCES
        ),
    }


def classify_prompt_profile(prompt: str) -> str:
    return tp.classify_prompt_profile(prompt)
    normalized = prompt.lower()
    word_target = extract_requested_word_target(prompt)

    image_keywords = (
        "bildprompt",
        "prompt fuer ein bild",
        "prompt fÃ¼r ein bild",
        "prompt fuer ein foto",
        "prompt fÃ¼r ein foto",
        "erstelle einen prompt",
        "schreibe einen prompt",
        "bild prompt",
        "prompthilfe",
        "prompt hilfe",
    )
    rewrite_keywords = (
        "umformulieren",
        "umschreiben",
        "schreibe um",
        "kuerzer um",
        "kÃ¼rzer um",
        "schreibe eleganter",
        "schreibe fluessiger",
        "schreibe flÃ¼ssiger",
        "verbessere diesen text",
        "formuliere den folgenden",
        "formuliere folgenden",
        "formuliere diesen text",
        "formuliere diesen satz",
    )
    writing_request_keywords = (
        "schreibe",
        "verfasse",
        "erstelle",
        "entwirf",
        "formuliere",
        "text",
        "abschnitt",
        "brief",
        "karte",
        "mail",
        "email",
        "nachricht",
    )
    creative_format_keywords = (
        "brief",
        "liebesbrief",
        "karte",
        "geburtstagskarte",
        "gedicht",
        "geschichte",
        "ansprache",
        "rede",
        "gruss",
        "grusskarte",
        "mail",
        "email",
        "nachricht",
    )
    creative_style_keywords = (
        "liebevoll",
        "herzlich",
        "freundlich",
        "warm",
        "klassisch",
        "poetisch",
        "romantisch",
        "goethe",
        "persoenlich",
        "persÃƒÂ¶nlich",
    )
    info_keywords = (
        "infotext",
        "sachtext",
        "fachtext",
        "erklaertext",
        "erklÃƒÂ¤rtext",
        "erklaere",
        "erklÃƒÂ¤re",
        "erlaeutere",
        "erlÃƒÂ¤utere",
        "erklaer",
        "erklÃƒÂ¤r",
        "sachlich",
        "informativ",
        "fakten",
        "wissenswert",
        "ueberblick",
        "ÃƒÂ¼berblick",
    )
    has_text_over_topic = re.search(r"\btext\s+(?:ueber|ÃƒÂ¼ber)\b", normalized) is not None

    if any(keyword in normalized for keyword in image_keywords):
        return PROMPT_PROFILE_IMAGE
    if any(keyword in normalized for keyword in rewrite_keywords):
        return PROMPT_PROFILE_REWRITE
    if any(keyword in normalized for keyword in creative_format_keywords):
        return PROMPT_PROFILE_WRITING
    if any(keyword in normalized for keyword in creative_style_keywords):
        return PROMPT_PROFILE_WRITING
    if any(keyword in normalized for keyword in info_keywords) and any(keyword in normalized for keyword in writing_request_keywords):
        return PROMPT_PROFILE_INFO
    if word_target is not None and has_text_over_topic and not any(keyword in normalized for keyword in creative_style_keywords):
        return PROMPT_PROFILE_INFO
    if any(keyword in normalized for keyword in writing_request_keywords) and word_target is not None:
        return PROMPT_PROFILE_WRITING
    if any(keyword in normalized for keyword in writing_request_keywords) and re.search(
        r"\b(text|abschnitt|brief|karte|mail|email|nachricht|gedicht)\b", normalized
    ):
        return PROMPT_PROFILE_WRITING
    return PROMPT_PROFILE_SHORT


def runtime_uses_multilingual_profile(runtime_state: dict | None) -> bool:
    return tp.runtime_uses_multilingual_profile(runtime_state)
    if not isinstance(runtime_state, dict):
        return False
    for key in ("resolved_model_path", "model_path"):
        value = runtime_state.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip().lower()
        if "gemma" in normalized and "12b" in normalized:
            return True
    return False


def extract_image_prompt_subject(prompt: str) -> str:
    return tp.extract_image_prompt_subject(prompt)
    subject = prompt.strip()
    subject = re.sub(
        r"^(bitte\s+)?(erstelle|schreibe|mach)\s+(mir\s+)?(einen|einen kurzen|einen kompakten)?\s*(bildprompt|prompt)\s+(fuer|fÃ¼r|zu)\s+",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    subject = re.sub(
        r"^(ein|eine)\s+(schoenes|schones|stimmungsvolles|einfaches)\s+bild\s+von\s+",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    subject = re.sub(r"^(ein|eine)\s+bild\s+von\s+", "", subject, flags=re.IGNORECASE)
    subject = re.sub(
        r"^(ich\s+brauche\s+)?(hilfe\s+bei\s+einem\s+bildprompt|einen\s+bildprompt|einen\s+prompt)\s+(fuer|fÃ¼r|zu)\s+",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    subject = subject.strip(" .:-")
    return subject or prompt.strip()


def build_runner_messages(
    prompt: str,
    *,
    retry: bool = False,
    previous_response: str | None = None,
    forced_mode: str | None = None,
    summary: str | None = None,
    recent_messages: list[dict[str, str]] | None = None,
    multilingual_runtime: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    if forced_mode == TEXT_WORK_MODE_WRITING:
        profile = PROMPT_PROFILE_WRITING
    elif forced_mode == TEXT_WORK_MODE_REWRITE:
        profile = PROMPT_PROFILE_REWRITE
    elif forced_mode == TEXT_WORK_MODE_IMAGE:
        profile = PROMPT_PROFILE_IMAGE
    else:
        profile = classify_prompt_profile(prompt)
    image_subject = extract_image_prompt_subject(prompt)
    word_target = extract_requested_word_target(prompt)
    word_bounds = extract_requested_word_bounds(prompt)
    tone_hints = extract_style_hints(prompt)
    requested_language = infer_prompt_language(prompt)
    translation_request = is_translation_request(prompt)
    requested_format = infer_requested_format(prompt)
    requested_format_instruction = build_requested_format_instruction(requested_format)
    summary_text = summary.strip() if isinstance(summary, str) and summary.strip() else None
    recent_message_lines: list[str] = []
    if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING, PROMPT_PROFILE_REWRITE):
        if word_target is not None and word_target >= 600:
            summary_text = None
            recent_messages = []
        elif word_target is not None and word_target >= 300:
            recent_messages = []
    if isinstance(recent_messages, list):
        for entry in recent_messages:
            if not isinstance(entry, dict):
                continue
            role_value = str(entry.get("role") or "").strip().lower()
            content_value = str(entry.get("content") or "").strip()
            if role_value not in {"user", "assistant"} or not content_value:
                continue
            role_label = "Nutzer" if role_value == "user" else "KI"
            recent_message_lines.append(f"{role_label}: {content_value}")
    context_block = ""
    if summary_text or recent_message_lines:
      context_lines = []
      if summary_text:
          context_lines.append(f"Chat-Zusammenfassung:\n{summary_text}")
      if recent_message_lines:
          context_lines.append("Letzte Chat-Nachrichten:\n" + "\n".join(recent_message_lines[-6:]))
      context_block = "\n\n" + "\n\n".join(context_lines)
    if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING, PROMPT_PROFILE_REWRITE):
        if multilingual_runtime:
            system_prompt = (
                "Du bist eine lokale mehrsprachige Schreib- und Ueberarbeitungs-KI. "
                "Antworte standardmaessig in derselben Sprache wie die Nutzereingabe. "
                "Wenn die Nutzereingabe auf Deutsch, Englisch, Spanisch oder Franzoesisch erfolgt, bleibe in dieser Sprache. "
                "Wechsle die Sprache nicht ohne ausdruecklichen Wunsch. "
                "Liefere vollstaendige, brauchbare Nutztexte statt knapper Kurzantworten. "
                "Erfuelle Format, Ton und grobe Laenge so gut wie moeglich. "
                "Keine Einleitung ueber deine Aufgabe. "
                "Keine Verweigerung, keine Meta-Hinweise, keine Entschuldigung. "
                "Kein Marketington, kein Abschweifen, keine erfundenen Details."
            )
        else:
            system_prompt = (
                "Du bist eine lokale Schreib- und Ueberarbeitungs-KI auf Deutsch. "
                "Antworte standardmaessig auf Deutsch. "
                "Liefere vollstaendige, brauchbare Nutztexte statt knapper Kurzantworten. "
                "Erfuelle Format, Ton und grobe Laenge so gut wie moeglich. "
                "Keine Einleitung ueber deine Aufgabe. "
                "Keine Verweigerung, keine Meta-Hinweise, keine Entschuldigung. "
                "Kein Marketington, kein Abschweifen, keine erfundenen Details."
            )
        if profile == PROMPT_PROFILE_WRITING:
            system_prompt += (
                " Im Schreibmodus hilfst du bei Szenen, Kapiteln, Ton, Stil und Fortsetzungen. "
                "Wenn ein Text noch zu kurz ist, fuehrst du ihn sinnvoll weiter statt ihn unnoetig zu verdichten. "
                "Erwachsene oder dunklere Stoffe werden nicht kuenstlich weichgespuelt."
            )
        elif profile == PROMPT_PROFILE_INFO:
            system_prompt += (
                " Im Infotextmodus schreibst du ruhig, klar und vollstaendig. "
                "Du bevorzugst zusammenhaengende Abschnitte statt knapper Stichpunkte."
            )
        else:
            system_prompt += (
                " Im Rewrite-Modus bewahrst du Inhalt und Substanz. "
                "Du kuerzt nicht unnoetig und schreibst keine blosse Kurzfassung."
            )
        if translation_request:
            system_prompt += (
                " Wenn der Auftrag eine Uebersetzung verlangt, zaehlt die ausdruecklich genannte Zielsprache. "
                "Gib nur den uebersetzten Zieltext aus und lasse keine Saetze in der Quellsprache stehen."
            )
    elif multilingual_runtime:
        system_prompt = (
            "Du bist eine lokale mehrsprachige Text-KI fuer kurze, saubere Einzelantworten. "
            "Antworte standardmaessig in derselben Sprache wie die Nutzereingabe. "
            "Wenn die Nutzereingabe auf Deutsch, Englisch, Spanisch oder Franzoesisch erfolgt, bleibe in dieser Sprache. "
            "Wechsle die Sprache nicht ohne ausdruecklichen Wunsch. "
            "Fuer Bildprompts lieferst du weiterhin kurze englische Prompt-Ausgabe. "
            "Antworte knapp, klar und ohne Wiederholungen. "
            "Keine Einleitung ueber deine Aufgabe. "
            "Kein Fuelltext, kein Marketington, kein Abschweifen. "
            "Wenn du etwas nicht sicher weisst, bleibe vorsichtig und erfinde keine Details. "
            "Keine Listen, ausser wenn der Nutzer sie ausdruecklich verlangt."
        )
    else:
        system_prompt = (
            "Du bist eine lokale Text-KI fuer kurze, saubere Einzelantworten. "
            "Antworte standardmaessig auf Deutsch. "
            "Verwende keine andere Sprache, ausser wenn du ausdruecklich einen Bildprompt liefern sollst. "
            "Antworte knapp, klar und ohne Wiederholungen. "
            "Keine Einleitung ueber deine Aufgabe. "
            "Kein Fuelltext, kein Marketington, kein Abschweifen. "
            "Wenn du etwas nicht sicher weisst, bleibe vorsichtig und erfinde keine Details. "
            "Keine Listen, ausser wenn der Nutzer sie ausdruecklich verlangt."
        )
    if retry:
        if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
            system_prompt += (
                " Wenn der erste Entwurf zu kurz ist, liefere im zweiten Anlauf mehr Nutztext "
                "und bleibe naeher am Wortziel."
            )
        else:
            system_prompt += " Wenn die Antwort unklar wird, antworte noch kuerzer, konkreter und strenger nach Vorgabe."

    if profile == PROMPT_PROFILE_IMAGE:
        if retry:
            user_prompt = (
                "Return exactly one short English image prompt. "
                "Only comma-separated visual keywords. "
                "Include subject, visual style, lighting, mood and key scene details. "
                "No German, no explanation, no full sentence, no list numbering. "
                "Use 10 to 14 short keyword groups. "
                "Between 18 and 28 words.\n\n"
                f"Scene or text to convert: {prompt}{context_block}"
            )
        else:
            user_prompt = (
                "Create exactly one short English image prompt. "
                "Use comma-separated visual keywords only. "
                "Include subject, style, lighting, mood and the most important scene details. "
                "No explanation, no full sentence, no German words. "
                "Use 10 to 14 short keyword groups. "
                "Between 18 and 30 words.\n\n"
                f"Scene or text to convert: {prompt}{context_block}"
            )
    elif profile == PROMPT_PROFILE_REWRITE:
        instructions = []
        instructions.append(
            "Ueberarbeite den folgenden Text klar, natuerlich und passend zum Auftrag. "
            "Verbessere Stil, Lesbarkeit, Struktur oder Ton, ohne den Kern unnoetig zu verlieren. "
            "Bewahre die Substanz des Ausgangstextes; schreibe keine blosse Kurzfassung."
        )
        if retry and previous_response and has_incomplete_long_form_ending(previous_response):
            instructions.append(
                "Der erste Entwurf brach am Ende unvollstaendig ab. Liefere jetzt eine vollstaendige, sauber abgeschlossene Ueberarbeitung."
            )
        if retry and word_bounds is not None and previous_response:
            previous_word_count = count_response_words(previous_response)
            minimum_words, maximum_words = word_bounds
            if previous_word_count > maximum_words:
                instructions.append(
                    f"Der erste Entwurf war zu lang. Straffe die Ueberarbeitung jetzt auf hoechstens {maximum_words} Woerter, ohne sie in eine Kurzfassung oder blosse Zusammenfassung zu verwandeln."
                )
            elif previous_word_count < minimum_words:
                instructions.append(
                    f"Der erste Entwurf war zu kurz. Erweitere die Ueberarbeitung jetzt auf mindestens {minimum_words} und hoechstens {maximum_words} Woerter."
                )
        if multilingual_runtime:
            instructions.append(build_explicit_language_instruction(requested_language) or "Bewahre die Sprache der Eingabe.")
        else:
            instructions.append("Antworte ausschliesslich auf Deutsch.")
        if translation_request:
            instructions.append("Wenn der Auftrag eine Uebersetzung verlangt, gib nur den uebersetzten Zieltext aus.")
            if requested_language is not None:
                instructions.append(build_explicit_language_instruction(requested_language) or "")
        if word_target is not None or word_bounds is not None:
            instructions.append(build_word_target_instruction(word_target, retry=retry, word_bounds=word_bounds))
            instructions.append("Liefere eine vollstaendige Ueberarbeitung im gewuenschten Umfang. Ueberschreite die Obergrenze nicht deutlich. Keine Kurzfassung und keine blosse Zusammenfassung.")
            if word_bounds is not None:
                minimum_words, maximum_words = word_bounds
                if maximum_words <= 180:
                    instructions.append(
                        f"Forme den Text zu einem vollen, natuerlichen Absatz oder Kurztext mit mindestens {minimum_words} Woertern. Vermeide starke Verdichtung auf nur wenige Saetze."
                    )
                    instructions.append("Nutze ungefaehr 7 bis 9 ganze Saetze, damit die Ueberarbeitung kurz, aber vollwertig bleibt.")
            if retry and word_bounds is not None:
                minimum_words, maximum_words = word_bounds
                instructions.append(
                    f"Pruefe vor dem Beenden die Wortzahl grob und bleibe zwischen {minimum_words} und {maximum_words} Woertern."
                )
        instructions.append("Gib nur die fertige Ueberarbeitung aus. Keine Einleitung, keine Erklaerung.")
        instructions.append(f"Aktueller Text oder Auftrag: {prompt}{context_block}")
        user_prompt = " ".join(instructions)
    elif profile == PROMPT_PROFILE_INFO:
        instructions = []
        if retry:
            instructions.append(
                "Der erste Infotext war zu kurz oder zu allgemein. Schreibe denselben Infotext jetzt vollstaendiger."
            )
            if previous_response and has_incomplete_long_form_ending(previous_response):
                instructions.append("Der erste Entwurf brach am Ende ab. Liefere jetzt einen vollstaendigen, sauber abgeschlossenen Text.")
            if previous_response:
                instructions.append("Erweitere den vorhandenen Entwurf statt nur neu anzusetzen.")
        else:
            instructions.append(
                "Schreibe einen gut lesbaren, sachlich passenden Infotext in derselben Sprache wie der Auftrag."
                if multilingual_runtime
                else "Schreibe einen gut lesbaren, sachlich passenden Infotext auf Deutsch."
            )
        if requested_format_instruction:
            instructions.append(requested_format_instruction)
        target_instruction_words = word_target or DEFAULT_LONG_FORM_WORD_TARGET
        instructions.append(build_word_target_instruction(target_instruction_words, retry=retry, word_bounds=word_bounds))
        if word_target is not None:
            instructions.append("Pruefe vor dem Beenden kurz die Laenge und erweitere den Text, falls er noch zu kurz ist.")
        if tone_hints:
            instructions.append(f"Ton und Stil: {', '.join(tone_hints)}.")
        instructions.append("Bleibe beim Thema. Keine Listen, ausser wenn sie ausdruecklich verlangt sind.")
        instructions.append("Wenn Fakten unsicher sind, bleibe allgemein statt Details zu erfinden.")
        instructions.append("Keine Einleitung ueber deine Aufgabe und keine Erklaerung danach.")
        instructions.append("Runde den Text mit einem natuerlichen, ruhigen Schlusssatz ab.")
        if previous_response:
            instructions.append(f"Ausgangsentwurf: {previous_response}")
        instructions.append(f"Thema: {prompt}{context_block}")
        user_prompt = " ".join(instructions)
    elif profile == PROMPT_PROFILE_WRITING:
        instructions = []
        if retry:
            instructions.append(
                "Der erste Entwurf war zu kurz oder zu allgemein. Schreibe denselben Text jetzt vollstaendiger und naeher am Wortziel."
            )
            if previous_response and has_incomplete_long_form_ending(previous_response):
                instructions.append("Der erste Entwurf brach am Ende ab. Liefere jetzt einen vollstaendigen, sauber abgeschlossenen Schluss.")
            if previous_response:
                instructions.append("Erweitere den vorhandenen Entwurf statt nur eine neue Mini-Antwort zu schreiben.")
        else:
            instructions.append(
                "Schreibe den angeforderten Text direkt in derselben Sprache wie der Auftrag."
                if multilingual_runtime
                else "Schreibe den angeforderten Text direkt auf Deutsch."
            )
        if requested_format_instruction:
            instructions.append(requested_format_instruction)
        target_instruction_words = word_target or DEFAULT_LONG_FORM_WORD_TARGET
        instructions.append(build_word_target_instruction(target_instruction_words, retry=retry, word_bounds=word_bounds))
        if retry and word_target is not None:
            minimum_words, maximum_words = word_bounds or build_word_target_window(word_target)
            instructions.append(
                f"Erweitere den Text jetzt auf mindestens {minimum_words} und hoechstens {maximum_words} Woerter."
            )
        if word_target is not None:
            instructions.append("Pruefe vor dem Beenden kurz die Laenge und erweitere den Text, falls er noch zu kurz ist.")
        if word_target is not None and word_target <= 140:
            instructions.append("Nutze 6 bis 7 ganze Saetze, damit der Text trotz kurzer Form vollstaendig wirkt.")
        if tone_hints:
            instructions.append(f"Ton und Stil: {', '.join(tone_hints)}.")
        if word_target is not None and re.search(r"\b(kurz|klein)\b", prompt.lower()):
            instructions.append("Auch wenn der Auftrag 'kurz' oder 'klein' sagt, halte ihn trotzdem nahe am Wortziel.")
        if requested_format == "Kartentext":
            instructions.append("Wenn kein Name genannt ist, schreibe ohne Platzhalter und ohne eckige Klammern.")
        if retry and requested_format == "Brief":
            instructions.append("Erweitere vor allem den Hauptteil des Briefs, nicht nur Anrede und Schluss.")
        if retry and requested_format == "Kartentext":
            instructions.append("Fuege zwei oder drei weitere ganze Saetze hinzu, damit der Kartentext vollstaendig wirkt.")
        instructions.append("Runde den Text mit einem natuerlichen, stimmigen Schlusssatz ab.")
        instructions.append("Der Text soll vollstaendig und brauchbar wirken, nicht nur aus wenigen Saetzen bestehen.")
        instructions.append("Liefer echten Nutztext statt einer Mini-Antwort.")
        instructions.append("Gib nur den fertigen Text aus. Keine Vorrede, keine Erklaerung, keine Nummerierung.")
        if previous_response:
            instructions.append(f"Ausgangsentwurf: {previous_response}")
        instructions.append(f"Auftrag: {prompt}{context_block}")
        user_prompt = " ".join(instructions)
    else:
        if retry:
            user_prompt = (
                "Beantworte die folgende Anfrage nur auf Deutsch. "
                "Genau zwei kurze Saetze. "
                "Antworte direkt auf die Frage. "
                "Verwende einfache, natuerliche Sprache. "
                "Keine Listen, keine Fremdsprache, keine Wiederholungen, keine erfundenen Details.\n\n"
                f"Anfrage: {prompt}"
            )
        else:
            user_prompt = (
                "Beantworte die folgende Anfrage kurz und klar in hoechstens zwei kurzen Saetzen. "
                "Antworte ausschliesslich auf Deutsch. "
                "Antworte direkt. "
                "Verwende einfache, natuerliche Sprache. "
                "Keine Wiederholungen, keine Einleitung, keine langen Listen, keine ausgeschmueckten Beispiele. "
                "Wenn du unsicher bist, sag das knapp statt Details zu erfinden.\n\n"
                f"Anfrage: {prompt}"
            )

    return profile, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_continuation_messages(
    profile: str,
    prompt: str,
    partial_text: str,
    *,
    multilingual_runtime: bool = False,
) -> list[dict[str, str]]:
    requested_language = infer_prompt_language(prompt)
    if multilingual_runtime:
        system_prompt = (
            "Du vollendest unvollstaendige Texte. "
            "Bleibe strikt in derselben Sprache wie der Auftrag. "
            "Wiederhole nichts aus dem vorhandenen Text. "
            "Liefere nur die direkte Fortsetzung bis zu einem sauberen Ende."
        )
    else:
        system_prompt = (
            "Du vollendest unvollstaendige Texte auf Deutsch. "
            "Wiederhole nichts aus dem vorhandenen Text. "
            "Liefere nur die direkte Fortsetzung bis zu einem sauberen Ende."
        )
    explicit_language_instruction = build_explicit_language_instruction(requested_language)
    tail_excerpt = partial_text[-CONTINUATION_CONTEXT_CHARACTERS:].strip()
    instructions = []
    if explicit_language_instruction:
        instructions.append(explicit_language_instruction)
    instructions.append(
        "Der vorhandene Text brach am Ende ab. Setze ihn direkt ab den letzten Worten fort, ohne den Anfang neu zu schreiben."
    )
    instructions.append("Fuehre den laufenden Satz oder Absatz sauber zu Ende und schliesse den Gesamttext natuerlich ab.")
    instructions.append(f"Urspruenglicher Auftrag: {prompt}")
    instructions.append(f"Letzter vorhandener Ausschnitt:\n{tail_excerpt}")
    user_prompt = " ".join(instructions)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_rewrite_underlength_messages(
    prompt: str,
    current_text: str,
    *,
    multilingual_runtime: bool = False,
) -> list[dict[str, str]]:
    word_bounds = extract_requested_word_bounds(prompt)
    requested_language = infer_prompt_language(prompt)
    minimum_words, maximum_words = word_bounds or (0, 0)
    if multilingual_runtime:
        system_prompt = (
            "Du erweiterst eine zu knappe Ueberarbeitung. "
            "Bleibe strikt in derselben Sprache wie der Auftrag. "
            "Bewahre Inhalt, Ton und Struktur. "
            "Gib nur die fertige neue Fassung aus."
        )
    else:
        system_prompt = (
            "Du erweiterst eine zu knappe Ueberarbeitung auf Deutsch. "
            "Bewahre Inhalt, Ton und Struktur. "
            "Gib nur die fertige neue Fassung aus."
        )
    instructions: list[str] = []
    explicit_language_instruction = build_explicit_language_instruction(requested_language)
    if explicit_language_instruction:
        instructions.append(explicit_language_instruction)
    if word_bounds is not None:
        instructions.append(
            f"Der aktuelle Rewrite ist noch zu kurz. Erweitere ihn auf mindestens {minimum_words} und hoechstens {maximum_words} Woerter."
        )
        if maximum_words <= 180:
            instructions.append("Schreibe einen vollen, natuerlichen Einzelabsatz mit etwa 7 bis 9 ganzen Saetzen.")
    instructions.append("Bewahre Aussage, Ton und Schwerpunkt des aktuellen Rewrites. Keine Zusammenfassung, keine Listen.")
    instructions.append(f"Aktueller Rewrite:\n{current_text.strip()}")
    instructions.append(f"Urspruenglicher Auftrag:\n{prompt.strip()}")
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": " ".join(instructions)},
    ]


def build_underlength_continuation_messages(
    profile: str,
    prompt: str,
    current_text: str,
    *,
    multilingual_runtime: bool = False,
) -> list[dict[str, str]]:
    word_bounds = extract_requested_word_bounds(prompt)
    word_target = extract_requested_word_target(prompt)
    requested_language = infer_prompt_language(prompt)
    if word_bounds is not None:
        minimum_words, maximum_words = word_bounds
    elif word_target is not None:
        minimum_words, maximum_words = build_word_target_window(word_target)
    else:
        minimum_words, maximum_words = 0, 0

    if multilingual_runtime:
        system_prompt = (
            "Du fuehrst einen bereits brauchbaren Text kontrolliert weiter. "
            "Bleibe strikt in derselben Sprache wie der Auftrag. "
            "Wiederhole nichts aus dem vorhandenen Text. "
            "Liefere nur die direkte Fortsetzung mit neuem Nutzinhalt."
        )
    else:
        system_prompt = (
            "Du fuehrst einen bereits brauchbaren deutschen Text kontrolliert weiter. "
            "Wiederhole nichts aus dem vorhandenen Text. "
            "Liefere nur die direkte Fortsetzung mit neuem Nutzinhalt."
        )

    instructions: list[str] = []
    explicit_language_instruction = build_explicit_language_instruction(requested_language)
    if explicit_language_instruction:
        instructions.append(explicit_language_instruction)
    if profile == PROMPT_PROFILE_INFO:
        instructions.append("Der Text ist noch zu kurz. Erweitere ihn mit 1 bis 2 weiteren sinnvollen Abschnitten.")
    else:
        instructions.append("Der Text ist noch zu kurz. Setze ihn mit dem naechsten sinnvollen Abschnitt fort.")
    if minimum_words > 0:
        instructions.append(
            f"Der Gesamttext soll mindestens {minimum_words} Woerter erreichen"
            + (f" und moeglichst unter {maximum_words} Woertern bleiben." if maximum_words > 0 else ".")
        )
    instructions.append("Fuehre Inhalt, Ton und Perspektive konsistent weiter.")
    instructions.append("Wiederhole weder den Anfang noch bereits geschriebene Saetze.")
    instructions.append("Gib nur die direkte Fortsetzung aus, nicht den Gesamttext.")
    instructions.append(f"Urspruenglicher Auftrag: {prompt}")
    instructions.append(f"Bisheriger Text:\n{current_text.strip()}")
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": " ".join(instructions)},
    ]


def merge_continuation_text(base_text: str, continuation_text: str) -> str:
    base = (base_text or "").rstrip()
    continuation = strip_common_lead_in(continuation_text or "").lstrip()
    if not base:
        return continuation
    if not continuation:
        return base
    if continuation[:1] in {".", ",", ";", ":", "!", "?", "”", "\""}:
        return f"{base}{continuation}"
    return f"{base} {continuation}"


def remove_consecutive_duplicate_paragraphs(text: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    if not paragraphs:
        return ""

    cleaned: list[str] = []
    previous_key = None
    for paragraph in paragraphs:
        key = re.sub(r"\s+", " ", paragraph.lower()).strip()
        if key == previous_key:
            continue
        cleaned.append(paragraph)
        previous_key = key
    return "\n\n".join(cleaned)


def remove_consecutive_duplicate_sentences(text: str) -> str:
    segments = re.split(r"(?<=[.!?])\s+", text.strip())
    cleaned: list[str] = []
    previous_key = None
    for segment in segments:
        sentence = segment.strip()
        if not sentence:
            continue
        key = re.sub(r"\s+", " ", sentence.lower()).strip()
        if key == previous_key:
            continue
        cleaned.append(sentence)
        previous_key = key
    return " ".join(cleaned).strip()


def normalize_response_whitespace(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = remove_consecutive_duplicate_paragraphs(normalized)
    normalized = remove_consecutive_duplicate_sentences(normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def normalize_long_form_response_whitespace(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = remove_consecutive_duplicate_paragraphs(normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def trim_to_sentence_limit(text: str, sentence_limit: int) -> str:
    segments = re.split(r"(?<=[.!?])\s+", text.strip())
    selected: list[str] = []
    for segment in segments:
        sentence = segment.strip()
        if not sentence:
            continue
        selected.append(sentence)
        if len(selected) >= sentence_limit:
            break
    if selected:
        return " ".join(selected).strip()
    return text.strip()


def strip_common_lead_in(text: str) -> str:
    cleaned = text.strip().strip("\"'")
    cleaned = re.sub(
        r"^(hier ist(?: ein(?: kurzer)?)?(?: englischer)?(?: bildprompt| prompt)?[:\-]\s*)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(bildprompt|prompt|umformulierung|antwort|brief|text|abschnitt|kartentext|e-mail|email|infotext|entwurf)[:\-]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip().strip("[]").strip()


def first_useful_line(text: str) -> str:
    for raw_line in text.splitlines():
        candidate = strip_common_lead_in(raw_line)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate:
            return candidate
    return ""


def enforce_character_limit(text: str, max_characters: int) -> str:
    normalized = text.strip()
    if len(normalized) <= max_characters:
        return normalized
    truncated = normalized[:max_characters].rstrip(" ,;:-")
    last_separator = max(truncated.rfind(", "), truncated.rfind(". "), truncated.rfind("; "))
    if last_separator >= max_characters // 2:
        truncated = truncated[:last_separator].rstrip(" ,;:-")
    return truncated.strip()


def sanitize_runner_response_text(profile: str, response_text: str) -> str:
    if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        normalized = normalize_long_form_response_whitespace(response_text)
    else:
        normalized = normalize_response_whitespace(response_text)
    if not normalized:
        return ""

    if profile == PROMPT_PROFILE_IMAGE:
        first_line = first_useful_line(normalized)
        if not first_line:
            first_line = strip_common_lead_in(normalized)
        first_line = re.sub(r"\s*,\s*", ", ", first_line)
        return enforce_character_limit(first_line, IMAGE_PROMPT_MAX_CHARACTERS)

    if profile == PROMPT_PROFILE_REWRITE:
        cleaned = strip_common_lead_in(normalized)
        return enforce_character_limit(cleaned, LONG_FORM_RESPONSE_MAX_CHARACTERS)

    if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        cleaned = strip_common_lead_in(normalized)
        return enforce_character_limit(cleaned, LONG_FORM_RESPONSE_MAX_CHARACTERS)

    shortened = trim_to_sentence_limit(normalized, MAX_VISIBLE_SENTENCES)
    shortened = strip_common_lead_in(shortened)
    return enforce_character_limit(shortened, RESPONSE_MAX_CHARACTERS)


def contains_cjk_characters(text: str) -> bool:
    return re.search(r"[\u3400-\u9fff]", text) is not None


def has_obvious_repetition(text: str) -> bool:
    lowered = text.lower()
    if re.search(r"\b(\w+)(?:[\s,;:-]+\1){3,}\b", lowered):
        return True
    return False


def has_incomplete_long_form_ending(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return False
    if re.search(r"[.!?…][\"'”»)]?\s*$", normalized):
        return False
    if re.search(r"[:,;\\-–—][\"'”»)]?\s*$", normalized):
        return True
    return re.search(r"[A-Za-zÀ-ɏß0-9][\"'”»)]?\s*$", normalized) is not None


def trim_to_complete_long_form_ending(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    if not has_incomplete_long_form_ending(normalized):
        return normalized
    sentence_matches = list(re.finditer(r"[.!?…][\"'”»)]?(?:\s|$)", normalized))
    if not sentence_matches:
        return normalized
    last_match = sentence_matches[-1]
    if last_match.end() < len(normalized) // 2:
        return normalized
    return normalized[:last_match.end()].rstrip()


def has_suspicious_mixed_case_token(text: str) -> bool:
    return re.search(r"\b[a-zÃ¤Ã¶Ã¼ÃŸ]+[A-Z][a-zA-Z]+\b", text) is not None


def has_suspicious_language_mix(text: str) -> bool:
    lowered = f" {text.lower()} "
    english_markers = (" both ", " and ", " the ", " with ", " direction ")
    german_markers = (" der ", " die ", " das ", " weil ", " ist ", " und ")
    return sum(marker in lowered for marker in english_markers) >= 2 and sum(marker in lowered for marker in german_markers) >= 2


def rewrite_has_language_mismatch(original_prompt: str, response_text: str) -> bool:
    requested_language = infer_prompt_language(original_prompt)
    if requested_language not in {"en", "es", "fr"}:
        return False
    response_language = infer_prompt_language(response_text)
    if response_language == requested_language:
        return False
    lowered = f" {response_text.lower()} "
    german_markers = (" der ", " die ", " das ", " und ", " mit ", " ist ", " eine ", " einen ")
    if sum(marker in lowered for marker in german_markers) >= 2:
        return True
    return response_language not in {requested_language, None}


def has_merged_article_token(text: str) -> bool:
    lowered = text.lower()
    return re.search(r"\b(?:das|der|die|dem|den|des|eine|einen|einem|einer)[a-z]{5,}\b", lowered) is not None


def image_prompt_needs_retry(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    keyword_count = len([segment for segment in re.split(r"\s*,\s*", normalized) if segment.strip()])
    if keyword_count < 8:
        return True
    lowered = f" {normalized.lower()} "
    required_signals = (" light", " lighting", " cinematic", " portrait", " scene", " atmosphere", " mood", " detailed", " soft", " dramatic")
    if not any(signal in lowered for signal in required_signals):
        return True
    return False


def rewrite_needs_retry(original_prompt: str, response_text: str) -> bool:
    normalized_prompt = re.sub(r"\s+", " ", original_prompt.strip().lower())
    normalized_response = re.sub(r"\s+", " ", response_text.strip().lower())
    if not normalized_response:
        return True
    if normalized_response == normalized_prompt:
        return True
    if len(normalized_response) < max(12, len(normalized_prompt) // 3):
        return True
    if rewrite_has_language_mismatch(original_prompt, response_text):
        return True
    word_bounds = extract_requested_word_bounds(original_prompt)
    if word_bounds is not None:
        minimum_words, maximum_words = word_bounds
        actual_words = count_response_words(response_text)
        if actual_words < minimum_words:
            return True
        overshoot_tolerance = max(12, int(maximum_words * 0.05))
        if actual_words > maximum_words + overshoot_tolerance:
            return True
    return False


def short_answer_needs_retry(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    if len(normalized) > RESPONSE_MAX_CHARACTERS:
        return True
    if normalized.endswith(":"):
        return True
    if has_suspicious_mixed_case_token(normalized):
        return True
    if has_suspicious_language_mix(normalized):
        return True
    if has_merged_article_token(normalized):
        return True
    return False


def is_significantly_under_word_target(target_words: int, actual_words: int) -> bool:
    minimum_words = max(40, int(target_words * 0.78))
    if target_words >= 220:
        minimum_words = max(minimum_words, target_words - 90)
    return actual_words < minimum_words


def has_unhelpful_writing_refusal(text: str) -> bool:
    lowered = text.lower()
    refusal_patterns = (
        r"\bich kann(?:\s+\w+){0,3}\s+leider\b",
        r"\bleider\s+kann\s+ich\b",
        r"\bich\s+kann\s+nicht\b",
        r"\bich\s+darf\b",
        r"\bals\s+ki\b",
    )
    return any(re.search(pattern, lowered) for pattern in refusal_patterns)


def long_form_needs_retry(profile: str, prompt: str, response_text: str) -> bool:
    normalized = response_text.strip()
    if not normalized:
        return True
    if has_unhelpful_writing_refusal(normalized):
        return True
    if has_suspicious_mixed_case_token(normalized):
        return True
    if has_suspicious_language_mix(normalized):
        return True
    if has_merged_article_token(normalized):
        return True
    if has_incomplete_long_form_ending(normalized):
        return True

    word_count = count_response_words(normalized)
    word_target = extract_requested_word_target(prompt)
    word_bounds = extract_requested_word_bounds(prompt)
    requested_format = infer_requested_format(prompt)

    if word_bounds is not None:
        minimum_words, _ = word_bounds
        if word_count < minimum_words:
            return True
    elif word_target is not None and is_significantly_under_word_target(word_target, word_count):
        return True

    if profile == PROMPT_PROFILE_WRITING and word_target is None:
        if requested_format == "Brief" and word_count < MIN_LONG_FORM_WORDS:
            return True
        if requested_format in {"Text", "Abschnitt", "Kartentext"} and word_count < 45:
            return True

    if profile == PROMPT_PROFILE_INFO and word_target is None and word_count < 60:
        normalized_prompt = prompt.lower()
        if any(keyword in normalized_prompt for keyword in ("text", "infotext", "sachtext", "fachtext", "erklaere", "erlaeutere")):
            return True

    return False


def response_needs_retry(profile: str, prompt: str, response_text: str) -> bool:
    normalized = response_text.strip()
    if not normalized:
        return True
    if contains_cjk_characters(normalized):
        return True
    if has_obvious_repetition(normalized):
        return True

    if profile == PROMPT_PROFILE_IMAGE:
        if image_prompt_needs_retry(normalized):
            return True
        lowered = f" {normalized.lower()} "
        german_markers = (" der ", " die ", " das ", " und ", " ist ", " wird ", " eine ", " einen ", " einer ", " einem ", " von ")
        if sum(marker in lowered for marker in german_markers) >= 2:
            return True
    elif profile == PROMPT_PROFILE_REWRITE:
        if rewrite_needs_retry(prompt, normalized):
            return True
    elif profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        if long_form_needs_retry(profile, prompt, normalized):
            return True
    elif short_answer_needs_retry(normalized):
        return True

    return False


def request_runner_response(runtime_state: dict, messages: list[dict[str, str]], *, request_settings: dict | None = None) -> str:
    base_url = f"http://{runtime_state['runner_host']}:{runtime_state['runner_port']}"
    request_settings = request_settings or {}
    requested_max_tokens = int(request_settings.get("max_tokens", RUNNER_MAX_TOKENS))
    estimated_prompt_tokens = estimate_message_token_usage(messages)
    safe_max_tokens = max(96, RUNNER_CONTEXT_LIMIT_TOKENS - estimated_prompt_tokens - 64)
    request_payload = {
        "messages": messages,
        "stream": False,
        "max_tokens": max(32, min(requested_max_tokens, safe_max_tokens)),
        "temperature": RUNNER_TEMPERATURE,
        "top_p": RUNNER_TOP_P,
        "repeat_penalty": RUNNER_REPEAT_PENALTY,
        "stop": request_settings.get("stop_sequences", RUNNER_STOP_SEQUENCES),
    }
    request_body = json.dumps(request_payload, ensure_ascii=True).encode("utf-8")
    request = urllib_request.Request(
        f"{base_url}/v1/chat/completions",
        data=request_body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )

    try:
        with urllib_request.urlopen(
            request,
            timeout=float(request_settings.get("timeout_seconds", RUNNER_PROMPT_TIMEOUT_SECONDS)),
        ) as response:
            response_body = response.read()
            response_status = response.status
    except urllib_error.HTTPError as exc:
        response_status = exc.code
        response_body = exc.read()
    except urllib_error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        reason_text = str(reason)
        if isinstance(reason, TimeoutError) or "timed out" in reason_text.lower():
            if probe_runner_port_open(runtime_state["runner_host"], int(runtime_state["runner_port"])):
                raise TextServiceRequestError(
                    status_code=HTTPStatus.GATEWAY_TIMEOUT,
                    error_type="runner_request_timeout",
                    blocker="runner_request_timeout",
                    message="Local text runner timed out while still processing the request.",
                ) from exc
        raise TextServiceRequestError(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_type="runner_request_failed",
            blocker="runner_unreachable",
            message=f"Local text runner is not reachable: {exc}",
        ) from exc
    except TimeoutError as exc:
        if probe_runner_port_open(runtime_state["runner_host"], int(runtime_state["runner_port"])):
            raise TextServiceRequestError(
                status_code=HTTPStatus.GATEWAY_TIMEOUT,
                error_type="runner_request_timeout",
                blocker="runner_request_timeout",
                message="Local text runner timed out while still processing the request.",
            ) from exc
        raise TextServiceRequestError(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_type="runner_request_failed",
            blocker="runner_unreachable",
            message=f"Local text runner is not reachable: {exc}",
        ) from exc
    except OSError as exc:
        if "timed out" in str(exc).lower() and probe_runner_port_open(runtime_state["runner_host"], int(runtime_state["runner_port"])):
            raise TextServiceRequestError(
                status_code=HTTPStatus.GATEWAY_TIMEOUT,
                error_type="runner_request_timeout",
                blocker="runner_request_timeout",
                message="Local text runner timed out while still processing the request.",
            ) from exc
        raise TextServiceRequestError(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_type="runner_request_failed",
            blocker="runner_unreachable",
            message=f"Local text runner is not reachable: {exc}",
        ) from exc

    try:
        response_payload = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_GATEWAY,
            error_type="runner_invalid_response",
            blocker="runner_invalid_response",
            message="Local text runner returned invalid JSON.",
        ) from exc

    response_text = extract_runner_response_text(response_payload)
    if response_status != HTTPStatus.OK or response_text is None:
        message = None
        if isinstance(response_payload, dict):
            error_payload = response_payload.get("error")
            if isinstance(error_payload, dict) and isinstance(error_payload.get("message"), str):
                message = error_payload.get("message").strip()
            elif isinstance(response_payload.get("message"), str):
                message = response_payload.get("message").strip()
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_GATEWAY if response_status == HTTPStatus.OK else HTTPStatus(response_status),
            error_type="runner_request_failed",
            blocker="runner_request_failed",
            message=message or "Local text runner did not return a usable response.",
        )

    return response_text


def post_runner_prompt(
    runtime_state: dict,
    prompt: str,
    *,
    mode: str | None = None,
    summary: str | None = None,
    recent_messages: list[dict[str, str]] | None = None,
) -> str:
    multilingual_runtime = runtime_uses_multilingual_profile(runtime_state)
    profile, messages = build_runner_messages(
        prompt,
        forced_mode=mode,
        summary=summary,
        recent_messages=recent_messages,
        multilingual_runtime=multilingual_runtime,
    )
    response_text = request_runner_response(
        runtime_state,
        messages,
        request_settings=build_runner_request_settings(profile, prompt),
    )
    sanitized_response_text = sanitize_runner_response_text(profile, response_text)
    if response_needs_retry(profile, prompt, sanitized_response_text):
        _, retry_messages = build_runner_messages(
            prompt,
            retry=True,
            previous_response=sanitized_response_text,
            forced_mode=mode,
            summary=summary,
            recent_messages=recent_messages,
            multilingual_runtime=multilingual_runtime,
        )
        retry_response_text = request_runner_response(
            runtime_state,
            retry_messages,
            request_settings=build_runner_request_settings(
                profile,
                prompt,
                retry=True,
                previous_response=sanitized_response_text,
            ),
        )
        retry_sanitized_response_text = sanitize_runner_response_text(profile, retry_response_text)
        if not response_needs_retry(profile, prompt, retry_sanitized_response_text):
            sanitized_response_text = retry_sanitized_response_text
        elif retry_sanitized_response_text:
            if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
                first_incomplete = has_incomplete_long_form_ending(sanitized_response_text)
                retry_incomplete = has_incomplete_long_form_ending(retry_sanitized_response_text)
                first_words = count_response_words(sanitized_response_text)
                retry_words = count_response_words(retry_sanitized_response_text)
                word_bounds = extract_requested_word_bounds(prompt)
                if first_incomplete and not retry_incomplete:
                    if should_prefer_retry_by_word_bounds(
                        word_bounds,
                        first_words=first_words,
                        retry_words=retry_words,
                    ):
                        sanitized_response_text = retry_sanitized_response_text
                elif not (retry_incomplete and not first_incomplete):
                    target_words = extract_requested_word_target(prompt)
                    if word_bounds is not None:
                        if should_prefer_retry_by_word_bounds(
                            word_bounds,
                            first_words=first_words,
                            retry_words=retry_words,
                        ):
                            sanitized_response_text = retry_sanitized_response_text
                    elif target_words is not None:
                        first_gap = abs(target_words - first_words)
                        retry_gap = abs(target_words - retry_words)
                        if retry_gap <= first_gap:
                            sanitized_response_text = retry_sanitized_response_text
                    elif retry_words >= first_words:
                        sanitized_response_text = retry_sanitized_response_text
            elif profile == PROMPT_PROFILE_REWRITE:
                first_incomplete = has_incomplete_long_form_ending(sanitized_response_text)
                retry_incomplete = has_incomplete_long_form_ending(retry_sanitized_response_text)
                first_words = count_response_words(sanitized_response_text)
                retry_words = count_response_words(retry_sanitized_response_text)
                if first_incomplete and not retry_incomplete:
                    word_bounds = extract_requested_word_bounds(prompt)
                    if should_prefer_retry_by_word_bounds(
                        word_bounds,
                        first_words=first_words,
                        retry_words=retry_words,
                    ):
                        sanitized_response_text = retry_sanitized_response_text
                elif not (retry_incomplete and not first_incomplete):
                    word_bounds = extract_requested_word_bounds(prompt)
                    if word_bounds is not None:
                        if should_prefer_retry_by_word_bounds(
                            word_bounds,
                            first_words=first_words,
                            retry_words=retry_words,
                        ):
                            sanitized_response_text = retry_sanitized_response_text
                    else:
                        sanitized_response_text = retry_sanitized_response_text
            else:
                sanitized_response_text = retry_sanitized_response_text

    if profile in (PROMPT_PROFILE_REWRITE, PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        completed_text = sanitized_response_text
        for _ in range(MAX_CONTINUATION_ATTEMPTS):
            if not has_incomplete_long_form_ending(completed_text):
                break
            continuation_messages = build_continuation_messages(
                profile,
                prompt,
                completed_text,
                multilingual_runtime=multilingual_runtime,
            )
            continuation_response_text = request_runner_response(
                runtime_state,
                continuation_messages,
                request_settings={
                    "max_tokens": RUNNER_CONTINUATION_MAX_TOKENS,
                    "timeout_seconds": min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, 120.0),
                    "stop_sequences": RUNNER_LONG_FORM_STOP_SEQUENCES,
                },
            )
            continuation_sanitized_text = sanitize_runner_response_text(profile, continuation_response_text)
            merged_continuation_text = merge_continuation_text(completed_text, continuation_sanitized_text)
            if merged_continuation_text == completed_text:
                break
            completed_text = merged_continuation_text
        if has_incomplete_long_form_ending(completed_text):
            completed_text = trim_to_complete_long_form_ending(completed_text)
        sanitized_response_text = completed_text

    if profile == PROMPT_PROFILE_REWRITE:
        word_bounds = extract_requested_word_bounds(prompt)
        if word_bounds is not None:
            minimum_words, maximum_words = word_bounds
            current_words = count_response_words(sanitized_response_text)
            if current_words < minimum_words and maximum_words <= 180:
                underlength_messages = build_rewrite_underlength_messages(
                    prompt,
                    sanitized_response_text,
                    multilingual_runtime=multilingual_runtime,
                )
                underlength_response_text = request_runner_response(
                    runtime_state,
                    underlength_messages,
                    request_settings={
                        "max_tokens": min(RUNNER_LONG_FORM_MAX_TOKENS, max(260, int(maximum_words * 1.45))),
                        "timeout_seconds": min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, 180.0),
                    },
                )
                underlength_sanitized_text = sanitize_runner_response_text(profile, underlength_response_text)
                if underlength_sanitized_text:
                    current_distance = calculate_word_bounds_distance(word_bounds, current_words)
                    expanded_words = count_response_words(underlength_sanitized_text)
                    expanded_distance = calculate_word_bounds_distance(word_bounds, expanded_words)
                    if expanded_distance <= current_distance and not rewrite_has_language_mismatch(prompt, underlength_sanitized_text):
                        sanitized_response_text = underlength_sanitized_text
    elif profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        word_bounds = extract_requested_word_bounds(prompt)
        if word_bounds is not None:
            minimum_words, maximum_words = word_bounds
            staged_text = sanitized_response_text
            for _ in range(MAX_UNDERLENGTH_CONTINUATION_ATTEMPTS):
                current_words = count_response_words(staged_text)
                if current_words >= minimum_words:
                    break
                remaining_words = max(24, maximum_words - current_words)
                underlength_messages = build_underlength_continuation_messages(
                    profile,
                    prompt,
                    staged_text,
                    multilingual_runtime=multilingual_runtime,
                )
                underlength_response_text = request_runner_response(
                    runtime_state,
                    underlength_messages,
                    request_settings={
                        "max_tokens": min(RUNNER_LONG_FORM_MAX_TOKENS, max(120, int(remaining_words * 1.7))),
                        "timeout_seconds": min(RUNNER_LONG_FORM_TIMEOUT_SECONDS, 180.0),
                        "stop_sequences": RUNNER_LONG_FORM_STOP_SEQUENCES,
                    },
                )
                underlength_sanitized_text = sanitize_runner_response_text(profile, underlength_response_text)
                merged_underlength_text = merge_continuation_text(staged_text, underlength_sanitized_text)
                if merged_underlength_text == staged_text:
                    break
                staged_text = merged_underlength_text
            sanitized_response_text = staged_text

    if not sanitized_response_text:
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_GATEWAY,
            error_type="runner_invalid_response",
            blocker="runner_empty_response",
            message="Local text runner returned an empty response.",
        )

    if contains_cjk_characters(sanitized_response_text) or has_obvious_repetition(sanitized_response_text):
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_GATEWAY,
            error_type="runner_low_quality_response",
            blocker="runner_low_quality_response",
            message="Local text runner returned an unusable response.",
        )

    return sanitized_response_text


def build_runtime_state(config: dict) -> dict:
    resolved_model_path = resolve_model_path(config.get("model_path", ""))
    resolved_runner_binary_path, runner_present = discover_runner_binary(config)
    model_configured = resolved_model_path is not None
    model_present = bool(resolved_model_path and resolved_model_path.is_file())
    runner_reachable = probe_runner_reachable(config["runner_host"], config["runner_port"])
    runner_port_usable = runner_reachable or is_runner_port_usable(config["runner_host"], config["runner_port"])
    runner_startable = runner_present and model_present and runner_port_usable

    if not model_configured:
        service_mode = "stub"
        model_status = config["model_status"]
        inference_available = False
    elif not model_present:
        service_mode = "real_model_not_ready"
        model_status = "model_missing"
        inference_available = False
    elif runner_reachable:
        service_mode = "real_model_ready"
        model_status = "ready"
        inference_available = True
    elif not runner_present:
        service_mode = "real_model_not_ready"
        model_status = "runner_missing"
        inference_available = False
    elif not runner_port_usable:
        service_mode = "real_model_not_ready"
        model_status = "runner_port_unusable"
        inference_available = False
    else:
        service_mode = "real_model_not_ready"
        model_status = "runner_not_running"
        inference_available = False

    return {
        "service_mode": service_mode,
        "stub_mode": service_mode == "stub",
        "runner_type": config["runner_type"],
        "runner_host": config["runner_host"],
        "runner_port": config["runner_port"],
        "runner_binary_path": str(resolved_runner_binary_path) if resolved_runner_binary_path is not None else None,
        "runner_present": runner_present,
        "runner_reachable": runner_reachable,
        "runner_port_usable": runner_port_usable,
        "runner_startable": runner_startable,
        "model_format": config["model_format"],
        "model_path": config["model_path"] or None,
        "resolved_model_path": str(resolved_model_path) if resolved_model_path is not None else None,
        "model_configured": model_configured,
        "model_present": model_present,
        "inference_available": inference_available,
        "model_status": model_status,
    }


def build_prompt_stub_response(*, service_name: str, runtime_state: dict, prompt: str) -> dict:
    normalized_prompt = prompt.strip()
    return {
        "ok": True,
        "service": service_name,
        "mode": DEFAULT_PROMPT_MODE,
        "service_mode": runtime_state["service_mode"],
        "runner_type": runtime_state["runner_type"],
        "runner_reachable": runtime_state["runner_reachable"],
        "model_status": runtime_state["model_status"],
        "model_configured": runtime_state["model_configured"],
        "model_present": runtime_state["model_present"],
        "inference_available": runtime_state["inference_available"],
        "response_text": f"Stub mode only. No local text model configured. Prompt accepted: {normalized_prompt}",
        "stub": runtime_state["stub_mode"],
    }


def build_prompt_runner_response(*, service_name: str, runtime_state: dict, response_text: str) -> dict:
    return {
        "ok": True,
        "service": service_name,
        "mode": DEFAULT_RUNNER_PROMPT_MODE,
        "service_mode": runtime_state["service_mode"],
        "runner_type": runtime_state["runner_type"],
        "runner_reachable": runtime_state["runner_reachable"],
        "model_status": runtime_state["model_status"],
        "model_configured": runtime_state["model_configured"],
        "model_present": runtime_state["model_present"],
        "inference_available": runtime_state["inference_available"],
        "response_text": response_text,
        "stub": False,
    }


def build_request_error_response(*, service_name: str, runtime_state: dict, error_type: str, blocker: str, message: str) -> dict:
    return {
        "ok": False,
        "service": service_name,
        "service_mode": runtime_state["service_mode"],
        "runner_type": runtime_state["runner_type"],
        "runner_reachable": runtime_state["runner_reachable"],
        "model_status": runtime_state["model_status"],
        "model_configured": runtime_state["model_configured"],
        "model_present": runtime_state["model_present"],
        "inference_available": runtime_state["inference_available"],
        "error_type": error_type,
        "blocker": blocker,
        "message": message,
        "stub": runtime_state["stub_mode"],
    }


def validate_prompt_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_json_payload",
            message="JSON object required.",
        )

    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="prompt_not_string",
            message="prompt must be a string.",
        )

    normalized_prompt = prompt.strip()
    if not normalized_prompt:
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="empty_prompt",
            message="prompt must not be empty.",
        )

    if len(normalized_prompt) > MAX_PROMPT_LENGTH:
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="prompt_too_long",
            message=f"prompt exceeds {MAX_PROMPT_LENGTH} characters.",
        )

    return normalized_prompt


def validate_optional_mode_payload(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("mode")
    if value is None:
        return None
    if not isinstance(value, str):
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="mode_not_string",
            message="mode must be a string.",
        )
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in VALID_TEXT_WORK_MODES:
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="invalid_mode",
            message="mode must be one of writing, rewrite or image_prompt.",
        )
    return normalized


def validate_optional_summary_payload(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("summary")
    if value is None:
        return None
    if not isinstance(value, str):
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="summary_not_string",
            message="summary must be a string.",
        )
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:900]


def validate_optional_recent_messages_payload(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []
    value = payload.get("recent_messages")
    if value is None:
        return []
    if not isinstance(value, list):
        raise TextServiceRequestError(
            status_code=HTTPStatus.BAD_REQUEST,
            error_type="invalid_request",
            blocker="recent_messages_not_list",
            message="recent_messages must be a list.",
        )
    validated: list[dict[str, str]] = []
    for entry in value[:6]:
        if not isinstance(entry, dict):
            continue
        role_value = entry.get("role")
        content_value = entry.get("content")
        if not isinstance(role_value, str) or not isinstance(content_value, str):
            continue
        normalized_role = role_value.strip().lower()
        normalized_content = content_value.strip()
        if normalized_role not in {"user", "assistant"} or not normalized_content:
            continue
        validated.append({"role": normalized_role, "content": normalized_content[:400]})
    return validated


class TextServiceServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], config: dict) -> None:
        super().__init__(server_address, handler_class)
        self.config = config

    def get_runtime_config(self) -> dict:
        config_path_value = self.config.get("config_path")
        if isinstance(config_path_value, str) and config_path_value.strip():
            try:
                updated_config = load_config(Path(config_path_value.strip()))
            except TextServiceConfigError:
                return self.config
            self.config = updated_config
            return updated_config
        return self.config

    def build_health_payload(self) -> dict:
        current_config = self.get_runtime_config()
        runtime_state = build_runtime_state(current_config)
        return {
            "service": current_config["service_name"],
            "status": "ok",
            "enabled": current_config["enabled"],
            "host": current_config["host"],
            "port": current_config["port"],
            "service_mode": runtime_state["service_mode"],
            "runner_type": runtime_state["runner_type"],
            "runner_binary_path": runtime_state["runner_binary_path"],
            "runner_present": runtime_state["runner_present"],
            "runner_reachable": runtime_state["runner_reachable"],
            "runner_startable": runtime_state["runner_startable"],
            "model_status": runtime_state["model_status"],
            "model_configured": runtime_state["model_configured"],
            "model_present": runtime_state["model_present"],
            "inference_available": runtime_state["inference_available"],
            "stub_mode": runtime_state["stub_mode"],
        }

    def build_info_payload(self) -> dict:
        current_config = self.get_runtime_config()
        runtime_state = build_runtime_state(current_config)
        return {
            "service": current_config["service_name"],
            "status": "ok",
            "enabled": current_config["enabled"],
            "host": current_config["host"],
            "port": current_config["port"],
            "service_mode": runtime_state["service_mode"],
            "runner_type": runtime_state["runner_type"],
            "runner_host": runtime_state["runner_host"],
            "runner_port": runtime_state["runner_port"],
            "runner_binary_path": runtime_state["runner_binary_path"],
            "runner_present": runtime_state["runner_present"],
            "runner_reachable": runtime_state["runner_reachable"],
            "runner_port_usable": runtime_state["runner_port_usable"],
            "runner_startable": runtime_state["runner_startable"],
            "model_format": runtime_state["model_format"],
            "model_path": runtime_state["model_path"],
            "resolved_model_path": runtime_state["resolved_model_path"],
            "model_status": runtime_state["model_status"],
            "model_configured": runtime_state["model_configured"],
            "model_present": runtime_state["model_present"],
            "config_path": current_config["config_path"],
            "api_version": "v1",
            "inference_available": runtime_state["inference_available"],
            "prompt_endpoint_available": True,
            "stub_mode": runtime_state["stub_mode"],
            "capabilities": [],
            "endpoints": ["/health", "/info", "/prompt"],
        }


class TextServiceHandler(BaseHTTPRequestHandler):
    server: TextServiceServer
    server_version = "LocalTextService/1.0"

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(HTTPStatus.OK, self.server.build_health_payload())
            return
        if self.path == "/info":
            self.send_json(HTTPStatus.OK, self.server.build_info_payload())
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})

    def do_POST(self) -> None:
        if self.path == "/prompt":
            self.handle_prompt()
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"status": "error", "reason": "not_found"})

    def log_message(self, format: str, *args) -> None:
        return

    def handle_prompt(self) -> None:
        current_config = self.server.get_runtime_config()
        try:
            payload = self.read_json_body()
            prompt = validate_prompt_payload(payload)
            mode = validate_optional_mode_payload(payload)
            summary = validate_optional_summary_payload(payload)
            recent_messages = validate_optional_recent_messages_payload(payload)
        except TextServiceRequestError as exc:
            runtime_state = build_runtime_state(current_config)
            self.send_json(
                exc.status_code,
                build_request_error_response(
                    service_name=current_config["service_name"],
                    runtime_state=runtime_state,
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return

        runtime_state = build_runtime_state(current_config)
        if runtime_state["service_mode"] == "stub":
            self.send_json(
                HTTPStatus.OK,
                build_prompt_stub_response(
                    service_name=current_config["service_name"],
                    runtime_state=runtime_state,
                    prompt=prompt,
                ),
            )
            return

        if runtime_state["service_mode"] != "real_model_ready":
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_request_error_response(
                    service_name=current_config["service_name"],
                    runtime_state=runtime_state,
                    error_type="model_not_ready",
                    blocker=runtime_state["service_mode"],
                    message="Local text model is not ready.",
                ),
            )
            return

        try:
            response_text = post_runner_prompt(
                runtime_state,
                prompt,
                mode=mode,
                summary=summary,
                recent_messages=recent_messages,
            )
        except TextServiceRequestError as exc:
            self.send_json(
                exc.status_code,
                build_request_error_response(
                    service_name=current_config["service_name"],
                    runtime_state=runtime_state,
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return

        self.send_json(
            HTTPStatus.OK,
            build_prompt_runner_response(
                service_name=current_config["service_name"],
                runtime_state=runtime_state,
                response_text=response_text,
            ),
        )

    def read_json_body(self) -> object:
        content_length_header = self.headers.get("Content-Length", "").strip()
        if not content_length_header:
            raise TextServiceRequestError(
                status_code=HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker="missing_request_body",
                message="request body required.",
            )

        try:
            content_length = int(content_length_header)
        except ValueError as exc:
            raise TextServiceRequestError(
                status_code=HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker="invalid_content_length",
                message="invalid Content-Length.",
            ) from exc

        if content_length <= 0:
            raise TextServiceRequestError(
                status_code=HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker="empty_request_body",
                message="request body required.",
            )

        raw_body = self.rfile.read(content_length)
        if not raw_body:
            raise TextServiceRequestError(
                status_code=HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker="empty_request_body",
                message="request body required.",
            )

        try:
            return json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TextServiceRequestError(
                status_code=HTTPStatus.BAD_REQUEST,
                error_type="invalid_request",
                blocker="invalid_json",
                message="valid UTF-8 JSON required.",
            ) from exc

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local loopback-only text service skeleton.")
    parser.add_argument("--config", default=str(default_config_path()), help="Path to the text service config JSON.")
    parser.add_argument("--host", default=None, help="Optional host override. Must stay 127.0.0.1.")
    parser.add_argument("--port", type=int, default=None, help="Optional port override.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))

    if args.host is not None:
        config["host"] = args.host
    if args.port is not None:
        config["port"] = args.port

    config = normalize_config(config)
    config["config_path"] = str(Path(args.config).resolve())

    if not config["enabled"]:
        raise SystemExit("text service disabled by config")

    with TextServiceServer((config["host"], config["port"]), TextServiceHandler, config) as server:
        server.serve_forever()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
