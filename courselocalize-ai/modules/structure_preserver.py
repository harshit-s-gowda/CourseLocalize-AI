from dataclasses import dataclass, field
import re
from typing import Any, Callable

from modules.terminology import protected_term_matches


PLACEHOLDER_PATTERN = re.compile(r"QZXCLZ[A-Z0-9]+QXZ")
INLINE_CODE_PATTERN = re.compile(r"(?<!`)`+[^`\n]*?`+")
URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
PATH_PATTERN = re.compile(
    r"(?<![\w])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
)
IDENTIFIER_PATTERNS = (
    re.compile(r"\b[A-Za-z_][A-Za-z0-9]*_[A-Za-z0-9_]+\b"),
    re.compile(r"\b[a-z]+[A-Z][A-Za-z0-9]*\b"),
    re.compile(r"\b[A-Za-z_]\w*(?=\s*\()"),
    re.compile(r"\b[A-Za-z_]\w*(?=\s*=)"),
)
FENCE_PATTERN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
HEADING_PREFIX = re.compile(r"^(\s{0,3}#{1,6}\s+)(.*)$")
QUOTE_PREFIX = re.compile(r"^(\s{0,3}>\s?)(.*)$")
LIST_PREFIX = re.compile(r"^(\s{0,3}(?:[-+*]|\d+[.)])\s+)(.*)$")


class PlaceholderError(ValueError):
    """Raised if the translation model loses, duplicates, or changes a sentinel."""


@dataclass
class PlaceholderVault:
    replacements: dict[str, str] = field(default_factory=dict)

    def protect(self, original: str, replacement: str | None = None) -> str:
        token = f"QZXCLZ{len(self.replacements) + 1:06d}QXZ"
        self.replacements[token] = original if replacement is None else replacement
        return token

    def restore_all(
        self,
        translated: str,
        expected_tokens: set[str] | None = None,
    ) -> str:
        found = PLACEHOLDER_PATTERN.findall(translated)
        unexpected = set(found) - set(self.replacements)
        if unexpected:
            raise PlaceholderError(
                "The translation returned an unknown protected placeholder."
            )
        required = (
            set(self.replacements)
            if expected_tokens is None
            else expected_tokens
        )
        invalid = [
            token
            for token in required
            if translated.count(token) != 1
        ]
        if invalid:
            raise PlaceholderError(
                "A protected code or terminology placeholder was missing, "
                "duplicated, or changed. The result was not saved."
            )
        return self.restore_text(translated)

    def restore_text(self, translated: str) -> str:
        restored = translated
        for token, original in self.replacements.items():
            restored = restored.replace(token, original)
        if PLACEHOLDER_PATTERN.search(restored):
            raise PlaceholderError(
                "A protected placeholder could not be restored safely."
            )
        return restored


def protect_text(
    text: str,
    target_code: str,
    terminology: list[dict[str, Any]],
    vault: PlaceholderVault,
) -> str:
    candidates: list[tuple[int, int, int, str]] = []
    patterns = [INLINE_CODE_PATTERN, URL_PATTERN, PATH_PATTERN, *IDENTIFIER_PATTERNS]
    for priority, pattern in enumerate(patterns):
        candidates.extend(
            (match.start(), match.end(), priority, match.group(0))
            for match in pattern.finditer(text)
        )
    term_priority = len(patterns)
    candidates.extend(
        (start, end, term_priority, replacement)
        for start, end, replacement in protected_term_matches(
            text, target_code, terminology
        )
    )
    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            -(candidate[1] - candidate[0]),
            candidate[2],
        )
    )

    selected: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, _priority, replacement in candidates:
        if start >= last_end:
            selected.append((start, end, replacement))
            last_end = end

    pieces: list[str] = []
    cursor = 0
    for start, end, replacement in selected:
        pieces.append(text[cursor:start])
        pieces.append(vault.protect(text[start:end], replacement))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def _split_prefix(line: str) -> tuple[str, str]:
    prefix = ""
    remainder = line
    while True:
        match = (
            QUOTE_PREFIX.match(remainder)
            or HEADING_PREFIX.match(remainder)
            or LIST_PREFIX.match(remainder)
        )
        if not match:
            break
        prefix += match.group(1)
        remainder = match.group(2)
        if match.re is HEADING_PREFIX:
            break
    return prefix, remainder


