import logging

from PIL import Image
import torch
from transformers import pipeline

logger = logging.getLogger(__name__)

_classifier = None


def get_classifier():
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
    Returns a dict:
        riskScore (float): probability of NSFW content (0-1)
        matchedKeywords (list): ["nsfw visual"] if riskScore > 0.5 else []
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
