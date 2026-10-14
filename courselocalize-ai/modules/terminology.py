import json
import re
from pathlib import Path
from typing import Any

from config import LANGUAGES, TERMINOLOGY_PATH


DEFAULT_TERMINOLOGY: list[dict[str, Any]] = [
    {"term": "Function", "mode": "translate", "translations": {}},
    {"term": "Variable", "mode": "translate", "translations": {}},
    {"term": "Database", "mode": "translate", "translations": {}},
    {"term": "Algorithm", "mode": "translate", "translations": {}},
    {"term": "Machine Learning", "mode": "translate", "translations": {}},
    {"term": "Artificial Intelligence", "mode": "translate", "translations": {}},
    {"term": "API", "mode": "preserve", "translations": {}},
    {"term": "Python", "mode": "preserve", "translations": {}},
    {"term": "SQL", "mode": "preserve", "translations": {}},
    {"term": "HTML", "mode": "preserve", "translations": {}},
]


def validate_terminology(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("The dictionary must be a JSON array of term objects.")

    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    allowed_codes = set(LANGUAGES.values())
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Entry {index} must be a JSON object.")
        term = item.get("term")
        mode = item.get("mode", "translate")
        translations = item.get("translations", {})
        if not isinstance(term, str) or not term.strip():
            raise ValueError(f"Entry {index} needs a non-empty term.")
        normalized = term.strip().casefold()
        if normalized in seen:
            raise ValueError(f'The term "{term.strip()}" appears more than once.')
        if mode not in {"preserve", "translate"}:
            raise ValueError(
                f'Entry "{term}" has an invalid mode. Use "preserve" or "translate".'
            )
        if not isinstance(translations, dict):
            raise ValueError(f'Entry "{term}" translations must be a JSON object.')
        for code, translation in translations.items():
            if code not in allowed_codes:
                raise ValueError(
                    f'Entry "{term}" uses unsupported language code "{code}".'
                )
            if not isinstance(translation, str) or not translation.strip():
                raise ValueError(
                    f'Entry "{term}" translation for {code} must be non-empty text.'
                )
        seen.add(normalized)
        validated.append(
            {
                "term": term.strip(),
                "mode": mode,
                "translations": {
                    code: translation.strip()
                    for code, translation in translations.items()
                },
            }
        )
    return validated


def load_terminology(path: Path = TERMINOLOGY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return [dict(entry) for entry in DEFAULT_TERMINOLOGY]
    try:
        with path.open("r", encoding="utf-8") as file:
            return validate_terminology(json.load(file))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Could not load the terminology dictionary: {exc}") from exc


def save_terminology(
    entries: list[dict[str, Any]], path: Path = TERMINOLOGY_PATH
) -> list[dict[str, Any]]:
    validated = validate_terminology(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
    return validated


def protected_term_matches(
    text: str, target_code: str, entries: list[dict[str, Any]]
) -> list[tuple[int, int, str]]:
    """Return non-overlapping (start, end, replacement) protected term spans."""
    candidates: list[tuple[int, int, int, str]] = []
    for entry in entries:
        term = entry["term"]
        preferred = entry.get("translations", {}).get(target_code)
        if entry.get("mode") != "preserve" and not preferred:
            continue
        pattern = re.compile(
            rf"(?<!\w){re.escape(term)}(?!\w)",
            flags=re.IGNORECASE,
        )
        replacement = preferred
        for match in pattern.finditer(text):
            candidates.append(
                (
                    match.start(),
                    match.end(),
                    match.end() - match.start(),
                    replacement or match.group(0),
                )
            )

    candidates.sort(key=lambda candidate: (candidate[0], -candidate[2]))
    selected: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, _length, replacement in candidates:
        if start >= last_end:
            selected.append((start, end, replacement))
            last_end = end
    return selected
