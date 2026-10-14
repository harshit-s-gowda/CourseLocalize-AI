from dataclasses import dataclass
import re


@dataclass
class QualityReport:
    checks: dict[str, bool]
    warnings: list[str]


def _count_markdown(source: str, pattern: str) -> int:
    return len(re.findall(pattern, source, flags=re.MULTILINE))


def extract_fenced_code_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    fence_char = ""
    for line in text.splitlines(keepends=True):
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)
            if not in_fence:
                in_fence = True
                fence_char = marker[0]
                current = [line]
            elif marker[0] == fence_char:
                current.append(line)
                blocks.append("".join(current))
                current = []
                in_fence = False
                fence_char = ""
            else:
                current.append(line)
        elif in_fence:
            current.append(line)
    return blocks


def _table_pipe_counts(text: str) -> list[int]:
    return [line.count("|") for line in text.splitlines() if line.count("|") >= 2]


def _paragraph_break_count(text: str) -> int:
    return len(re.findall(r"\n[ \t]*\n", text))


def check_translation(source: str, translated: str) -> QualityReport:
    if not source.strip() or not translated.strip():
        return QualityReport(
            checks={
                "Input is not empty": bool(source.strip()),
                "Output is not empty": bool(translated.strip()),
                "Code blocks are unchanged": False,
                "Headings are preserved": False,
                "List structure is preserved": False,
                "Table delimiters are preserved": False,
                "Paragraph breaks are preserved": False,
            },
            warnings=["The input or translation is empty."],
        )

    source_code = extract_fenced_code_blocks(source)
    translated_code = extract_fenced_code_blocks(translated)
    checks = {
        "Input is not empty": True,
        "Output is not empty": True,
        "Code blocks are unchanged": source_code == translated_code,
        "Headings are preserved": _count_markdown(source, r"^\s{0,3}#{1,6}\s")
        == _count_markdown(translated, r"^\s{0,3}#{1,6}\s"),
        "List structure is preserved": _count_markdown(
            source, r"^\s{0,3}(?:[-+*]|\d+[.)])\s"
        )
        == _count_markdown(translated, r"^\s{0,3}(?:[-+*]|\d+[.)])\s"),
        "Table delimiters are preserved": _table_pipe_counts(source)
        == _table_pipe_counts(translated),
        "Paragraph breaks are preserved": _paragraph_break_count(source)
        == _paragraph_break_count(translated),
    }
    warnings = [
        f"{label} check did not pass."
        for label, passed in checks.items()
        if not passed
    ]
    return QualityReport(checks=checks, warnings=warnings)


def evaluate_reference(
    translation: str,
    reference: str,
) -> dict[str, float]:
    if not translation.strip() or not reference.strip():
        raise ValueError("Both the translation and reference must contain text.")
    try:
        import sacrebleu
    except ImportError as exc:
        raise RuntimeError(
            "BLEU and chrF++ evaluation require the sacrebleu package."
        ) from exc

    bleu = sacrebleu.BLEU(effective_order=True)
    chrf = sacrebleu.CHRF(word_order=2)
    bleu_score = bleu.corpus_score([translation], [[reference]]).score
    chrf_score = chrf.corpus_score([translation], [[reference]]).score
    return {"BLEU": float(bleu_score), "chrF++": float(chrf_score)}