def _is_table_separator(line: str) -> bool:
    if "|" not in line:
        return False
    compact = line.replace("|", "").replace(":", "").replace("-", "").strip()
    return not compact


def _split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def _has_visible_text_outside_placeholders(text: str) -> bool:
    return bool(PLACEHOLDER_PATTERN.sub("", text).strip())


def translate_markdown_document(
    source: str,
    target_code: str,
    terminology: list[dict[str, Any]],
    translate_batch: Callable[[list[str]], list[str]],
) -> tuple[str, PlaceholderVault]:
    """Translate prose while retaining line layout, Markdown markers, and code."""
    vault = PlaceholderVault()
    prepared_lines: list[dict[str, Any]] = []
    to_translate: list[str] = []
    in_code_fence = False
    active_fence = ""

    for line in source.splitlines(keepends=True):
        content, ending = _split_line_ending(line)
        fence_match = FENCE_PATTERN.match(content)
        if fence_match:
            marker = fence_match.group(1)
            if not in_code_fence:
                in_code_fence = True
                active_fence = marker[0]
            elif marker[0] == active_fence:
                in_code_fence = False
                active_fence = ""
            prepared_lines.append({"kind": "raw", "text": line})
            continue
        if in_code_fence or not content.strip():
            prepared_lines.append({"kind": "raw", "text": line})
            continue

        if content.count("|") >= 2 and _is_table_separator(content):
            prepared_lines.append({"kind": "raw", "text": line})
            continue

        if content.count("|") >= 2:
            cells = content.split("|")
            protected_cells: list[str] = []
            for cell in cells:
                protected = protect_text(cell, target_code, terminology, vault)
                translate = _has_visible_text_outside_placeholders(protected)
                if translate:
                    to_translate.append(protected)
                protected_cells.append(protected)
            prepared_lines.append(
                {
                    "kind": "table",
                    "cells": protected_cells,
                    "ending": ending,
                }
            )
            continue

        prefix, body = _split_prefix(content)
        protected_body = protect_text(body, target_code, terminology, vault)
        should_translate = _has_visible_text_outside_placeholders(protected_body)
        if should_translate:
            to_translate.append(protected_body)
        prepared_lines.append(
            {
                "kind": "line",
                "prefix": prefix,
                "body": protected_body,
                "ending": ending,
            }
        )

    if in_code_fence:
        raise ValueError("The Markdown document contains an unclosed code fence.")
    if not to_translate:
        raise ValueError("No translatable text was found outside code blocks.")

    translated_parts = translate_batch(to_translate)
    if len(translated_parts) != len(to_translate):
        raise ValueError(
            "The translation model returned an unexpected number of results."
        )
    combined_translated = "\n".join(translated_parts)
    translated_tokens = {
        token
        for segment in to_translate
        for token in PLACEHOLDER_PATTERN.findall(segment)
    }
    restored_combined = vault.restore_all(
        combined_translated,
        expected_tokens=translated_tokens,
    )

    # Each model result is restored individually after the whole response has
    # passed placeholder integrity checks; splitting preserves each source line.
    restored_parts = []
    for part in translated_parts:
        restored_part = part
        for token, original in vault.replacements.items():
            restored_part = restored_part.replace(token, original)
        restored_parts.append(restored_part)

    part_index = 0
    output_lines: list[str] = []
    for prepared in prepared_lines:
        if prepared["kind"] == "raw":
            output_lines.append(prepared["text"])
            continue
        if prepared["kind"] == "table":
            output_cells = []
            for cell in prepared["cells"]:
                if _has_visible_text_outside_placeholders(cell):
                    output_cells.append(restored_parts[part_index])
                    part_index += 1
                else:
                    output_cells.append(vault.restore_text(cell))
            output_lines.append(
                "|".join(output_cells) + prepared["ending"]
            )
            continue
        body = prepared["body"]
        if _has_visible_text_outside_placeholders(body):
            body = restored_parts[part_index]
            part_index += 1
        else:
            body = vault.restore_text(body)
        prefix = prepared["prefix"]
        output_lines.append(prefix + body + prepared["ending"])

    if part_index != len(restored_parts):
        raise ValueError("The document structure could not be reconstructed safely.")
    translated_document = "".join(output_lines)
    if not translated_document.strip():
        raise ValueError("The translation returned empty output.")
    # The full combined check above catches corruption before any result is used.
    if not restored_combined.strip():
        raise ValueError("The translation returned empty output.")
    return translated_document, vault
