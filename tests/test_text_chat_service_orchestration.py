from __future__ import annotations

import unittest
from http import HTTPStatus

import python.text_chat_service_orchestration as text_chat_service


class TextChatServiceOrchestrationTests(unittest.TestCase):
    def test_prepare_request_uses_slot_context_and_defaults(self) -> None:
        prepared = text_chat_service.prepare_text_chat_service_request(
            slot={
                "title": "Bestehender Chat",
                "summary": "Kurzstand",
                "model_profile": "multilingual",
                "messages": [
                    {"role": "user", "content": "A"},
                    {"role": "assistant", "content": "B"},
                    {"role": "user", "content": "C"},
                ],
            },
            prompt=" Neue Frage ",
            requested_title=None,
            default_title="Chat 1",
            default_profile_id="standard",
            recent_messages_limit=2,
            infer_language=lambda prompt: "de" if "Frage" in prompt else "en",
            compose_prompt=lambda prompt, *, summary, recent_messages: f"{prompt.strip()}|{summary}|{len(recent_messages)}",
        )

        self.assertEqual(prepared["current_title"], "Bestehender Chat")
        self.assertEqual(prepared["inferred_language"], "de")
        self.assertEqual(prepared["profile_id"], "multilingual")
        self.assertEqual(
            prepared["recent_messages"],
            [
                {"role": "assistant", "content": "B"},
                {"role": "user", "content": "C"},
            ],
        )
        self.assertEqual(prepared["summary"], "Kurzstand")
        self.assertEqual(prepared["composed_prompt"], "Neue Frage|Kurzstand|2")

    def test_prepare_request_handles_missing_slot_data(self) -> None:
        prepared = text_chat_service.prepare_text_chat_service_request(
            slot=None,
            prompt="Prompt",
            requested_title="Neuer Chat",
            default_title="Chat 2",
            default_profile_id="standard",
            recent_messages_limit=6,
            infer_language=lambda prompt: "de",
            compose_prompt=lambda prompt, *, summary, recent_messages: prompt,
        )

        self.assertEqual(prepared["current_title"], "Neuer Chat")
        self.assertEqual(prepared["profile_id"], "standard")
        self.assertEqual(prepared["recent_messages"], [])
        self.assertIsNone(prepared["summary"])

    def test_execute_request_retries_once_after_switch_when_predicate_matches(
        self,
    ) -> None:
        calls: list[dict] = []
        sleeps: list[float] = []
        responses = iter(
            [
                ({}, "timeout", None, None, None),
                (
                    {"ok": True, "response_text": "Antwort"},
                    None,
                    HTTPStatus.OK,
                    "svc",
                    "ready",
                ),
            ]
        )

        def request_callable(
            prompt: str,
            *,
            mode: str | None,
            summary: str | None,
            recent_messages: list[dict],
        ):
            calls.append(
                {
                    "prompt": prompt,
                    "mode": mode,
                    "summary": summary,
                    "recent_messages": recent_messages,
                }
            )
            return next(responses)

        result = text_chat_service.execute_text_chat_service_request(
            request_callable=request_callable,
            retry_predicate=lambda **kwargs: True,
            sleep_callable=sleeps.append,
            switch_result={"changed": True},
            composed_prompt="Prompt",
            mode="writing",
            summary="Kurzstand",
            recent_messages=[{"role": "user", "content": "A"}],
        )

        self.assertEqual(len(calls), 2)
        self.assertEqual(sleeps, [5.0])
        self.assertEqual(result["response_status"], HTTPStatus.OK)
        self.assertEqual(
            result["response_payload"], {"ok": True, "response_text": "Antwort"}
        )

    def test_normalize_service_result_maps_transport_service_and_success_cases(
        self,
    ) -> None:
        unavailable = text_chat_service.normalize_text_chat_service_result(
            response_payload=None,
            response_error="timeout",
            response_status=None,
            service_name=None,
            model_status=None,
        )
        self.assertFalse(unavailable["ok"])
        self.assertEqual(unavailable["http_status"], HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(unavailable["blocker"], "text_service_unreachable")

        service_error = text_chat_service.normalize_text_chat_service_result(
            response_payload={"ok": False, "blocker": "busy", "message": "Busy"},
            response_error=None,
            response_status=HTTPStatus.CONFLICT,
            service_name=None,
            model_status=None,
        )
        self.assertFalse(service_error["ok"])
        self.assertEqual(service_error["http_status"], HTTPStatus.CONFLICT)
        self.assertEqual(service_error["blocker"], "busy")
        self.assertEqual(service_error["message"], "Busy")

        success = text_chat_service.normalize_text_chat_service_result(
            response_payload={"ok": True, "response_text": " Antwort "},
            response_error=None,
            response_status=HTTPStatus.OK,
            service_name="local-text-service",
            model_status="configured",
        )
        self.assertTrue(success["ok"])
        self.assertEqual(success["response_text"], "Antwort")
        self.assertEqual(success["service_name"], "local-text-service")
        self.assertEqual(success["model_status"], "configured")

    def test_post_response_state_updates_default_title_and_summary(self) -> None:
        result = text_chat_service.build_text_chat_post_response_state(
            updated_slot={
                "message_count": 2,
                "messages": [
                    {"role": "user", "content": "Bitte hilf mir."},
                    {"role": "assistant", "content": "Gern."},
                ],
            },
            slot_index=1,
            current_title="Chat 1",
            prompt="Bitte hilf mir.",
            default_title="Chat 1",
            excerpt_text=lambda text, *, limit: text[:limit],
            build_summary=lambda messages: "Zusammenfassung" if messages else None,
        )

        self.assertEqual(result["current_title"], "Bitte hilf mir.")
        self.assertEqual(result["updated_summary"], "Zusammenfassung")


if __name__ == "__main__":
    unittest.main()
