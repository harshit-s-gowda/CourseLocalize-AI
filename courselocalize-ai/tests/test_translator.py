import unittest
from unittest.mock import MagicMock, patch

from modules.translator import (
    TranslationError,
    _extract_translation,
    _translate_endpoint,
    translate_many,
)


class TranslatorTests(unittest.TestCase):
    def test_extracts_hugging_face_translation_response(self):
        self.assertEqual(
            _extract_translation([{"translation_text": "नमस्ते"}]),
            "नमस्ते",
        )

    def test_rejects_response_without_translation(self):
        with self.assertRaises(TranslationError):
            _extract_translation({"status": "ok"})

    def test_endpoint_posts_language_codes_and_reads_translation(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b'[{"translation_text":"namaste"}]'
        )
        with (
            patch("modules.translator.ENDPOINT_URL", "https://example.invalid/translate"),
            patch("modules.translator.ENDPOINT_TOKEN", "test-token"),
            patch("modules.translator.urllib.request.urlopen", return_value=response) as call,
        ):
            result = _translate_endpoint("Hello", "eng_Latn", "hin_Deva")
        request = call.call_args.args[0]
        self.assertEqual(result, "namaste")
        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer test-token",
        )
        self.assertIn(b'"src_lang": "eng_Latn"', request.data)
        self.assertIn(b'"tgt_lang": "hin_Deva"', request.data)

    def test_reports_missing_local_model_dependencies(self):
        with (
            patch("modules.translator.ENDPOINT_URL", ""),
            patch(
                "modules.translator._load_local_components",
                side_effect=TranslationError("dependencies unavailable"),
            ),
        ):
            with self.assertRaisesRegex(TranslationError, "dependencies unavailable"):
                translate_many(["Hello"], "hin_Deva")


if __name__ == "__main__":
    unittest.main()
