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
RUNNER_PROMPT_TIMEOUT_SECONDS = 30.0
RUNNER_MAX_TOKENS = 80
RUNNER_TEMPERATURE = 0.1
RUNNER_TOP_P = 0.78
RUNNER_REPEAT_PENALTY = 1.18
RUNNER_STOP_SEQUENCES = ["\n\n\n", "\nUser:", "\nBenutzer:", "\nSystem:", "<|im_end|>"]
RESPONSE_MAX_CHARACTERS = 320
IMAGE_PROMPT_MAX_CHARACTERS = 240
LONG_FORM_RESPONSE_MAX_CHARACTERS = 4200
MAX_VISIBLE_SENTENCES = 2
DEFAULT_LONG_FORM_WORD_TARGET = 110
MIN_LONG_FORM_WORDS = 55
MAX_LONG_FORM_WORD_TARGET = 420
RUNNER_LONG_FORM_MIN_TOKENS = 220
RUNNER_LONG_FORM_MAX_TOKENS = 620
RUNNER_LONG_FORM_TIMEOUT_SECONDS = 60.0

PROMPT_PROFILE_IMAGE = "image_prompt_help"
PROMPT_PROFILE_REWRITE = "rewrite"
PROMPT_PROFILE_INFO = "info_text"
PROMPT_PROFILE_WRITING = "writing_task"
PROMPT_PROFILE_SHORT = "short_answer"


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
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
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


def extract_requested_word_target(prompt: str) -> int | None:
    match = re.search(
        r"\b(?:ca\.?|circa|etwa|ungefaehr|ungef\u00e4hr)?\s*(\d{2,4})\s*(?:woerter|worte|worten|w\u00f6rter|w\u00f6rtern|words)\b",
        prompt,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    try:
        target = int(match.group(1))
    except ValueError:
        return None

    if target < 40 or target > MAX_LONG_FORM_WORD_TARGET:
        return None
    return target


def infer_requested_format(prompt: str) -> str | None:
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


def build_word_target_window(word_target: int) -> tuple[int, int]:
    tolerance = max(8, int(word_target * 0.1))
    minimum_words = max(40, word_target - tolerance)
    maximum_words = word_target + tolerance
    return minimum_words, maximum_words


def build_requested_format_instruction(requested_format: str | None) -> str | None:
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


def build_word_target_instruction(word_target: int | None, *, retry: bool = False) -> str:
    if word_target is None:
        return "Liefere einen kompakten, aber vollstaendigen Text."
    minimum_words, maximum_words = build_word_target_window(word_target)
    if retry:
        return (
            f"Ziel: ungefaehr {word_target} Woerter. Schreibe mindestens {minimum_words} und hoechstens {maximum_words} Woerter. "
            f"Der erste Entwurf war zu kurz. Unterschreite {minimum_words} Woerter nicht."
        )
    return (
        f"Ziel: ungefaehr {word_target} Woerter. Schreibe moeglichst zwischen {minimum_words} und {maximum_words} Woertern. "
        "Eine kleine Abweichung ist okay, aber bleibe moeglichst nah daran."
    )


def count_response_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9\u00c0-\u024f\u00df]+(?:['-][A-Za-z0-9\u00c0-\u024f\u00df]+)*", text))


def build_runner_request_settings(profile: str, prompt: str, *, retry: bool = False) -> dict:
    word_target = extract_requested_word_target(prompt)
    max_tokens = RUNNER_MAX_TOKENS
    timeout_seconds = RUNNER_PROMPT_TIMEOUT_SECONDS

    if profile == PROMPT_PROFILE_REWRITE:
        max_tokens = 120
    elif profile == PROMPT_PROFILE_INFO:
        target_words = word_target or DEFAULT_LONG_FORM_WORD_TARGET
        max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(RUNNER_LONG_FORM_MIN_TOKENS, int(target_words * 2.0)))
        timeout_seconds = RUNNER_LONG_FORM_TIMEOUT_SECONDS if word_target else 45.0
    elif profile == PROMPT_PROFILE_WRITING:
        target_words = word_target or DEFAULT_LONG_FORM_WORD_TARGET
        minimum_tokens = 300 if word_target is not None and word_target <= 160 else RUNNER_LONG_FORM_MIN_TOKENS
        max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, max(minimum_tokens, int(target_words * 2.3)))
        timeout_seconds = RUNNER_LONG_FORM_TIMEOUT_SECONDS if word_target else 45.0

    if retry and profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        max_tokens = min(RUNNER_LONG_FORM_MAX_TOKENS, int(max_tokens * 1.12))
        timeout_seconds = min(70.0, timeout_seconds + 8.0)

    return {
        "max_tokens": int(max_tokens),
        "timeout_seconds": float(timeout_seconds),
    }


