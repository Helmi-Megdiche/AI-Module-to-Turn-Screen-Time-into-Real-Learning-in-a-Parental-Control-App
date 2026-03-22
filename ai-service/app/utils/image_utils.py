"""
Helpers to turn browser/Node base64 strings into RGB ``PIL.Image`` objects for OCR.

Accepts either raw base64 or a full ``data:image/...;base64,...`` data URL.
"""

import base64
import io

from PIL import Image


def _normalize_base64(image_b64: str) -> str:
    """Strip data-URL prefix and fix padding — browsers often send data:image/png;base64,..."""
    s = image_b64.strip()
    if s.startswith("data:") and "base64," in s:
        s = s.split("base64,", 1)[1].strip()
    # Standard base64 length must be a multiple of 4
    pad = (-len(s)) % 4
    if pad:
        s += "=" * pad
    return s


def base64_to_pil(image_b64: str) -> Image.Image:
    """Decode, open with Pillow, and convert to RGB (EasyOCR expects a consistent mode)."""
    normalized = _normalize_base64(image_b64)
    # validate=True catches garbage early; padding fix above fixes most paste issues
    raw = base64.b64decode(normalized, validate=True)
    return Image.open(io.BytesIO(raw)).convert("RGB")
