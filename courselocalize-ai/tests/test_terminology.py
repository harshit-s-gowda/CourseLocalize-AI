import tempfile
import unittest
from pathlib import Path

from modules.terminology import (
    DEFAULT_TERMINOLOGY,
    load_terminology,
    protected_term_matches,
    save_terminology,
    validate_terminology,
)


class TerminologyTests(unittest.TestCase):
    def test_default_dictionary_has_preserved_and_translatable_terms(self):
        modes = {entry["term"]: entry["mode"] for entry in DEFAULT_TERMINOLOGY}
        self.assertEqual(modes["API"], "preserve")
        self.assertEqual(modes["Function"], "translate")

    def test_preserves_exact_term_and_uses_preferred_translation(self):
        entries = [
            {"term": "API", "mode": "preserve", "translations": {}},
            {
                "term": "Database",
                "mode": "translate",
                "translations": {"hin_Deva": "डेटाबेस"},
            },
        ]
        matches = protected_term_matches(
            "The api uses a Database.", "hin_Deva", entries
        )
        self.assertEqual([match[2] for match in matches], ["api", "डेटाबेस"])

    def test_rejects_duplicate_terms(self):
        with self.assertRaisesRegex(ValueError, "more than once"):
            validate_terminology(
                [
                    {"term": "API", "mode": "preserve"},
                    {"term": "api", "mode": "preserve"},
                ]
            )

    def test_saves_and_loads_dictionary_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terms.json"
            saved = save_terminology(DEFAULT_TERMINOLOGY, path)
            self.assertEqual(load_terminology(path), saved)


if __name__ == "__main__":
    unittest.main()
