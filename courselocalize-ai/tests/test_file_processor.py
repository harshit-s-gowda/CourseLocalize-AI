import unittest

import pymupdf

from modules.file_processor import (
    ContentError,
    download_bytes,
    extract_text,
    validate_pasted_text,
)


class FileProcessorTests(unittest.TestCase):
    def test_extracts_utf8_markdown(self):
        self.assertEqual(
            extract_text("lesson.md", b"# Hello\n\nCourse content"),
            "# Hello\n\nCourse content",
        )

    def test_extracts_selectable_pdf_text(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "A database stores information.")
        pdf_bytes = document.tobytes()
        document.close()
        self.assertIn(
            "A database stores information.",
            extract_text("lesson.pdf", pdf_bytes),
        )

    def test_rejects_empty_upload(self):
        with self.assertRaisesRegex(ContentError, "empty"):
            extract_text("lesson.txt", b"")

    def test_rejects_unsupported_file_type(self):
        with self.assertRaisesRegex(ContentError, "Unsupported file type"):
            extract_text("lesson.exe", b"not executable")

    def test_rejects_invalid_utf8(self):
        with self.assertRaisesRegex(ContentError, "UTF-8"):
            extract_text("lesson.txt", b"\xff")

    def test_rejects_empty_pasted_text(self):
        with self.assertRaisesRegex(ContentError, "Paste course content"):
            validate_pasted_text(" \n")

    def test_download_output_is_utf8(self):
        self.assertEqual(download_bytes("ನಮಸ್ಕಾರ"), "ನಮಸ್ಕಾರ".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
