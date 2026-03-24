"""
Vision moderation service using a local NSFW image classifier.

The module loads ``Falconsai/nsfw_image_detection`` once, reuses it for later calls,
and exposes ``classify_image`` to return API-compatible risk metadata.
"""

import logging

from PIL import Image
import torch
from transformers import pipeline

logger = logging.getLogger(__name__)

_classifier = None


def get_classifier():
    """
    Return a singleton NSFW classifier pipeline.

    Returns:
        Any: Hugging Face image-classification pipeline.
    """
    global _classifier
    if _classifier is None:
        device = 0 if torch.cuda.is_available() else -1
        logger.info(
            "Loading NSFW image classifier... model=%s device=%s",
            "Falconsai/nsfw_image_detection",
            "cuda:0" if device == 0 else "cpu",
        )
        _classifier = pipeline(
            "image-classification",
            model="Falconsai/nsfw_image_detection",
            device=device,
        )
    return _classifier


def classify_image(image: Image.Image):
    """
    Run NSFW classification on a PIL image.

    Args:
        image: Input screenshot as ``PIL.Image``.

    Returns:
        dict: ``{"riskScore": float, "matchedKeywords": list[str]}``.
        ``matchedKeywords`` contains ``"nsfw visual"`` when score > 0.5.
    """
    try:
        pipe = get_classifier()
        result = pipe(image)
        nsfw_score = next((r["score"] for r in result if r["label"] == "nsfw"), 0.0)
        matched = ["nsfw visual"] if nsfw_score > 0.5 else []
        return {"riskScore": nsfw_score, "matchedKeywords": matched}
    except Exception as e:
        logger.error("Vision inference failed: %s", e)
        return {"riskScore": 0.0, "matchedKeywords": []}
