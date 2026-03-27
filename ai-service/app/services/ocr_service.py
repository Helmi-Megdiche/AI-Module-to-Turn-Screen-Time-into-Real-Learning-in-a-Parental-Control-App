"""
EasyOCR wrapper: one shared ``Reader`` instance (expensive to construct).

Languages: English, French, Arabic. GPU is used only when CUDA is verified usable.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)

_reader: Any = None

_EASYOCR_LANGS = ["en", "fr", "ar"]


def _cuda_usable_for_easyocr() -> bool:
    """
    EasyOCR only uses GPU when ``gpu=True`` *and* ``torch.cuda.is_available()`` inside its Reader.
    Warm up CUDA here so the driver is ready before Reader runs (helps some Windows/uvicorn setups).
    """
    if not torch.cuda.is_available() or torch.cuda.device_count() < 1:
        return False
    try:
        torch.cuda.init()
        _ = torch.zeros(1, device="cuda")
        del _
        return True
    except Exception as exc:
        logger.warning("CUDA not usable for EasyOCR, falling back to CPU: %s", exc)
        return False


def get_reader():
    """Lazily construct the global EasyOCR reader (GPU if CUDA available, else CPU)."""
    global _reader
    if _reader is None:
        import easyocr

        cuda_ok = _cuda_usable_for_easyocr()
        logger.info(
            "EasyOCR initialised | langs=%s | gpu=%s | torch=%s | cuda_available=%s",
            list(_EASYOCR_LANGS),
            cuda_ok,
            torch.__version__,
            torch.cuda.is_available(),
        )
        _reader = easyocr.Reader(_EASYOCR_LANGS, gpu=cuda_ok, verbose=False)
    return _reader


def extract_text(pil_image: Image.Image) -> str:
    """Run detection+recognition, join line texts with spaces, strip ends."""
    reader = get_reader()
    im = pil_image.copy()
    im.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    arr = np.array(im)
    result = reader.readtext(arr)
    texts = [item[1] for item in result]
    return " ".join(texts).strip()