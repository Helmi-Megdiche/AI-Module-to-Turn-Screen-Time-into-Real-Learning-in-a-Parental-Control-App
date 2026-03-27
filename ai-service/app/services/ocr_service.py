"""
EasyOCR wrapper: one shared ``Reader`` instance (expensive to construct).

Languages: **English + Arabic** only in a single reader (EasyOCR does not allow ``ar`` with
``fr`` in the same ``lang_list``). If initialization fails, the reader stays unavailable and
``extract_text`` returns ``""`` so the rest of the service can still run (vision + moderation).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)

_reader: Any = None
_reader_init_failed: bool = False

_EASYOCR_LANGS = ["en", "ar"]


def _cuda_usable_for_easyocr() -> bool:
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def get_reader() -> Any | None:
    """Lazily construct the global EasyOCR reader, or return None if loading failed."""
    global _reader, _reader_init_failed
    if _reader_init_failed:
        return None
    if _reader is not None:
        return _reader
    import easyocr

    cuda_ok = _cuda_usable_for_easyocr()
    try:
        _reader = easyocr.Reader(_EASYOCR_LANGS, gpu=cuda_ok, verbose=False)
        logger.info("EasyOCR initialised | langs=en,ar | gpu=%s", cuda_ok)
        return _reader
    except Exception as e:
        logger.warning("Failed to load EasyOCR: %s", e)
        _reader_init_failed = True
        return None


def extract_text(pil_image: Image.Image) -> str:
    """Run OCR; return unique words (case-insensitive) sorted and joined, or \"\" if no reader."""
    reader = get_reader()
    if reader is None:
        return ""
    try:
        im = pil_image.copy()
        im.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        img_np = np.array(im)
        result = reader.readtext(img_np)
        words: set[str] = set()
        for _bbox, text, _conf in result:
            for word in text.split():
                words.add(word.lower())
        return " ".join(sorted(words)).strip()
    except Exception as e:
        logger.warning("OCR extraction failed: %s", e)
        return ""
