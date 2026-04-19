from __future__ import annotations

from pathlib import Path

import pytest

try:
    import scene_store
except ModuleNotFoundError:
    from python import scene_store


NOW_ISO = "2026-04-18T12:00:00+00:00"
LATER_ISO = "2026-04-18T13:00:00+00:00"


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    return tmp_path / "scenes.sqlite3"


def test_ensure_scene_store_creates_tables(db: Path) -> None:
    scene_store.ensure_scene_store(db)
    assert db.exists()


def test_create_and_get_scene(db: Path) -> None:
    created = scene_store.create_scene(
        db, title="Kapitel 1", body="Es war einmal.", now_iso=NOW_ISO
    )
    assert created["title"] == "Kapitel 1"
    assert created["body"] == "Es war einmal."
    assert created["id"]
    assert created["created_at"] == NOW_ISO

    fetched = scene_store.get_scene(db, created["id"])
    assert fetched is not None
    assert fetched["title"] == "Kapitel 1"
    assert fetched["body"] == "Es war einmal."


def test_get_scene_returns_none_for_missing(db: Path) -> None:
    scene_store.ensure_scene_store(db)
    assert scene_store.get_scene(db, "nonexistent-id") is None


def test_list_scenes_empty(db: Path) -> None:
    result = scene_store.list_scenes(db)
    assert result == []


def test_list_scenes_multiple(db: Path) -> None:
    scene_store.create_scene(db, title="Szene A", now_iso=NOW_ISO)
    scene_store.create_scene(db, title="Szene B", now_iso=LATER_ISO)
    scenes = scene_store.list_scenes(db)
    assert len(scenes) == 2
    titles = {s["title"] for s in scenes}
    assert "Szene A" in titles
    assert "Szene B" in titles


def test_update_scene_title(db: Path) -> None:
    created = scene_store.create_scene(db, title="Alt", now_iso=NOW_ISO)
    updated = scene_store.update_scene(
        db, created["id"], title="Neu", now_iso=LATER_ISO
    )
    assert updated is not None
    assert updated["title"] == "Neu"
    assert updated["updated_at"] == LATER_ISO


def test_update_scene_body(db: Path) -> None:
    created = scene_store.create_scene(db, title="T", body="Original", now_iso=NOW_ISO)
    updated = scene_store.update_scene(
        db, created["id"], body="Geaendert", now_iso=LATER_ISO
    )
    assert updated is not None
    assert updated["body"] == "Geaendert"


def test_update_scene_last_prompt(db: Path) -> None:
    created = scene_store.create_scene(db, title="T", now_iso=NOW_ISO)
    updated = scene_store.update_scene(
        db,
        created["id"],
        last_prompt="cinematic portrait",
        last_negative_prompt="blurry",
        now_iso=LATER_ISO,
    )
    assert updated is not None
    assert updated["last_prompt"] == "cinematic portrait"
    assert updated["last_negative_prompt"] == "blurry"


def test_update_nonexistent_scene(db: Path) -> None:
    result = scene_store.update_scene(db, "missing", title="X", now_iso=NOW_ISO)
    assert result is None


def test_delete_scene(db: Path) -> None:
    created = scene_store.create_scene(db, title="ToDelete", now_iso=NOW_ISO)
    deleted = scene_store.delete_scene(db, created["id"])
    assert deleted is True
    assert scene_store.get_scene(db, created["id"]) is None


def test_delete_nonexistent_scene(db: Path) -> None:
    scene_store.ensure_scene_store(db)
    deleted = scene_store.delete_scene(db, "missing")
    assert deleted is False


def test_active_scene_id_none_initially(db: Path) -> None:
    assert scene_store.get_active_scene_id(db) is None


def test_set_and_get_active_scene_id(db: Path) -> None:
    created = scene_store.create_scene(db, title="Active", now_iso=NOW_ISO)
    scene_store.set_active_scene_id(db, created["id"])
    assert scene_store.get_active_scene_id(db) == created["id"]


