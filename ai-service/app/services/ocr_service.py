"""EasyOCR wrapper — reader is heavy, so we build it once."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_reader: Any = None


def get_reader():
    global _reader
    if _reader is None:
        import easyocr

        # gpu=False keeps laptops without CUDA happy; flip via env later if needed
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


def extract_text(pil_image: Image.Image) -> str:
    reader = get_reader()
    arr = np.array(pil_image)
    # Each item is (box, text, confidence)
    result = reader.readtext(arr)
    texts = [item[1] for item in result]
    return " ".join(texts).strip()
