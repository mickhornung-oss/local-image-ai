from __future__ import annotations

import unittest

import python.text_chat_responses as text_chat_responses


class TextChatResponsesTests(unittest.TestCase):
    def test_build_slot_detail_response_preserves_slot_and_profile_state(self) -> None:
        payload = text_chat_responses.build_text_chat_slot_detail_response(
            slot={
                "slot_index": 2,
                "occupied": True,
                "title": "Projektchat",
                "summary": "Kurzstand",
                "message_count": 3,
                "messages": [{"role": "user"}],
            },
            profile_state={
                "profiles": [{"id": "standard"}, {"id": "multilingual"}],
                "current_profile_id": "multilingual",
                "switch_state": {"busy": False},
            },
        )

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["slot"]["slot_index"], 2)
        self.assertEqual(payload["slot"]["title"], "Projektchat")
        self.assertEqual(
            payload["model_profiles"], [{"id": "standard"}, {"id": "multilingual"}]
        )
        self.assertEqual(payload["current_model_profile_id"], "multilingual")
        self.assertEqual(payload["model_switch_state"], {"busy": False})

    def test_build_slot_detail_response_uses_stable_defaults_for_missing_data(
        self,
    ) -> None:
        payload = text_chat_responses.build_text_chat_slot_detail_response(
            slot=None,
            profile_state=None,
        )

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["slot"], {})
        self.assertEqual(payload["model_profiles"], [])
        self.assertIsNone(payload["current_model_profile_id"])
        self.assertIsNone(payload["model_switch_state"])

    def test_build_slot_detail_response_filters_invalid_profiles(self) -> None:
        payload = text_chat_responses.build_text_chat_slot_detail_response(
            slot={"slot_index": 1},
            profile_state={
                "profiles": [{"id": "standard"}, "invalid", 42],
                "current_profile_id": "standard",
            },
        )

        self.assertEqual(payload["slot"], {"slot_index": 1})
        self.assertEqual(payload["model_profiles"], [{"id": "standard"}])
        self.assertEqual(payload["current_model_profile_id"], "standard")


if __name__ == "__main__":
    unittest.main()
