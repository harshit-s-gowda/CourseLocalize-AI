from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import HISTORY_PATH


MAX_HISTORY_ITEMS = 25


def load_history(path: Path = HISTORY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read local history: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError("Local history must contain a JSON array.")
    return [item for item in data if isinstance(item, dict)]


def add_history_item(
    source_filename: str,
    target_language: str,
    status: str,
    original: str = "",
    translated: str = "",
    warnings: list[str] | None = None,
    path: Path = HISTORY_PATH,
) -> dict[str, Any]:
    if status not in {"success", "failed"}:
        raise ValueError("History status must be success or failed.")
    record = {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_filename": source_filename,
        "target_language": target_language,
        "status": status,
        "original": original if status == "success" else "",
        "translated": translated if status == "success" else "",
        "warnings": warnings or [],
    }
    items = [record, *load_history(path)]
    save_history(items[:MAX_HISTORY_ITEMS], path)
    return record


def save_history(items: list[dict[str, Any]], path: Path = HISTORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def clear_history(path: Path = HISTORY_PATH) -> None:
    save_history([], path)
