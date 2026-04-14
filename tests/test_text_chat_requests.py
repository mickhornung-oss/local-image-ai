from __future__ import annotations

import unittest

import python.text_chat_requests as text_chat_requests


def _slot_index_normalizer(value: object) -> int:
    slot_index = int(str(value).strip())
    if slot_index < 1 or slot_index > 5:
        raise ValueError("invalid_text_chat_slot")
    return slot_index


def _title_normalizer(value: object) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "invalid_text_chat_title"
    normalized = " ".join(value.split())
    if not normalized:
        return None, "empty_text_chat_title"
    return normalized, None


class TextChatRequestsTests(unittest.TestCase):
    def test_resolve_slot_request_path_parses_detail_and_action(self) -> None:
        self.assertEqual(
            text_chat_requests.resolve_text_chat_slot_request_path(
                "/text-service/chats/slot/3",
                slots_path="/text-service/chats",
                slot_index_normalizer=_slot_index_normalizer,
            ),
            (3, None),
        )
        self.assertEqual(
            text_chat_requests.resolve_text_chat_slot_request_path(
                "/text-service/chats/slot/4/rename",
                slots_path="/text-service/chats",
                slot_index_normalizer=_slot_index_normalizer,
            ),
            (4, "rename"),
        )

    def test_resolve_slot_request_path_rejects_invalid_paths(self) -> None:
        self.assertIsNone(
            text_chat_requests.resolve_text_chat_slot_request_path(
                "/text-service/chats/slot/0",
                slots_path="/text-service/chats",
                slot_index_normalizer=_slot_index_normalizer,
            )
        )
        self.assertIsNone(
            text_chat_requests.resolve_text_chat_slot_request_path(
                "/text-service/chats/slot/2/rename/extra",
                slots_path="/text-service/chats",
                slot_index_normalizer=_slot_index_normalizer,
            )
        )

    def test_normalize_slot_action_accepts_known_actions_only(self) -> None:
        self.assertEqual(text_chat_requests.normalize_text_chat_slot_action(" rename "), "rename")
        self.assertIsNone(text_chat_requests.normalize_text_chat_slot_action("unknown"))
        self.assertIsNone(text_chat_requests.normalize_text_chat_slot_action(None))

    def test_payload_coercion_handles_optional_and_required_payloads(self) -> None:
        self.assertEqual(text_chat_requests.coerce_optional_text_chat_payload(None), ({}, None))
        self.assertEqual(
            text_chat_requests.coerce_optional_text_chat_payload({"title": "Chat"}),
            ({"title": "Chat"}, None),
        )
        self.assertEqual(
            text_chat_requests.coerce_required_text_chat_payload(None),
            (None, "invalid_json"),
        )
        self.assertEqual(
            text_chat_requests.coerce_required_text_chat_payload({"title": "Chat"}),
            ({"title": "Chat"}, None),
        )

    def test_title_normalization_variants_preserve_existing_rules(self) -> None:
        self.assertEqual(
            text_chat_requests.normalize_create_text_chat_title(
                "",
                title_normalizer=_title_normalizer,
            ),
            (None, "empty_text_chat_title"),
        )
        self.assertEqual(
            text_chat_requests.normalize_required_text_chat_title(
                None,
                title_normalizer=_title_normalizer,
            ),
            (None, "invalid_text_chat_title"),
        )
        self.assertEqual(
            text_chat_requests.normalize_optional_text_chat_title(
                "",
                title_normalizer=_title_normalizer,
            ),
            (None, None),
        )
        self.assertEqual(
            text_chat_requests.normalize_optional_text_chat_title(
                " Projekt Chat ",
                title_normalizer=_title_normalizer,
            ),
            ("Projekt Chat", None),
        )


if __name__ == "__main__":
    unittest.main()