def test_set_active_scene_id_none(db: Path) -> None:
    created = scene_store.create_scene(db, title="X", now_iso=NOW_ISO)
    scene_store.set_active_scene_id(db, created["id"])
    scene_store.set_active_scene_id(db, None)
    assert scene_store.get_active_scene_id(db) is None


def test_delete_active_scene_clears_active(db: Path) -> None:
    created = scene_store.create_scene(db, title="Active", now_iso=NOW_ISO)
    scene_store.set_active_scene_id(db, created["id"])
    scene_store.delete_scene(db, created["id"])
    assert scene_store.get_active_scene_id(db) is None


def test_add_and_list_scene_results(db: Path) -> None:
    created = scene_store.create_scene(db, title="S", now_iso=NOW_ISO)
    scene_store.add_scene_result(db, created["id"], "result-abc", now_iso=NOW_ISO)
    scene_store.add_scene_result(db, created["id"], "result-def", now_iso=LATER_ISO)
    results = scene_store.list_scene_results(db, created["id"])
    assert len(results) == 2
    assert "result-abc" in results
    assert "result-def" in results


def test_list_scene_result_entries_include_link_timestamp(db: Path) -> None:
    created = scene_store.create_scene(db, title="S", now_iso=NOW_ISO)
    scene_store.add_scene_result(db, created["id"], "result-abc", now_iso=NOW_ISO)
    scene_store.add_scene_result(db, created["id"], "result-def", now_iso=LATER_ISO)
    entries = scene_store.list_scene_result_entries(db, created["id"])
    assert len(entries) == 2
    assert entries[0]["result_id"] == "result-def"
    assert entries[0]["linked_at"] == LATER_ISO
    assert entries[1]["result_id"] == "result-abc"
    assert entries[1]["linked_at"] == NOW_ISO


def test_list_scene_results_empty(db: Path) -> None:
    created = scene_store.create_scene(db, title="S", now_iso=NOW_ISO)
    assert scene_store.list_scene_results(db, created["id"]) == []


def test_delete_scene_removes_results(db: Path) -> None:
    created = scene_store.create_scene(db, title="S", now_iso=NOW_ISO)
    scene_store.add_scene_result(db, created["id"], "result-xyz", now_iso=NOW_ISO)
    scene_store.delete_scene(db, created["id"])
    assert scene_store.list_scene_results(db, created["id"]) == []


def test_build_scene_overview_empty(db: Path) -> None:
    overview = scene_store.build_scene_overview(db)
    assert overview["scenes"] == []
    assert overview["active_scene_id"] is None
    assert overview["active_scene"] is None


def test_build_scene_overview_with_active(db: Path) -> None:
    created = scene_store.create_scene(db, title="Main", body="Text", now_iso=NOW_ISO)
    scene_store.set_active_scene_id(db, created["id"])
    overview = scene_store.build_scene_overview(db)
    assert overview["active_scene_id"] == created["id"]
    assert overview["active_scene"] is not None
    assert overview["active_scene"]["title"] == "Main"


def test_normalize_scene_title_valid(db: Path) -> None:
    title, error = scene_store.normalize_scene_title("  Meine Szene  ")
    assert title == "Meine Szene"
    assert error is None


def test_normalize_scene_title_truncates(db: Path) -> None:
    long_title = "A" * 200
    title, error = scene_store.normalize_scene_title(long_title)
    assert title is not None
    assert len(title) <= 120
    assert error is None


def test_normalize_scene_title_empty_returns_error(db: Path) -> None:
    title, error = scene_store.normalize_scene_title("   ")
    assert title is None
    assert error == "empty_scene_title"


def test_normalize_scene_title_none_returns_error(db: Path) -> None:
    title, error = scene_store.normalize_scene_title(None)
    assert title is None
    assert error == "missing_scene_title"
