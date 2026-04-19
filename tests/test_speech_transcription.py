from __future__ import annotations

import unittest
from http import HTTPStatus

import python.speech_transcription as speech_transcription


class SpeechTranscriptionTests(unittest.TestCase):
    def test_parse_multipart_audio_reads_file_and_language(self) -> None:
        boundary = "----speech-boundary"
        multipart = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="language"\r\n\r\n'
            "de-DE\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="audio"; filename="sample.webm"\r\n'
            "Content-Type: audio/webm\r\n\r\n"
            "payload"
            f"\r\n--{boundary}--\r\n"
        ).encode("utf-8")

        file_name, payload, language = speech_transcription.parse_multipart_audio(
            f"multipart/form-data; boundary={boundary}",
            multipart,
        )

        self.assertEqual("sample.webm", file_name)
        self.assertEqual(b"payload", payload)
        self.assertEqual("de-de", language)

    def test_transcribe_audio_payload_rejects_unsupported_extension(self) -> None:
        with self.assertRaises(speech_transcription.SpeechTranscriptionError) as exc:
            speech_transcription.transcribe_audio_payload(
                original_name="clip.txt",
                payload=b"not-audio",
                language="de",
            )
        self.assertEqual(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, exc.exception.status_code)
        self.assertEqual("unsupported_audio_format", exc.exception.blocker)

    def test_runtime_payload_contains_consistent_shape(self) -> None:
        payload = speech_transcription.build_runtime_state_payload()
        self.assertIn("status", payload)
        self.assertIn("available", payload)
        self.assertIn("supported_extensions", payload)
        self.assertTrue(isinstance(payload["supported_extensions"], list))


if __name__ == "__main__":
    unittest.main()