def classify_prompt_profile(prompt: str) -> str:
    normalized = prompt.lower()
    word_target = extract_requested_word_target(prompt)

    image_keywords = (
        "bildprompt",
        "prompt fuer ein bild",
        "prompt für ein bild",
        "prompt fuer ein foto",
        "prompt für ein foto",
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
        "kürzer um",
        "schreibe eleganter",
        "schreibe fluessiger",
        "schreibe flüssiger",
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
        "persÃ¶nlich",
    )
    info_keywords = (
        "infotext",
        "sachtext",
        "fachtext",
        "erklaertext",
        "erklÃ¤rtext",
        "erklaere",
        "erklÃ¤re",
        "erlaeutere",
        "erlÃ¤utere",
        "erklaer",
        "erklÃ¤r",
        "sachlich",
        "informativ",
        "fakten",
        "wissenswert",
        "ueberblick",
        "Ã¼berblick",
    )
    has_text_over_topic = re.search(r"\btext\s+(?:ueber|Ã¼ber)\b", normalized) is not None

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


def extract_image_prompt_subject(prompt: str) -> str:
    subject = prompt.strip()
    subject = re.sub(
        r"^(bitte\s+)?(erstelle|schreibe|mach)\s+(mir\s+)?(einen|einen kurzen|einen kompakten)?\s*(bildprompt|prompt)\s+(fuer|für|zu)\s+",
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
        r"^(ich\s+brauche\s+)?(hilfe\s+bei\s+einem\s+bildprompt|einen\s+bildprompt|einen\s+prompt)\s+(fuer|für|zu)\s+",
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
) -> tuple[str, list[dict[str, str]]]:
    profile = classify_prompt_profile(prompt)
    image_subject = extract_image_prompt_subject(prompt)
    word_target = extract_requested_word_target(prompt)
    tone_hints = extract_style_hints(prompt)
    requested_format = infer_requested_format(prompt)
    requested_format_instruction = build_requested_format_instruction(requested_format)
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
    if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
        system_prompt += (
            " Bei harmlosen Schreibauftraegen lieferst du direkt den gewuenschten Nutztext. "
            "Erfuelle Format, Ton und grobe Laenge so gut wie moeglich. "
            "Keine Verweigerung, keine Meta-Hinweise, keine Entschuldigung."
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
                f"Subject: {image_subject}"
            )
        else:
            user_prompt = (
                "Create exactly one short English image prompt. "
                "Use comma-separated visual keywords only. "
                "Include subject, style, lighting, mood and the most important scene details. "
                "No explanation, no full sentence, no German words. "
                "Use 10 to 14 short keyword groups. "
                "Between 18 and 30 words.\n\n"
                f"Subject: {image_subject}"
            )
    elif profile == PROMPT_PROFILE_REWRITE:
        user_prompt = (
            "Formuliere den folgenden Text kurz, natuerlich und sauber um. "
            "Behalte die Bedeutung bei. "
            "Gib nur die fertige Umformulierung aus. "
            "Antworte ausschliesslich auf Deutsch. "
            "Keine Einleitung, keine Erklaerung.\n\n"
            f"Text: {prompt}"
        )
    elif profile == PROMPT_PROFILE_INFO:
        instructions = []
        if retry:
            instructions.append(
                "Der erste Infotext war zu kurz oder zu allgemein. Schreibe denselben Infotext jetzt vollstaendiger."
            )
            if previous_response:
                instructions.append("Erweitere den vorhandenen Entwurf statt nur neu anzusetzen.")
        else:
            instructions.append("Schreibe einen gut lesbaren, sachlich passenden Infotext auf Deutsch.")
        if requested_format_instruction:
            instructions.append(requested_format_instruction)
        instructions.append(build_word_target_instruction(word_target, retry=retry))
        if word_target is not None:
            instructions.append("Pruefe vor dem Beenden kurz die Laenge und erweitere den Text, falls er noch zu kurz ist.")
        if tone_hints:
            instructions.append(f"Ton und Stil: {', '.join(tone_hints)}.")
        instructions.append("Bleibe beim Thema. Keine Listen, ausser wenn sie ausdruecklich verlangt sind.")
        instructions.append("Wenn Fakten unsicher sind, bleibe allgemein statt Details zu erfinden.")
        instructions.append("Keine Einleitung ueber deine Aufgabe und keine Erklaerung danach.")
        if previous_response:
            instructions.append(f"Ausgangsentwurf: {previous_response}")
        instructions.append(f"Thema: {prompt}")
        user_prompt = " ".join(instructions)
    elif profile == PROMPT_PROFILE_WRITING:
        instructions = []
        if retry:
            instructions.append(
                "Der erste Entwurf war zu kurz oder zu allgemein. Schreibe denselben Text jetzt vollstaendiger und naeher am Wortziel."
            )
            if previous_response:
                instructions.append("Erweitere den vorhandenen Entwurf statt nur eine neue Mini-Antwort zu schreiben.")
        else:
            instructions.append("Schreibe den angeforderten Text direkt auf Deutsch.")
        if requested_format_instruction:
            instructions.append(requested_format_instruction)
        instructions.append(build_word_target_instruction(word_target, retry=retry))
        if retry and word_target is not None:
            minimum_words, maximum_words = build_word_target_window(word_target)
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
        instructions.append("Der Text soll vollstaendig und brauchbar wirken, nicht nur aus wenigen Saetzen bestehen.")
        instructions.append("Liefer echten Nutztext statt einer Mini-Antwort.")
        instructions.append("Gib nur den fertigen Text aus. Keine Vorrede, keine Erklaerung, keine Nummerierung.")
        if previous_response:
            instructions.append(f"Ausgangsentwurf: {previous_response}")
        instructions.append(f"Auftrag: {prompt}")
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
        first_line = first_useful_line(normalized)
        if not first_line:
            first_line = strip_common_lead_in(normalized)
        first_line = trim_to_sentence_limit(first_line, 2)
        return enforce_character_limit(first_line, RESPONSE_MAX_CHARACTERS)

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


