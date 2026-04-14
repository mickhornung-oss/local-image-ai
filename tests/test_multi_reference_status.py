from __future__ import annotations

from http import HTTPStatus
import unittest

import python.multi_reference_status as multi_reference_status


class MultiReferenceStatusTests(unittest.TestCase):
    def test_build_status_payload_populates_slots_and_ready_flag(self) -> None:
        payload = multi_reference_status.build_multi_reference_status_payload(
            [
                {"slot_index": 1, "image_id": "img-1"},
                {"slot_index": 3, "image_id": "img-3"},
            ],
            max_slots=4,
        )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["max_slots"], 4)
        self.assertEqual(payload["reference_count"], 2)
        self.assertTrue(payload["multi_reference_ready"])
        self.assertEqual(payload["slots"][0]["slot_index"], 1)
        self.assertTrue(payload["slots"][0]["occupied"])
        self.assertEqual(payload["slots"][1]["slot_index"], 2)
        self.assertFalse(payload["slots"][1]["occupied"])

    def test_build_status_payload_filters_invalid_items_and_defaults_to_not_ready(self) -> None:
        payload = multi_reference_status.build_multi_reference_status_payload(
            [
                {"slot_index": "invalid", "image_id": "img-a"},
                {"image_id": "img-b"},
                "ignore",
            ],
            max_slots=3,
        )

        self.assertEqual(payload["reference_count"], 0)
        self.assertFalse(payload["multi_reference_ready"])
        self.assertEqual(len(payload["slots"]), 3)
        self.assertFalse(any(slot["occupied"] for slot in payload["slots"]))

    def test_find_first_free_slot_uses_status_payload(self) -> None:
        slot_index = multi_reference_status.find_first_free_multi_reference_slot(
            {
                "slots": [
                    {"slot_index": 1, "occupied": True},
                    {"slot_index": 2, "occupied": False},
                    {"slot_index": 3, "occupied": True},
                ]
            }
        )
        self.assertEqual(slot_index, 2)

    def test_resolve_readiness_http_status_returns_ok_or_resolved_error(self) -> None:
        self.assertEqual(
            multi_reference_status.resolve_multi_reference_readiness_http_status(
                {"ok": True},
                status_code_resolver=lambda **kwargs: HTTPStatus.CONFLICT,
            ),
            HTTPStatus.OK,
        )
        self.assertEqual(
            multi_reference_status.resolve_multi_reference_readiness_http_status(
                {"ok": False, "error_type": "invalid_request", "blocker": "insufficient_multi_reference_images"},
                status_code_resolver=lambda **kwargs: HTTPStatus.CONFLICT,
            ),
            HTTPStatus.CONFLICT,
        )


if __name__ == "__main__":
    unittest.main()
