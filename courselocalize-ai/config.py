from pathlib import Path
import os


APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
TERMINOLOGY_PATH = DATA_DIR / "terminology.json"
HISTORY_PATH = DATA_DIR / "history.json"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_DOCUMENT_CHARS = 50_000
MAX_TRANSLATION_CHUNK_CHARS = 350
MODEL_ID = os.getenv(
    "INDICTRANS2_MODEL",
    "ai4bharat/indictrans2-en-indic-dist-200M",
)
ENDPOINT_URL = os.getenv("INDICTRANS2_ENDPOINT_URL", "").strip()
ENDPOINT_TOKEN = (
    os.getenv("HUGGINGFACEHUB_API_TOKEN")
    or os.getenv("HF_TOKEN")
    or ""
).strip()
MODEL_TOKEN = (
    os.getenv("HF_TOKEN")
    or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    or ""
).strip()

SOURCE_LANGUAGE = "eng_Latn"
LANGUAGES = {
    "Kannada": "kan_Knda",
    "Hindi": "hin_Deva",
    "Tamil": "tam_Taml",
    "Telugu": "tel_Telu",
}
