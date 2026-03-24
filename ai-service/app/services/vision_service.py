"""
Vision moderation service using a local NSFW+violence image classifier.

The module loads ``ml6team/violence-and-nsfw`` once, reuses it for later calls,
and exposes ``classify_image`` to return API-compatible risk metadata with the
same public contract as before.
"""

import logging

from PIL import Image
import torch
from transformers import pipeline

from app.config import VISION_MATCHED_KEYWORDS_THRESHOLD, VISION_MODEL_NAME

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
            "Loading visual safety classifier... model=%s device=%s",
            VISION_MODEL_NAME,
            "cuda:0" if device == 0 else "cpu",
        )
        _classifier = pipeline(
            "image-classification",
            model=VISION_MODEL_NAME,
            device=device,
        )
    return _classifier


def _score_for_label(result: list[dict], label: str) -> float:
    label_lower = label.lower()
    return float(
        next(
            (
                row.get("score", 0.0)
                for row in result
                if str(row.get("label", "")).strip().lower() == label_lower
            ),
            0.0,
        )
    )


def classify_image(image: Image.Image):
    """
    Run NSFW classification on a PIL image.

    Args:
        image: Input screenshot as ``PIL.Image``.

    Returns:
        dict: ``{"riskScore": float, "matchedKeywords": list[str]}``.
        ``riskScore`` is the max of NSFW and violence scores.
        ``matchedKeywords`` includes ``nsfw visual`` and/or ``violence visual``
        when each label score is above ``VISION_MATCHED_KEYWORDS_THRESHOLD``.
    """
    try:
        pipe = get_classifier()
        result = pipe(image)

        nsfw_score = _score_for_label(result, "nsfw")
        violence_score = _score_for_label(result, "violence")
        risk_score = max(nsfw_score, violence_score)

        matched = []
        if nsfw_score > VISION_MATCHED_KEYWORDS_THRESHOLD:
            matched.append("nsfw visual")
        if violence_score > VISION_MATCHED_KEYWORDS_THRESHOLD:
            matched.append("violence visual")

        return {"riskScore": risk_score, "matchedKeywords": matched}
    except Exception as e:
        logger.error("Vision inference failed: %s", e)
        return {"riskScore": 0.0, "matchedKeywords": []}
