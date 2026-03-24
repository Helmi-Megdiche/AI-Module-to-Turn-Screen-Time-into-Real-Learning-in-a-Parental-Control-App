"""
Vision moderation service using a local NSFW+violence image classifier.

The module loads a configurable model (default ``Ateeqq/nsfw-image-detection``),
reuses it for later calls,
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

NSFW_LABEL_ALIASES = {
    "nsfw",
    "nudity",
    "pornography",
    "nudity_pornography",
}

VIOLENCE_LABEL_ALIASES = {
    "violence",
    "violent",
    "gore",
    "bloodshed",
    "gore_bloodshed_violent",
}


def get_classifier():
    """
    Return a singleton NSFW classifier pipeline.

    Returns:
        Any: Hugging Face image-classification pipeline.
    """
    global _classifier
    if _classifier is None:
        device = 0 if torch.cuda.is_available() else -1
        device_label = "cuda:0" if device == 0 else "cpu"
        model_candidates = [
            VISION_MODEL_NAME,
            "Ateeqq/nsfw-image-detection",
            "Falconsai/nsfw_image_detection",
        ]
        last_error = None

        for model_name in model_candidates:
            try:
                logger.info(
                    "Loading visual safety classifier... model=%s device=%s",
                    model_name,
                    device_label,
                )
                _classifier = pipeline(
                    "image-classification",
                    model=model_name,
                    device=device,
                )
                logger.info("Visual safety classifier ready: %s", model_name)
                break
            except Exception as exc:
                last_error = exc
                logger.warning("Could not load vision model %s: %s", model_name, exc)

        if _classifier is None:
            raise RuntimeError(
                f"Unable to load any vision model candidate: {last_error}"
            )
    return _classifier


def _normalized_label(label: str) -> str:
    return str(label).strip().lower().replace("-", "_").replace(" ", "_")


def _max_score_for_aliases(result: list[dict], aliases: set[str]) -> float:
    max_score = 0.0
    for row in result:
        label = _normalized_label(row.get("label", ""))
        score = float(row.get("score", 0.0))
        if label in aliases and score > max_score:
            max_score = score
    return max_score


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

        nsfw_score = _max_score_for_aliases(result, NSFW_LABEL_ALIASES)
        violence_score = _max_score_for_aliases(result, VIOLENCE_LABEL_ALIASES)
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
