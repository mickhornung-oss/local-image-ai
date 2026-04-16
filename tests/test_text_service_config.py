from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import python.text_service as text_service


class TextServiceConfigTests(unittest.TestCase):
    def test_normalize_config_accepts_loopback_defaults(self) -> None:
        payload = text_service.normalize_config(
            {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 8091,
                "service_name": "local-text-service",
                "model_status": "configured",
                "runner_type": "llama_cpp_server",
                "runner_host": "127.0.0.1",
                "runner_port": 8092,
                "runner_binary_path": "vendor/text_runner/llama-server.exe",
                "model_format": "gguf",
                "model_path": "vendor/text_models/model.gguf",
            }
        )
        self.assertEqual(payload["host"], "127.0.0.1")
        self.assertEqual(payload["runner_port"], 8092)
        self.assertEqual(payload["model_format"], "gguf")

    def test_normalize_config_rejects_non_loopback_host(self) -> None:
        with self.assertRaises(text_service.TextServiceConfigError):
            text_service.normalize_config({"host": "0.0.0.0"})

    def test_validate_optional_mode_payload(self) -> None:
        self.assertEqual(
            text_service.validate_optional_mode_payload({"mode": "rewrite"}),
            text_service.TEXT_WORK_MODE_REWRITE,
        )

    def test_build_runner_messages_uses_mid_length_default_for_writing(self) -> None:
        profile, messages = text_service.build_runner_messages(
            "Schreibe einen freundlichen Einladungstext fuer einen kleinen Teamabend.",
            forced_mode=text_service.TEXT_WORK_MODE_WRITING,
        )

        self.assertEqual(profile, text_service.PROMPT_PROFILE_WRITING)
        self.assertEqual(len(messages), 2)
        self.assertIn("ungefaehr 110 Woerter", messages[1]["content"])

    def test_request_runner_response_uses_expanded_context_budget(self) -> None:
        captured_payload: dict[str, object] = {}

        class _Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b'{"choices":[{"message":{"content":"Antworttext"}}]}'

        def fake_urlopen(request, timeout):
            nonlocal captured_payload
            captured_payload = json.loads(request.data.decode("utf-8"))
            return _Response()

        runtime_state = {"runner_host": "127.0.0.1", "runner_port": 8092}
        messages = [{"role": "user", "content": "Bitte schreibe einen laengeren Text."}]

        with patch.object(
            text_service, "estimate_message_token_usage", return_value=1700
        ), patch.object(
            text_service.urllib_request, "urlopen", side_effect=fake_urlopen
        ):
            response = text_service.request_runner_response(
                runtime_state,
                messages,
                request_settings={"max_tokens": 1200, "timeout_seconds": 1.0},
            )

        self.assertEqual(response, "Antworttext")
        self.assertEqual(captured_payload["max_tokens"], 1200)

    def test_build_runner_request_settings_increases_retry_budget_for_underlength_writing(
        self,
    ) -> None:
        first = text_service.build_runner_request_settings(
            text_service.PROMPT_PROFILE_WRITING,
            "Schreibe einen Infotext mit 160 bis 200 Woertern ueber eine kleine Werkstatt.",
        )
        retry = text_service.build_runner_request_settings(
            text_service.PROMPT_PROFILE_WRITING,
            "Schreibe einen Infotext mit 160 bis 200 Woertern ueber eine kleine Werkstatt.",
            retry=True,
            previous_response="Kurzer Entwurf mit deutlich zu wenig Inhalt.",
        )

        self.assertGreater(retry["max_tokens"], first["max_tokens"])
        self.assertGreaterEqual(retry["timeout_seconds"], first["timeout_seconds"])

    def test_build_runner_request_settings_uses_long_form_stop_sequences_for_writing(
        self,
    ) -> None:
        settings = text_service.build_runner_request_settings(
            text_service.PROMPT_PROFILE_WRITING,
            "Schreibe einen Text mit 160 bis 200 Woertern ueber ein Atelier.",
        )

        self.assertEqual(
            settings["stop_sequences"], text_service.RUNNER_LONG_FORM_STOP_SEQUENCES
        )

    def test_build_underlength_continuation_messages_requests_direct_continuation(
        self,
    ) -> None:
        messages = text_service.build_underlength_continuation_messages(
            text_service.PROMPT_PROFILE_WRITING,
            "Schreibe einen Text mit 160 bis 200 Woertern ueber eine Werkstatt.",
            "Die Werkstatt lag still in der Morgensonne.",
        )

        self.assertEqual(len(messages), 2)
        self.assertIn("fuehrst", messages[0]["content"])
        self.assertIn("Gib nur die direkte Fortsetzung aus", messages[1]["content"])

    def test_is_translation_request_detects_explicit_target_language(self) -> None:
        self.assertTrue(
            text_service.is_translation_request(
                "Translate the following German text into natural English without shortening it."
            )
        )


if __name__ == "__main__":
    unittest.main()
