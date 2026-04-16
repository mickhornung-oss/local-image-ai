from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path


def text_chat_dir_access_state(db_path: Path) -> tuple[bool, str | None]:
    root = db_path.parent
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)
    if not root.is_dir():
        return False, "text_chat_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "text_chat_dir_not_accessible"
    return True, None


def text_chat_connection(db_path: Path) -> sqlite3.Connection:
    accessible, error = text_chat_dir_access_state(db_path)
    if not accessible:
        raise OSError(error or "text_chat_dir_not_accessible")
    connection = sqlite3.connect(db_path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_text_chat_store(db_path: Path, *, slot_count: int) -> None:
    with text_chat_connection(db_path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS text_chat_slots (
                slot_index INTEGER PRIMARY KEY,
                title TEXT,
                summary TEXT,
                language TEXT,
                model_profile TEXT,
                model TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS text_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_index INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS text_chat_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            )
            """)
        for slot_index in range(1, slot_count + 1):
            connection.execute(
                """
                INSERT OR IGNORE INTO text_chat_slots (
                    slot_index, title, summary, language, model, created_at, updated_at
                ) VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL)
                """,
                (slot_index,),
            )
        connection.execute("""
            INSERT OR IGNORE INTO text_chat_state (state_key, state_value)
            VALUES ('active_slot_index', '1')
            """)
        slot_columns = {
            str(row["name"]).strip().lower()
            for row in connection.execute(
                "PRAGMA table_info(text_chat_slots)"
            ).fetchall()
        }
        if "model_profile" not in slot_columns:
            connection.execute(
                "ALTER TABLE text_chat_slots ADD COLUMN model_profile TEXT"
            )


def normalize_text_chat_slot_index(value: object, *, slot_count: int) -> int:
    try:
        slot_index = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError("invalid_text_chat_slot")
    if slot_index < 1 or slot_index > slot_count:
        raise ValueError("invalid_text_chat_slot")
    return slot_index


def normalize_text_chat_title(
    value: object, *, max_length: int
) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "invalid_text_chat_title"
    normalized = re.sub(r"\s+", " ", value.strip())
    if not normalized:
        return None, "empty_text_chat_title"
    if len(normalized) > max_length:
        normalized = normalized[:max_length].rstrip()
    return normalized, None


def build_default_text_chat_title(slot_index: int) -> str:
    return f"Chat {slot_index}"


def excerpt_text(value: str, *, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 1)].rstrip()}â€¦"


def infer_text_chat_language_from_text(value: str) -> str:
    sample = f" {str(value or '').lower()} "
    german_score = 0
    english_score = 0
    german_tokens = (
        " der ",
        " die ",
        " das ",
        " und ",
        " nicht ",
        " bitte ",
        " fuer ",
        " fÃ¼r ",
        " mit ",
        " ich ",
    )
    english_tokens = (
        " the ",
        " and ",
        " please ",
        " with ",
        " this ",
        " that ",
        " write ",
        " prompt ",
        " image ",
    )
    if re.search(r"[Ã¤Ã¶Ã¼ÃŸ]", sample):
        german_score += 2
    german_score += sum(1 for token in german_tokens if token in sample)
    english_score += sum(1 for token in english_tokens if token in sample)
    return "en" if english_score > german_score else "de"


def get_active_text_chat_slot_index(db_path: Path, *, slot_count: int) -> int:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    with text_chat_connection(db_path) as connection:
        row = connection.execute(
            "SELECT state_value FROM text_chat_state WHERE state_key = 'active_slot_index'"
        ).fetchone()
    if row is None:
        return 1
    try:
        return normalize_text_chat_slot_index(row["state_value"], slot_count=slot_count)
    except ValueError:
        return 1


def set_active_text_chat_slot_index(
    db_path: Path, slot_index: int, *, slot_count: int
) -> None:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    with text_chat_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO text_chat_state (state_key, state_value)
            VALUES ('active_slot_index', ?)
            ON CONFLICT(state_key) DO UPDATE SET state_value=excluded.state_value
            """,
            (str(slot_index),),
        )


