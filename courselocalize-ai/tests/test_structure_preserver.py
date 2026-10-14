import unittest

from modules.structure_preserver import (
    PlaceholderError,
    PlaceholderVault,
    translate_markdown_document,
)
from modules.terminology import DEFAULT_TERMINOLOGY


def uppercase_translation(segments):
    return [segment.upper() for segment in segments]


class StructurePreserverTests(unittest.TestCase):
    def test_restores_inline_code_terms_headings_lists_and_fenced_code(self):
        source = (
            "# Database basics\n"
            "\n"
            "Use the API and `db.connect()` in Python.\n"
            "- Keep this list item.\n"
            "\n"
            "```python\n"
            "def connect_db():\n"
            "    return True\n"
            "```\n"
        )
        output, _vault = translate_markdown_document(
            source,
            "hin_Deva",
            DEFAULT_TERMINOLOGY,
            uppercase_translation,
        )

        self.assertTrue(output.startswith("# DATABASE BASICS\n"))
        self.assertIn("API", output)
        self.assertIn("`db.connect()`", output)
        self.assertIn("IN Python.", output)
        self.assertIn("- KEEP THIS LIST ITEM.", output)
        self.assertIn("def connect_db():\n    return True\n", output)

    def test_translates_markdown_table_cells_but_keeps_delimiters(self):
        source = "| Term | Detail |\n| --- | --- |\n| API | Service |\n"
        output, _vault = translate_markdown_document(
            source,
            "kan_Knda",
            DEFAULT_TERMINOLOGY,
            uppercase_translation,
        )
        self.assertEqual(output.count("|"), source.count("|"))
        self.assertIn("| --- | --- |", output)
        self.assertIn("| API | SERVICE |", output)

    def test_checks_missing_placeholders(self):
        vault = PlaceholderVault()
        token = vault.protect("print('safe')")
        with self.assertRaises(PlaceholderError):
            vault.restore_all("translation", expected_tokens={token})

    def test_rejects_unclosed_code_fence(self):
        with self.assertRaisesRegex(ValueError, "unclosed code fence"):
            translate_markdown_document(
                "Intro\n```python\nprint('x')\n",
                "hin_Deva",
                DEFAULT_TERMINOLOGY,
                uppercase_translation,
            )


if __name__ == "__main__":
    unittest.main()
