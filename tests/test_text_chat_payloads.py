from __future__ import annotations

import unittest

import python.text_chat_payloads as text_chat_payloads


class TextChatPayloadsTests(unittest.TestCase):
    def test_build_active_chat_payload_applies_defaults_for_empty_slot(self) -> None:
        payload = text_chat_payloads.build_text_chat_active_chat_payload(
            2,
            {"occupied": False, "messages": None, "message_count": None},
            default_title="Chat 2",
            default_model_profile="standard",
        )

        self.assertEqual(payload["slot_index"], 2)
        self.assertFalse(payload["occupied"])
        self.assertEqual(payload["title"], "Chat 2")
        self.assertEqual(payload["model_profile"], "standard")
        self.assertEqual(payload["messages"], [])
        self.assertEqual(payload["message_count"], 0)
        self.assertIsNone(payload["summary"])

    def test_build_active_chat_payload_preserves_existing_metadata(self) -> None:
        payload = text_chat_payloads.build_text_chat_active_chat_payload(
            1,
            {
                "occupied": True,
                "title": "Projektchat",
                "summary": "Kurzstand",
                "language": "de",
                "model_profile": "rewrite",
                "model": "model.gguf",
                "created_at": "2026-04-04T10:00:00Z",
                "updated_at": "2026-04-04T10:01:00Z",
                "message_count": 2,
                "messages": [{"role": "user"}, {"role": "assistant"}],
                "last_assistant_message": "Antwort",
            },
            default_title="Chat 1",
            default_model_profile="standard",
        )

        self.assertTrue(payload["occupied"])
        self.assertEqual(payload["title"], "Projektchat")
        self.assertEqual(payload["summary"], "Kurzstand")
        self.assertEqual(payload["model_profile"], "rewrite")
        self.assertEqual(payload["message_count"], 2)
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["last_assistant_message"], "Antwort")

    def test_build_slot_overview_payload_handles_missing_preview(self) -> None:
        payload = text_chat_payloads.build_text_chat_slot_overview_payload(
            3,
            {
                "occupied": True,
                "title": "Chat Drei",
                "message_count": 1,
                "last_assistant_message": "Dies ist eine laengere Antwort mit mehreren Worten",
            },
            default_title="Chat 3",
            default_model_profile="standard",
            preview_limit=12,
        )

        self.assertEqual(payload["slot_index"], 3)
        self.assertEqual(payload["title"], "Chat Drei")
        self.assertEqual(payload["model_profile"], "standard")
        self.assertEqual(payload["message_count"], 1)
        self.assertEqual(payload["last_message_preview"], "Dies ist ei...")

    def test_build_slot_overview_payload_uses_defaults_for_empty_input(self) -> None:
        payload = text_chat_payloads.build_text_chat_slot_overview_payload(
            4,
            None,
            default_title="Chat 4",
            default_model_profile="standard",
            preview_limit=100,
        )

        self.assertFalse(payload["occupied"])
        self.assertEqual(payload["title"], "Chat 4")
        self.assertEqual(payload["model_profile"], "standard")
        self.assertEqual(payload["message_count"], 0)
        self.assertIsNone(payload["last_message_preview"])

    def test_build_overview_payload_maps_profile_state_and_slots(self) -> None:
        payload = text_chat_payloads.build_text_chat_overview_payload(
            slot_count=5,
            active_slot_index=1,
            active_chat={"slot_index": 1, "title": "Chat 1"},
            slots=[{"slot_index": 1, "title": "Chat 1"}, "ignore"],
            profile_state={
                "profiles": [{"id": "standard"}],
                "current_profile_id": "standard",
                "switch_state": {"busy": False},
            },
        )

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["slot_count"], 5)
        self.assertEqual(payload["active_slot_index"], 1)
        self.assertEqual(payload["current_model_profile_id"], "standard")
        self.assertEqual(payload["model_profiles"], [{"id": "standard"}])
        self.assertEqual(payload["slots"], [{"slot_index": 1, "title": "Chat 1"}])
        self.assertEqual(payload["active_chat"], {"slot_index": 1, "title": "Chat 1"})


if __name__ == "__main__":
    unittest.main()