def list_text_chat_messages(
    db_path: Path,
    slot_index: int,
    *,
    slot_count: int,
    limit: int,
) -> list[dict]:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    with text_chat_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM text_chat_messages
            WHERE slot_index = ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (slot_index, limit),
        ).fetchall()
    return [
        {
            "id": int(row["id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def build_text_chat_summary(
    messages: list[dict],
    *,
    recent_messages_count: int,
    summary_max_characters: int,
) -> str | None:
    if len(messages) <= recent_messages_count:
        return None
    older_messages = messages[:-recent_messages_count]
    if not older_messages:
        return None
    lines: list[str] = []
    current_user: str | None = None
    for message in older_messages:
        role = str(message.get("role") or "").strip().lower()
        content = excerpt_text(str(message.get("content") or ""), limit=140)
        if not content:
            continue
        if role == "user":
            current_user = content
            continue
        if role == "assistant":
            if current_user:
                lines.append(f"- Nutzer: {current_user} | KI: {content}")
                current_user = None
            else:
                lines.append(f"- KI: {content}")
    if current_user:
        lines.append(f"- Nutzer: {current_user}")
    if not lines:
        return None
    summary = "\n".join(lines[-4:])
    if len(summary) > summary_max_characters:
        summary = summary[:summary_max_characters].rstrip()
    return summary


def update_text_chat_slot_metadata(
    db_path: Path,
    slot_index: int,
    *,
    slot_count: int,
    title: str | None = None,
    summary: str | None = None,
    language: str | None = None,
    model_profile: str | None = None,
    model: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
) -> None:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    assignments: list[str] = []
    values: list[object] = []
    for field_name, field_value in (
        ("title", title),
        ("summary", summary),
        ("language", language),
        ("model_profile", model_profile),
        ("model", model),
        ("created_at", created_at),
        ("updated_at", updated_at),
    ):
        if field_value is not None:
            assignments.append(f"{field_name} = ?")
            values.append(field_value)
    if not assignments:
        return
    values.append(slot_index)
    with text_chat_connection(db_path) as connection:
        connection.execute(
            f"UPDATE text_chat_slots SET {', '.join(assignments)} WHERE slot_index = ?",
            values,
        )


def clear_text_chat_slot(db_path: Path, slot_index: int, *, slot_count: int) -> None:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    with text_chat_connection(db_path) as connection:
        connection.execute(
            "DELETE FROM text_chat_messages WHERE slot_index = ?", (slot_index,)
        )
        connection.execute(
            """
            UPDATE text_chat_slots
            SET title = NULL, summary = NULL, language = NULL, model_profile = NULL, model = NULL, created_at = NULL, updated_at = NULL
            WHERE slot_index = ?
            """,
            (slot_index,),
        )


def create_text_chat_in_slot(
    db_path: Path,
    slot_index: int,
    *,
    slot_count: int,
    title: str | None,
    now_iso: str,
    default_model_profile: str,
    default_model_label: str | None,
    default_visible_messages_limit: int,
) -> dict:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    normalized_title = title or build_default_text_chat_title(slot_index)
    clear_text_chat_slot(db_path, slot_index, slot_count=slot_count)
    update_text_chat_slot_metadata(
        db_path,
        slot_index,
        slot_count=slot_count,
        title=normalized_title,
        summary=None,
        language="de",
        model_profile=default_model_profile,
        model=default_model_label,
        created_at=now_iso,
        updated_at=now_iso,
    )
    set_active_text_chat_slot_index(db_path, slot_index, slot_count=slot_count)
    return get_text_chat_slot(
        db_path,
        slot_index,
        slot_count=slot_count,
        default_model_profile=default_model_profile,
        visible_messages_limit=default_visible_messages_limit,
    )


def append_text_chat_message(
    db_path: Path,
    slot_index: int,
    *,
    slot_count: int,
    role: str,
    content: str,
    now_iso: str,
) -> None:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    with text_chat_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO text_chat_messages (slot_index, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (slot_index, role, content, now_iso),
        )


def get_text_chat_slot(
    db_path: Path,
    slot_index: int,
    *,
    slot_count: int,
    default_model_profile: str,
    visible_messages_limit: int,
) -> dict:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    with text_chat_connection(db_path) as connection:
        slot_row = connection.execute(
            """
            SELECT slot_index, title, summary, language, model_profile, model, created_at, updated_at
            FROM text_chat_slots
            WHERE slot_index = ?
            """,
            (slot_index,),
        ).fetchone()
    messages = list_text_chat_messages(
        db_path,
        slot_index,
        slot_count=slot_count,
        limit=visible_messages_limit,
    )
    occupied = bool(
        slot_row
        and isinstance(slot_row["updated_at"], str)
        and str(slot_row["updated_at"]).strip()
    )
    last_assistant_message = next(
        (
            message["content"]
            for message in reversed(messages)
            if message["role"] == "assistant" and message["content"].strip()
        ),
        None,
    )
    return {
        "slot_index": slot_index,
        "occupied": occupied,
        "title": (
            str(slot_row["title"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["title"], str)
            and str(slot_row["title"]).strip()
            else build_default_text_chat_title(slot_index)
        ),
        "summary": (
            str(slot_row["summary"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["summary"], str)
            and str(slot_row["summary"]).strip()
            else None
        ),
        "language": (
            str(slot_row["language"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["language"], str)
            and str(slot_row["language"]).strip()
            else None
        ),
        "model_profile": (
            str(slot_row["model_profile"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["model_profile"], str)
            and str(slot_row["model_profile"]).strip()
            else default_model_profile
        ),
        "model": (
            str(slot_row["model"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["model"], str)
            and str(slot_row["model"]).strip()
            else None
        ),
        "created_at": (
            str(slot_row["created_at"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["created_at"], str)
            and str(slot_row["created_at"]).strip()
            else None
        ),
        "updated_at": (
            str(slot_row["updated_at"]).strip()
            if occupied
            and slot_row
            and isinstance(slot_row["updated_at"], str)
            and str(slot_row["updated_at"]).strip()
            else None
        ),
        "message_count": len(messages),
        "messages": messages,
        "last_assistant_message": last_assistant_message,
    }


def list_text_chat_slots(
    db_path: Path,
    *,
    slot_count: int,
    default_model_profile: str,
    visible_messages_limit: int,
) -> list[dict]:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    slots: list[dict] = []
    for slot_index in range(1, slot_count + 1):
        slot = get_text_chat_slot(
            db_path,
            slot_index,
            slot_count=slot_count,
            default_model_profile=default_model_profile,
            visible_messages_limit=visible_messages_limit,
        )
        slots.append(
            {
                "slot_index": slot_index,
                "occupied": slot["occupied"],
                "title": slot["title"],
                "summary": slot["summary"],
                "language": slot["language"],
                "model_profile": slot["model_profile"],
                "model": slot["model"],
                "created_at": slot["created_at"],
                "updated_at": slot["updated_at"],
                "message_count": slot["message_count"],
                "last_message_preview": (
                    excerpt_text(slot["last_assistant_message"] or "", limit=100)
                    if slot["last_assistant_message"]
                    else None
                ),
            }
        )
    return slots


def create_text_chat_in_first_empty_slot(
    db_path: Path,
    *,
    slot_count: int,
    title: str | None,
    now_iso: str,
    default_model_profile: str,
    default_model_label: str | None,
    default_visible_messages_limit: int,
) -> dict | None:
    ensure_text_chat_store(db_path, slot_count=slot_count)
    for slot in list_text_chat_slots(
        db_path,
        slot_count=slot_count,
        default_model_profile=default_model_profile,
        visible_messages_limit=default_visible_messages_limit,
    ):
        if slot["occupied"] is not True:
            return create_text_chat_in_slot(
                db_path,
                slot["slot_index"],
                slot_count=slot_count,
                title=title,
                now_iso=now_iso,
                default_model_profile=default_model_profile,
                default_model_label=default_model_label,
                default_visible_messages_limit=default_visible_messages_limit,
            )
    return None