def has_suspicious_mixed_case_token(text: str) -> bool:
    return re.search(r"\b[a-zäöüß]+[A-Z][a-zA-Z]+\b", text) is not None


def has_suspicious_language_mix(text: str) -> bool:
    lowered = f" {text.lower()} "
    english_markers = (" both ", " and ", " the ", " with ", " direction ")
    german_markers = (" der ", " die ", " das ", " weil ", " ist ", " und ")
    return sum(marker in lowered for marker in english_markers) >= 2 and sum(marker in lowered for marker in german_markers) >= 2


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

    word_count = count_response_words(normalized)
    word_target = extract_requested_word_target(prompt)
    requested_format = infer_requested_format(prompt)

    if word_target is not None and is_significantly_under_word_target(word_target, word_count):
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
    request_payload = {
        "messages": messages,
        "stream": False,
        "max_tokens": int(request_settings.get("max_tokens", RUNNER_MAX_TOKENS)),
        "temperature": RUNNER_TEMPERATURE,
        "top_p": RUNNER_TOP_P,
        "repeat_penalty": RUNNER_REPEAT_PENALTY,
        "stop": RUNNER_STOP_SEQUENCES,
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
    except (urllib_error.URLError, TimeoutError, OSError) as exc:
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


def post_runner_prompt(runtime_state: dict, prompt: str) -> str:
    profile, messages = build_runner_messages(prompt)
    response_text = request_runner_response(
        runtime_state,
        messages,
        request_settings=build_runner_request_settings(profile, prompt),
    )
    sanitized_response_text = sanitize_runner_response_text(profile, response_text)
    if response_needs_retry(profile, prompt, sanitized_response_text):
        _, retry_messages = build_runner_messages(prompt, retry=True, previous_response=sanitized_response_text)
        retry_response_text = request_runner_response(
            runtime_state,
            retry_messages,
            request_settings=build_runner_request_settings(profile, prompt, retry=True),
        )
        retry_sanitized_response_text = sanitize_runner_response_text(profile, retry_response_text)
        if not response_needs_retry(profile, prompt, retry_sanitized_response_text):
            sanitized_response_text = retry_sanitized_response_text
        elif retry_sanitized_response_text:
            if profile in (PROMPT_PROFILE_INFO, PROMPT_PROFILE_WRITING):
                target_words = extract_requested_word_target(prompt)
                if target_words is not None:
                    first_gap = abs(target_words - count_response_words(sanitized_response_text))
                    retry_gap = abs(target_words - count_response_words(retry_sanitized_response_text))
                    if retry_gap <= first_gap:
                        sanitized_response_text = retry_sanitized_response_text
                elif count_response_words(retry_sanitized_response_text) >= count_response_words(sanitized_response_text):
                    sanitized_response_text = retry_sanitized_response_text
            else:
                sanitized_response_text = retry_sanitized_response_text

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


class TextServiceServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], config: dict) -> None:
        super().__init__(server_address, handler_class)
        self.config = config

    def build_health_payload(self) -> dict:
        runtime_state = build_runtime_state(self.config)
        return {
            "service": self.config["service_name"],
            "status": "ok",
            "enabled": self.config["enabled"],
            "host": self.config["host"],
            "port": self.config["port"],
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
        runtime_state = build_runtime_state(self.config)
        return {
            "service": self.config["service_name"],
            "status": "ok",
            "enabled": self.config["enabled"],
            "host": self.config["host"],
            "port": self.config["port"],
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
            "config_path": self.config["config_path"],
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
        try:
            payload = self.read_json_body()
            prompt = validate_prompt_payload(payload)
        except TextServiceRequestError as exc:
            runtime_state = build_runtime_state(self.server.config)
            self.send_json(
                exc.status_code,
                build_request_error_response(
                    service_name=self.server.config["service_name"],
                    runtime_state=runtime_state,
                    error_type=exc.error_type,
                    blocker=exc.blocker,
                    message=exc.message,
                ),
            )
            return

        runtime_state = build_runtime_state(self.server.config)
        if runtime_state["service_mode"] == "stub":
            self.send_json(
                HTTPStatus.OK,
                build_prompt_stub_response(
                    service_name=self.server.config["service_name"],
                    runtime_state=runtime_state,
                    prompt=prompt,
                ),
            )
            return

        if runtime_state["service_mode"] != "real_model_ready":
            self.send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                build_request_error_response(
                    service_name=self.server.config["service_name"],
                    runtime_state=runtime_state,
                    error_type="model_not_ready",
                    blocker=runtime_state["service_mode"],
                    message="Local text model is not ready.",
                ),
            )
            return

        try:
            response_text = post_runner_prompt(runtime_state, prompt)
        except TextServiceRequestError as exc:
            self.send_json(
                exc.status_code,
                build_request_error_response(
                    service_name=self.server.config["service_name"],
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
                service_name=self.server.config["service_name"],
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
