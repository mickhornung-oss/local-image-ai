from __future__ import annotations

import unittest

import python.text_prompting as text_prompting


class TextPromptingTests(unittest.TestCase):
    def test_extract_requested_word_bounds_range(self) -> None:
        self.assertEqual(
            text_prompting.extract_requested_word_bounds(
                "Schreibe bitte zwischen 120 und 150 Woertern."
            ),
            (120, 150),
        )

    def test_extract_requested_word_target_single_value(self) -> None:
        self.assertEqual(
            text_prompting.extract_requested_word_target(
                "Bitte schreibe etwa 200 Woerter ueber Licht."
            ),
            200,
        )

    def test_classify_prompt_profile_image(self) -> None:
        self.assertEqual(
            text_prompting.classify_prompt_profile(
                "Schreibe einen Bildprompt fuer eine ruhige Waldszene."
            ),
            text_prompting.PROMPT_PROFILE_IMAGE,
        )

    def test_classify_prompt_profile_rewrite(self) -> None:
        self.assertEqual(
            text_prompting.classify_prompt_profile(
                "Bitte formuliere diesen Text freundlicher um."
            ),
            text_prompting.PROMPT_PROFILE_REWRITE,
        )

    def test_classify_prompt_profile_writing(self) -> None:
        self.assertEqual(
            text_prompting.classify_prompt_profile(
                "Schreibe einen warmen Brief mit 140 Woertern."
            ),
            text_prompting.PROMPT_PROFILE_WRITING,
        )

    def test_extract_image_prompt_subject(self) -> None:
        self.assertEqual(
            text_prompting.extract_image_prompt_subject(
                "Schreibe einen Bildprompt fuer eine Katze am Fenster"
            ),
            "eine Katze am Fenster",
        )

    def test_runtime_uses_multilingual_profile(self) -> None:
        self.assertTrue(
            text_prompting.runtime_uses_multilingual_profile(
                {"resolved_model_path": r"C:\models\gemma-3-12b-instruct.gguf"}
            )
        )


if __name__ == "__main__":
    unittest.main()
