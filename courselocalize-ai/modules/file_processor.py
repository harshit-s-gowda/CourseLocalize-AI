from pathlib import Path

from config import MAX_UPLOAD_BYTES


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


class ContentError(ValueError):
    """Raised when uploaded or pasted course content cannot be processed."""


def extract_text(filename: str, content: bytes) -> str:
    """Extract UTF-8 text or selectable PDF text without executing file contents."""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ContentError(f"Unsupported file type. Upload one of: {supported}.")
    if not content:
        raise ContentError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ContentError("The file is larger than the 5 MB upload limit.")

    if suffix == ".pdf":
        try:
            import pymupdf
        except ImportError as exc:
            raise ContentError(
                "PDF support is not installed. Install the project requirements "
                "and try again."
            ) from exc

        try:
            with pymupdf.open(stream=content, filetype="pdf") as document:
                if document.needs_pass:
                    raise ContentError(
                        "This PDF is password-protected and cannot be read."
                    )
                text = "\n\n".join(page.get_text("text") for page in document)
        except ContentError:
            raise
        except Exception as exc:
            raise ContentError(
                "The PDF could not be read. It may be corrupted or unsupported."
            ) from exc
        if not text.strip():
            raise ContentError(
                "No selectable text was found in the PDF. Scanned PDFs need OCR "
                "before they can be localized."
            )
        return text

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContentError(
            "The file is not valid UTF-8 text. Save it as UTF-8 and upload it again."
        ) from exc
    if not text.strip():
        raise ContentError("The uploaded file contains no text.")
    return text


def validate_pasted_text(text: str) -> str:
    if not text or not text.strip():
        raise ContentError("Paste course content before starting localization.")
    if len(text) > MAX_UPLOAD_BYTES:
        raise ContentError("Pasted content is larger than the 5 MB input limit.")
    return text


def download_bytes(text: str) -> bytes:
    """Return UTF-8 bytes for Streamlit's TXT and Markdown download buttons."""
    return text.encode("utf-8")
