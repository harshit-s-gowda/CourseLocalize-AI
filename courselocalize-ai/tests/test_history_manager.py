import tempfile
import unittest
from pathlib import Path

from modules.history_manager import add_history_item, clear_history, load_history


class HistoryManagerTests(unittest.TestCase):
    def test_saves_reopens_and_clears_successful_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            record = add_history_item(
                "lesson.md",
                "Hindi",
                "success",
                original="# Lesson",
                translated="# पाठ",
                path=path,
            )
            items = load_history(path)
            self.assertEqual(items[0]["id"], record["id"])
            self.assertEqual(items[0]["translated"], "# पाठ")
            clear_history(path)
            self.assertEqual(load_history(path), [])

    def test_failed_history_does_not_store_course_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            record = add_history_item(
                "lesson.md",
                "Hindi",
                "failed",
                original="private course text",
                translated="fake result",
                path=path,
            )
            self.assertEqual(record["original"], "")
            self.assertEqual(record["translated"], "")


if __name__ == "__main__":
    unittest.main()
