import json
from functools import lru_cache
import urllib.error
import urllib.request
from typing import Any, Callable

from config import (
    ENDPOINT_TOKEN,
    ENDPOINT_URL,
    MAX_TRANSLATION_CHUNK_CHARS,
    MODEL_TOKEN,
    MODEL_ID,
    SOURCE_LANGUAGE,
)


class TranslationError(RuntimeError):
    """Raised when no real translation could be produced."""


def split_long_text(text: str, limit: int = MAX_TRANSLATION_CHUNK_CHARS) -> list[str]:
    remaining = text.strip()
    chunks: list[str] = []
    while len(remaining) > limit:
        cut = remaining.rfind(" ", 0, limit + 1)
        if cut < limit // 2:
            cut = limit
        chunk = remaining[:cut].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def translate_many(
    texts: list[str],
    target_code: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[str]:
    """Translate text using a configured HF-compatible endpoint or local IT2."""
    if not texts:
        return []
    normalized = [text.strip() for text in texts]
    if any(not text for text in normalized):
        raise TranslationError("The translation input contains an empty segment.")

    chunks_by_text = [split_long_text(text) for text in normalized]
    chunk_count = sum(len(chunks) for chunks in chunks_by_text)
    completed = 0
    translated_by_text: list[list[str]] = [[] for _ in normalized]

    flattened_chunks = [
        (text_index, chunk)
        for text_index, chunks in enumerate(chunks_by_text)
        for chunk in chunks
    ]
    for offset in range(0, len(flattened_chunks), 8):
        batch = flattened_chunks[offset : offset + 8]
        batch_texts = [chunk for _text_index, chunk in batch]
        if ENDPOINT_URL:
            batch_results = [
                _translate_endpoint(
                    text,
                    source_code=SOURCE_LANGUAGE,
                    target_code=target_code,
                )
                for text in batch_texts
            ]
        else:
            batch_results = _translate_local(
                batch_texts,
                source_code=SOURCE_LANGUAGE,
                target_code=target_code,
            )
        if len(batch_results) != len(batch):
            raise TranslationError(
                "The translation service returned an unexpected number of results."
            )
        for (text_index, _chunk), translated in zip(batch, batch_results):
            if not isinstance(translated, str) or not translated.strip():
                raise TranslationError(
                    "The translation service returned an empty result."
                )
            translated_by_text[text_index].append(translated.strip())
            completed += 1
            if progress_callback:
                progress_callback(completed, chunk_count)

    results = [" ".join(parts) for parts in translated_by_text]
    if any(not result.strip() for result in results):
        raise TranslationError("The translation service returned empty output.")
    return results


def _translate_endpoint(
    text: str, source_code: str, target_code: str
) -> str:
    payload = {
        "inputs": text,
        "parameters": {
            "src_lang": source_code,
            "tgt_lang": target_code,
        },
    }
    headers = {"Content-Type": "application/json"}
    if ENDPOINT_TOKEN:
        headers["Authorization"] = f"Bearer {ENDPOINT_TOKEN}"
    request = urllib.request.Request(
        ENDPOINT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise TranslationError(
            f"The configured translation endpoint returned HTTP {exc.code}: "
            f"{detail or exc.reason}"
        ) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TranslationError(
            f"Could not reach the configured translation endpoint: {exc}"
        ) from exc

    try:
        response_data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TranslationError(
            "The configured endpoint returned a response that was not valid JSON."
        ) from exc
    return _extract_translation(response_data)


def _extract_translation(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        if len(value) == 1:
            return _extract_translation(value[0])
        raise TranslationError(
            "The endpoint returned multiple translations for one input segment."
        )
    if isinstance(value, dict):
        for key in ("translation_text", "generated_text", "translated_text"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
        if isinstance(value.get("error"), str):
            raise TranslationError(
                f"The translation endpoint reported an error: {value['error']}"
            )
    raise TranslationError(
        "The endpoint response did not contain translation_text or generated_text."
    )


@lru_cache(maxsize=1)
def _load_local_components() -> tuple[Any, Any, Any, Any, str]:
    try:
        import torch
        from IndicTransToolkit import IndicProcessor
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise TranslationError(
            "Local IndicTrans2 dependencies are not installed. Install "
            "requirements-model.txt, or configure INDICTRANS2_ENDPOINT_URL."
        ) from exc

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            token=MODEL_TOKEN or None,
        )
        model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_ID,
            trust_remote_code=True,
            token=MODEL_TOKEN or None,
        )
        model.to(device)
        model.eval()
        processor = IndicProcessor(inference=True)
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        raise TranslationError(
            "Could not load the AI4Bharat IndicTrans2 model. Check internet "
            "access, Hugging Face model access approval, available RAM, and "
            f"installation versions. Details: {reason}"
        ) from exc
    return torch, tokenizer, model, processor, device


def _translate_local(
    texts: list[str], source_code: str, target_code: str
) -> list[str]:
    try:
        torch, tokenizer, model, processor, device = _load_local_components()
        processed = processor.preprocess_batch(
            texts,
            src_lang=source_code,
            tgt_lang=target_code,
        )
        inputs = tokenizer(
            processed,
            truncation=True,
            padding="longest",
            max_length=256,
            return_tensors="pt",
            return_attention_mask=True,
        ).to(device)
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )
        decoded = tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        output = processor.postprocess_batch(decoded, lang=target_code)
    except TranslationError:
        raise
    except Exception as exc:
        raise TranslationError(
            f"IndicTrans2 inference failed ({type(exc).__name__}: {exc})."
        ) from exc

    if len(output) != len(texts):
        raise TranslationError(
            "IndicTrans2 returned an unexpected number of translated segments."
        )
    return output
