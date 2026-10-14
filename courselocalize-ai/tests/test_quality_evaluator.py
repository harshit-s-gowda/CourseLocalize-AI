import unittest

from modules.quality_evaluator import check_translation, extract_fenced_code_blocks


class QualityEvaluatorTests(unittest.TestCase):
    def test_checks_structure_and_exact_code(self):
        source = (
            "# Title\n\n"
            "- Item\n\n"
            "| Term | Meaning |\n"
            "| --- | --- |\n\n"
            "```python\nprint('hi')\n```\n"
        )
        report = check_translation(source, source)
        self.assertTrue(all(report.checks.values()))
        self.assertEqual(
            extract_fenced_code_blocks(source),
            ["```python\nprint('hi')\n```\n"],
        )

    def test_warns_when_heading_or_code_changes(self):
        report = check_translation(
            "# Title\n```python\nprint('hi')\n```\n",
            "Title\n```python\nprint('hello')\n```\n",
        )
        self.assertFalse(report.checks["Code blocks are unchanged"])
        self.assertFalse(report.checks["Headings are preserved"])
        self.assertTrue(report.warnings)


if __name__ == "__main__":
    unittest.main()
