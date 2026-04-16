from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import python.text_chat_store as text_chat_store


class TextChatStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "text_chats.sqlite3"
        self.slot_count = 5
        self.default_profile = "standard"
        self.visible_messages_limit = 80

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_ensure_store_initializes_slots_and_default_active_slot(self) -> None:
        text_chat_store.ensure_text_chat_store(self.db_path, slot_count=self.slot_count)

        self.assertTrue(self.db_path.is_file())
        self.assertEqual(
            text_chat_store.get_active_text_chat_slot_index(
                self.db_path, slot_count=self.slot_count
            ),
            1,
        )

        slots = text_chat_store.list_text_chat_slots(
            self.db_path,
            slot_count=self.slot_count,
            default_model_profile=self.default_profile,
            visible_messages_limit=self.visible_messages_limit,
        )
        self.assertEqual(len(slots), self.slot_count)
        self.assertFalse(any(slot["occupied"] for slot in slots))

    def test_slot_index_and_title_normalization(self) -> None:
        self.assertEqual(
            text_chat_store.normalize_text_chat_slot_index(
                " 2 ", slot_count=self.slot_count
            ),
            2,
        )
        with self.assertRaises(ValueError):
            text_chat_store.normalize_text_chat_slot_index(
                "0", slot_count=self.slot_count
            )

        normalized, error = text_chat_store.normalize_text_chat_title(
            "  Hello   world  ", max_length=10
        )
        self.assertEqual(normalized, "Hello worl")
        self.assertIsNone(error)

        normalized, error = text_chat_store.normalize_text_chat_title(
            "   ", max_length=10
        )
        self.assertIsNone(normalized)
        self.assertEqual(error, "empty_text_chat_title")

    def test_create_append_and_load_chat_slot(self) -> None:
        created = text_chat_store.create_text_chat_in_slot(
            self.db_path,
            2,
            slot_count=self.slot_count,
            title="Projektplanung",
            now_iso="2026-04-04T10:00:00Z",
            default_model_profile=self.default_profile,
            default_model_label="model.gguf",
            default_visible_messages_limit=self.visible_messages_limit,
        )
        self.assertTrue(created["occupied"])
        self.assertEqual(created["slot_index"], 2)
        self.assertEqual(created["title"], "Projektplanung")
        self.assertEqual(
            text_chat_store.get_active_text_chat_slot_index(
                self.db_path, slot_count=self.slot_count
            ),
            2,
        )

        text_chat_store.append_text_chat_message(
            self.db_path,
            2,
            slot_count=self.slot_count,
            role="user",
            content="Bitte fasse das zusammen.",
            now_iso="2026-04-04T10:01:00Z",
        )
        text_chat_store.append_text_chat_message(
            self.db_path,
            2,
            slot_count=self.slot_count,
            role="assistant",
            content="Hier ist die Zusammenfassung.",
            now_iso="2026-04-04T10:01:05Z",
        )

        slot = text_chat_store.get_text_chat_slot(
            self.db_path,
            2,
            slot_count=self.slot_count,
            default_model_profile=self.default_profile,
            visible_messages_limit=self.visible_messages_limit,
        )
        self.assertEqual(slot["message_count"], 2)
        self.assertEqual(slot["messages"][0]["role"], "user")
        self.assertEqual(
            slot["last_assistant_message"], "Hier ist die Zusammenfassung."
        )

    def test_create_in_first_empty_slot_uses_first_free_slot(self) -> None:
        text_chat_store.create_text_chat_in_slot(
            self.db_path,
            1,
            slot_count=self.slot_count,
            title="Chat Eins",
            now_iso="2026-04-04T10:00:00Z",
            default_model_profile=self.default_profile,
            default_model_label="model.gguf",
            default_visible_messages_limit=self.visible_messages_limit,
        )
        created = text_chat_store.create_text_chat_in_first_empty_slot(
            self.db_path,
            slot_count=self.slot_count,
            title="Naechster Chat",
            now_iso="2026-04-04T10:02:00Z",
            default_model_profile=self.default_profile,
            default_model_label="model.gguf",
            default_visible_messages_limit=self.visible_messages_limit,
        )

        self.assertIsNotNone(created)
        assert created is not None
        self.assertEqual(created["slot_index"], 2)
        self.assertEqual(created["title"], "Naechster Chat")

    def test_clear_slot_removes_messages_and_metadata(self) -> None:
        text_chat_store.create_text_chat_in_slot(
            self.db_path,
            3,
            slot_count=self.slot_count,
            title="Temporar",
            now_iso="2026-04-04T10:00:00Z",
            default_model_profile=self.default_profile,
            default_model_label="model.gguf",
            default_visible_messages_limit=self.visible_messages_limit,
        )
        text_chat_store.append_text_chat_message(
            self.db_path,
            3,
            slot_count=self.slot_count,
            role="assistant",
            content="Antwort",
            now_iso="2026-04-04T10:00:05Z",
        )

        text_chat_store.clear_text_chat_slot(
            self.db_path, 3, slot_count=self.slot_count
        )

        slot = text_chat_store.get_text_chat_slot(
            self.db_path,
            3,
            slot_count=self.slot_count,
            default_model_profile=self.default_profile,
            visible_messages_limit=self.visible_messages_limit,
        )
        self.assertFalse(slot["occupied"])
        self.assertEqual(slot["message_count"], 0)
        self.assertEqual(slot["title"], "Chat 3")

    def test_summary_returns_none_for_short_history_and_text_for_longer_history(
        self,
    ) -> None:
        short_summary = text_chat_store.build_text_chat_summary(
            [{"role": "user", "content": "Hallo"}],
            recent_messages_count=6,
            summary_max_characters=900,
        )
        self.assertIsNone(short_summary)

        messages = [
            {"role": "user", "content": "Erste Frage"},
            {"role": "assistant", "content": "Erste Antwort"},
            {"role": "user", "content": "Zweite Frage"},
            {"role": "assistant", "content": "Zweite Antwort"},
            {"role": "user", "content": "Dritte Frage"},
            {"role": "assistant", "content": "Dritte Antwort"},
            {"role": "user", "content": "Vierte Frage"},
        ]
        summary = text_chat_store.build_text_chat_summary(
            messages,
            recent_messages_count=2,
            summary_max_characters=900,
        )
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertIn("Nutzer", summary)


if __name__ == "__main__":
    unittest.main()
