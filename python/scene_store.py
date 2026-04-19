from __future__ import annotations

import os
import re
import sqlite3
import uuid
from pathlib import Path


def scene_dir_access_state(db_path: Path) -> tuple[bool, str | None]:
    root = db_path.parent
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, str(exc)
    if not root.is_dir():
        return False, "scene_dir_not_directory"
    if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
        return False, "scene_dir_not_accessible"
    return True, None


def scene_connection(db_path: Path) -> sqlite3.Connection:
    accessible, error = scene_dir_access_state(db_path)
    if not accessible:
        raise OSError(error or "scene_dir_not_accessible")
    connection = sqlite3.connect(db_path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_scene_store(db_path: Path) -> None:
    with scene_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                last_prompt TEXT,
                last_negative_prompt TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scene_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scene_id TEXT NOT NULL,
                result_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scene_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT NOT NULL
            )
            """
        )


def normalize_scene_title(
    value: object, *, max_length: int = 120
) -> tuple[str | None, str | None]:
    if value is None:
        return None, "missing_scene_title"
    if not isinstance(value, str):
        return None, "invalid_scene_title"
    normalized = re.sub(r"\s+", " ", value.strip())
    if not normalized:
        return None, "empty_scene_title"
    if len(normalized) > max_length:
        normalized = normalized[:max_length].rstrip()
    return normalized, None


def _build_scene_dict(row: sqlite3.Row) -> dict:
    return {
        "id": str(row["id"]),
        "title": str(row["title"]),
        "body": str(row["body"] or ""),
        "last_prompt": str(row["last_prompt"])
        if row["last_prompt"] is not None
        else None,
        "last_negative_prompt": str(row["last_negative_prompt"])
        if row["last_negative_prompt"] is not None
        else None,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def create_scene(db_path: Path, *, title: str, body: str = "", now_iso: str) -> dict:
    ensure_scene_store(db_path)
    scene_id = str(uuid.uuid4())
    with scene_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO scenes (id, title, body, last_prompt, last_negative_prompt, created_at, updated_at)
            VALUES (?, ?, ?, NULL, NULL, ?, ?)
            """,
            (scene_id, title, body, now_iso, now_iso),
        )
    result = get_scene(db_path, scene_id)
    assert result is not None
    return result


def get_scene(db_path: Path, scene_id: str) -> dict | None:
    ensure_scene_store(db_path)
    with scene_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, title, body, last_prompt, last_negative_prompt, created_at, updated_at
            FROM scenes WHERE id = ?
            """,
            (scene_id,),
        ).fetchone()
    if row is None:
        return None
    return _build_scene_dict(row)


def list_scenes(db_path: Path) -> list[dict]:
    ensure_scene_store(db_path)
    with scene_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, body, last_prompt, last_negative_prompt, created_at, updated_at
            FROM scenes ORDER BY updated_at DESC, created_at DESC
            """
        ).fetchall()
    return [_build_scene_dict(row) for row in rows]


def update_scene(
    db_path: Path,
    scene_id: str,
    *,
    title: str | None = None,
    body: str | None = None,
    last_prompt: str | None = None,
    last_negative_prompt: str | None = None,
    now_iso: str,
) -> dict | None:
    ensure_scene_store(db_path)
    assignments: list[str] = ["updated_at = ?"]
    values: list[object] = [now_iso]
    if title is not None:
        assignments.append("title = ?")
        values.append(title)
    if body is not None:
        assignments.append("body = ?")
        values.append(body)
    if last_prompt is not None:
        assignments.append("last_prompt = ?")
        values.append(last_prompt)
    if last_negative_prompt is not None:
        assignments.append("last_negative_prompt = ?")
        values.append(last_negative_prompt)
    values.append(scene_id)
    with scene_connection(db_path) as connection:
        connection.execute(
            f"UPDATE scenes SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
    return get_scene(db_path, scene_id)


def delete_scene(db_path: Path, scene_id: str) -> bool:
    ensure_scene_store(db_path)
    with scene_connection(db_path) as connection:
        cursor = connection.execute("DELETE FROM scenes WHERE id = ?", (scene_id,))
        connection.execute("DELETE FROM scene_results WHERE scene_id = ?", (scene_id,))
    deleted = (cursor.rowcount or 0) > 0
    if deleted:
        active_id = get_active_scene_id(db_path)
        if active_id == scene_id:
            set_active_scene_id(db_path, None)
    return deleted


def get_active_scene_id(db_path: Path) -> str | None:
    ensure_scene_store(db_path)
    with scene_connection(db_path) as connection:
        row = connection.execute(
            "SELECT state_value FROM scene_state WHERE state_key = 'active_scene_id'"
        ).fetchone()
    if row is None:
        return None
    value = str(row["state_value"]).strip()
    return value if value else None


def set_active_scene_id(db_path: Path, scene_id: str | None) -> None:
    ensure_scene_store(db_path)
    value = str(scene_id).strip() if scene_id is not None else ""
    with scene_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO scene_state (state_key, state_value)
            VALUES ('active_scene_id', ?)
            ON CONFLICT(state_key) DO UPDATE SET state_value=excluded.state_value
            """,
            (value,),
        )


def add_scene_result(
    db_path: Path, scene_id: str, result_id: str, *, now_iso: str
) -> None:
    ensure_scene_store(db_path)
    with scene_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO scene_results (scene_id, result_id, created_at) VALUES (?, ?, ?)",
            (scene_id, result_id, now_iso),
        )


def list_scene_results(db_path: Path, scene_id: str) -> list[str]:
    entries = list_scene_result_entries(db_path, scene_id)
    return [str(entry["result_id"]) for entry in entries]


def list_scene_result_entries(db_path: Path, scene_id: str) -> list[dict]:
    ensure_scene_store(db_path)
    with scene_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT result_id, created_at FROM scene_results WHERE scene_id = ? ORDER BY created_at DESC, id DESC",
            (scene_id,),
        ).fetchall()
    return [
        {
            "result_id": str(row["result_id"]),
            "linked_at": str(row["created_at"]),
        }
        for row in rows
    ]


def build_scene_overview(db_path: Path) -> dict:
    ensure_scene_store(db_path)
    scenes = list_scenes(db_path)
    active_id = get_active_scene_id(db_path)
    active_scene = None
    if active_id:
        active_scene = get_scene(db_path, active_id)
        if active_scene is None:
            active_id = None
    return {
        "scenes": scenes,
        "active_scene_id": active_id,
        "active_scene": active_scene,
    }
