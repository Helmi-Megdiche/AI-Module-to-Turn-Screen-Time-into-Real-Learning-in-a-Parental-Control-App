"""
EasyOCR wrapper: **two** shared ``Reader`` instances (Latin en+fr, Arabic ar).

EasyOCR does not allow ``ar`` with ``fr`` in the same ``lang_list``. We run the Latin reader
first and optionally the Arabic reader when confidence is low or Arabizi hints appear in the
Latin output — never triple-lang on every request.

If the Latin reader fails to initialize, ``extract_text`` returns ``""``. If the Arabic reader
fails, fallback Latin-only continues when the Arabic pass would have run.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)

_LATIN_LANGS = ["en", "fr"]
_ARABIC_LANGS = ["ar"]

# Arabizi-style Latin digits in risky / dialect typing (trigger Arabic pass).
ARABIZI_HINTS: frozenset[str] = frozenset("35792")

_ARABIC_FALLBACK_CONF_THRESHOLD = 0.55

_latin_reader: Any = None
_arabic_reader: Any = None
_latin_init_failed: bool = False
_arabic_init_failed: bool = False


def _cuda_usable_for_easyocr() -> bool:
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def get_latin_reader() -> Any | None:
    """Lazily construct the Latin (en+fr) reader, or None if loading failed."""
    global _latin_reader, _latin_init_failed
    if _latin_init_failed:
        return None
    if _latin_reader is not None:
        return _latin_reader
    import easyocr

    cuda_ok = _cuda_usable_for_easyocr()
    try:
        _latin_reader = easyocr.Reader(_LATIN_LANGS, gpu=cuda_ok, verbose=False)
        logger.info("EasyOCR Latin reader initialised | langs=en,fr | gpu=%s", cuda_ok)
        return _latin_reader
    except Exception as e:
        logger.warning("Failed to load EasyOCR Latin reader: %s", e)
        _latin_init_failed = True
        return None


def get_arabic_reader() -> Any | None:
    """Lazily construct the Arabic reader, or None if loading failed."""
    global _arabic_reader, _arabic_init_failed
    if _arabic_init_failed:
        return None
    if _arabic_reader is not None:
        return _arabic_reader
    import easyocr

    cuda_ok = _cuda_usable_for_easyocr()
    try:
        _arabic_reader = easyocr.Reader(_ARABIC_LANGS, gpu=cuda_ok, verbose=False)
        logger.info("EasyOCR Arabic reader initialised | langs=ar | gpu=%s", cuda_ok)
        return _arabic_reader
    except Exception as e:
        logger.warning("Failed to load EasyOCR Arabic reader: %s", e)
        _arabic_init_failed = True
        return None


def get_reader() -> Any | None:
    """
    Backward-compatible preload hook for FastAPI startup: ensures Latin reader is loaded.

    Returns:
        The Latin reader, or None if Latin OCR is unavailable.
    """
    return get_latin_reader()


def avg_confidence(results: list[Any]) -> float:
    """Mean EasyOCR confidence for ``readtext`` rows ``(bbox, text, conf)``."""
    if not results:
        return 0.0
    return sum(float(r[2]) for r in results) / len(results)


def contains_arabizi(text: str) -> bool:
    """True if Latin OCR output contains digit letters common in Arabizi."""
    return any(c in ARABIZI_HINTS for c in text)


def _results_to_unique_words_ordered(results: list[Any]) -> str:
    """Unique words, case-insensitive, first-seen order (box order, then word order within box)."""
    seen: set[str] = set()
    words: list[str] = []
    for _bbox, text, _conf in results:
        for word in (text or "").split():
            lower = word.lower()
            if lower not in seen:
                seen.add(lower)
                words.append(lower)
    return " ".join(words).strip()


def extract_text(pil_image: Image.Image) -> str:
    """
    Run adaptive OCR; return unique words (case-insensitive) in first-seen order, or "" if
    the Latin reader is unavailable.
    """
    latin_reader = get_latin_reader()
    if latin_reader is None:
        return ""
    try:
        im = pil_image.copy()
        im.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        img_np = np.array(im)

        t0 = perf_counter()
        latin_results = latin_reader.readtext(img_np)
        latin_conf = avg_confidence(latin_results)
        latin_joined = " ".join(str(r[1]) for r in latin_results)

        use_arabic = latin_conf < _ARABIC_FALLBACK_CONF_THRESHOLD or contains_arabizi(latin_joined)
        mode = "latin_only"
        merged: list[Any] = list(latin_results)

        if use_arabic:
            arabic_reader = get_arabic_reader()
            if arabic_reader is not None:
                arabic_results = arabic_reader.readtext(img_np)
                merged.extend(arabic_results)
                mode = "latin_plus_arabic"
            else:
                logger.debug("OCR Arabic reader unavailable; using Latin pass only (wanted fallback)")

        elapsed_ms = int((perf_counter() - t0) * 1000)
        final_text = _results_to_unique_words_ordered(merged)

        logger.debug(
            "OCR mode=%s latin_conf=%.2f boxes_latin=%d boxes_total=%d time_ms=%d chars=%d",
            mode,
            latin_conf,
            len(latin_results),
            len(merged),
            elapsed_ms,
            len(final_text),
        )
        return final_text
    except Exception as e:
        logger.warning("OCR extraction failed: %s", e)
        return ""
