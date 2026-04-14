from __future__ import annotations

import re


DEFAULT_LONG_FORM_WORD_TARGET = 110
MAX_LONG_FORM_WORD_TARGET = 1400

PROMPT_PROFILE_IMAGE = "image_prompt_help"
PROMPT_PROFILE_REWRITE = "rewrite"
PROMPT_PROFILE_INFO = "info_text"
PROMPT_PROFILE_WRITING = "writing_task"
PROMPT_PROFILE_SHORT = "short_answer"

TEXT_WORK_MODE_WRITING = "writing"
TEXT_WORK_MODE_REWRITE = "rewrite"
TEXT_WORK_MODE_IMAGE = "image_prompt"


def build_word_target_window(word_target: int) -> tuple[int, int]:
    tolerance = max(8, int(word_target * 0.1))
    minimum_words = max(40, word_target - tolerance)
    maximum_words = word_target + tolerance
    return minimum_words, maximum_words


def extract_requested_word_bounds(prompt: str) -> tuple[int, int] | None:
    range_match = re.search(
        r"\b(?:zwischen|between)?\s*(\d{2,4})\s*(?:-|â€“|â€”|bis|to|and|und)\s*(\d{2,4})\s*(?:woerter|woertern|worte|worten|w\u00f6rter|w\u00f6rtern|words)\b",
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
    bounds = extract_requested_word_bounds(prompt)
    if bounds is None:
        return None
    lower_bound, upper_bound = bounds
    return int(round((lower_bound + upper_bound) / 2))


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


def infer_prompt_language(prompt: str) -> str | None:
    normalized = f" {prompt.lower()} "
    explicit_english_markers = (" in english ", " auf englisch ", " english ", " englisch ")
    explicit_spanish_markers = (" in spanish ", " auf spanisch ", " spanish ", " spanisch ", " espanol ", " espaÃ±ol ")
    explicit_french_markers = (" in french ", " auf franzoesisch ", " french ", " francais ", " franÃ§ais ", " franzoesisch ")
    if any(marker in normalized for marker in explicit_english_markers):
        return "en"
    if any(marker in normalized for marker in explicit_spanish_markers):
        return "es"
    if any(marker in normalized for marker in explicit_french_markers):
        return "fr"
    english_markers = (" the ", " and ", " with ", " into ", " rewrite ", " draft ", " words ")
    spanish_markers = (" el ", " la ", " los ", " las ", " con ", " para ", " reescribe ", " palabras ")
    french_markers = (" le ", " la ", " les ", " avec ", " pour ", " rÃ©Ã©cris ", " mots ")
    german_markers = (" der ", " die ", " das ", " und ", " mit ", " fuer ", " woerter ", " Ã¼berarbeite ")

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
    if language_code == "en":
        return "Antworte vollstaendig auf Englisch. Verwende kein Deutsch."
    if language_code == "es":
        return "Antworte vollstaendig auf Spanisch. Verwende kein Deutsch."
    if language_code == "fr":
        return "Antworte vollstaendig auf Franzoesisch. Verwende kein Deutsch."
    if language_code == "de":
        return "Antworte vollstaendig auf Deutsch."
    return None


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


def build_word_target_instruction(
    word_target: int | None,
    *,
    retry: bool = False,
    word_bounds: tuple[int, int] | None = None,
) -> str:
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
    return len(re.findall(r"[A-Za-z0-9\u00c0-\u024f\u00df]+(?:['-][A-Za-z0-9\u00c0-\u024f\u00df]+)*", text))


def calculate_word_bounds_distance(word_bounds: tuple[int, int] | None, actual_words: int) -> int:
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
    if word_bounds is None:
        return retry_words >= first_words
    first_distance = calculate_word_bounds_distance(word_bounds, first_words)
    retry_distance = calculate_word_bounds_distance(word_bounds, retry_words)
    return retry_distance <= first_distance


def classify_prompt_profile(prompt: str) -> str:
    normalized = prompt.lower()
    word_target = extract_requested_word_target(prompt)

    image_keywords = (
        "bildprompt",
        "prompt fuer ein bild",
        "prompt fÃƒÂ¼r ein bild",
        "prompt fuer ein foto",
        "prompt fÃƒÂ¼r ein foto",
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
        "kÃƒÂ¼rzer um",
        "schreibe eleganter",
        "schreibe fluessiger",
        "schreibe flÃƒÂ¼ssiger",
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
        "persÃƒÆ’Ã‚Â¶nlich",
    )
    info_keywords = (
        "infotext",
        "sachtext",
        "fachtext",
        "erklaertext",
        "erklÃƒÆ’Ã‚Â¤rtext",
        "erklaere",
        "erklÃƒÆ’Ã‚Â¤re",
        "erlaeutere",
        "erlÃƒÆ’Ã‚Â¤utere",
        "erklaer",
        "erklÃƒÆ’Ã‚Â¤r",
        "sachlich",
        "informativ",
        "fakten",
        "wissenswert",
        "ueberblick",
        "ÃƒÆ’Ã‚Â¼berblick",
    )
    has_text_over_topic = re.search(r"\btext\s+(?:ueber|ÃƒÆ’Ã‚Â¼ber)\b", normalized) is not None

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
    subject = prompt.strip()
    subject = re.sub(
        r"^(bitte\s+)?(erstelle|schreibe|mach)\s+(mir\s+)?(einen|einen kurzen|einen kompakten)?\s*(bildprompt|prompt)\s+(fuer|fÃƒÂ¼r|zu)\s+",
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
        r"^(ich\s+brauche\s+)?(hilfe\s+bei\s+einem\s+bildprompt|einen\s+bildprompt|einen\s+prompt)\s+(fuer|fÃƒÂ¼r|zu)\s+",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    subject = subject.strip(" .:-")
    return subject or prompt.strip()
