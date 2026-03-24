from __future__ import annotations

from PIL import Image

import app.services.vision_service as vision_service


def test_classify_safe_image() -> None:
    img = Image.new("RGB", (224, 224), color="white")

    def fake_pipe(_image):
        return [
            {"label": "safe", "score": 0.98},
            {"label": "nsfw", "score": 0.01},
            {"label": "violence", "score": 0.01},
        ]

    vision_service._classifier = fake_pipe
    result = vision_service.classify_image(img)

    assert result["riskScore"] < 0.5
    assert "nsfw visual" not in result["matchedKeywords"]
    assert "violence visual" not in result["matchedKeywords"]


def test_classify_nsfw_image_adds_nsfw_keyword() -> None:
    img = Image.new("RGB", (224, 224), color="white")

    def fake_pipe(_image):
        return [
            {"label": "nsfw", "score": 0.91},
            {"label": "violence", "score": 0.08},
            {"label": "safe", "score": 0.01},
        ]

    vision_service._classifier = fake_pipe
    result = vision_service.classify_image(img)

    assert result["riskScore"] == 0.91
    assert "nsfw visual" in result["matchedKeywords"]
    assert "violence visual" not in result["matchedKeywords"]


def test_classify_violence_image_adds_violence_keyword() -> None:
    img = Image.new("RGB", (224, 224), color="white")

    def fake_pipe(_image):
        return [
            {"label": "violence", "score": 0.87},
            {"label": "nsfw", "score": 0.11},
            {"label": "safe", "score": 0.02},
        ]

    vision_service._classifier = fake_pipe
    result = vision_service.classify_image(img)

    assert result["riskScore"] == 0.87
    assert "violence visual" in result["matchedKeywords"]
    assert "nsfw visual" not in result["matchedKeywords"]


def test_classify_mixed_harmful_uses_max_and_both_keywords() -> None:
    img = Image.new("RGB", (224, 224), color="white")

    def fake_pipe(_image):
        return [
            {"label": "nsfw", "score": 0.76},
            {"label": "violence", "score": 0.83},
            {"label": "safe", "score": 0.01},
        ]

    vision_service._classifier = fake_pipe
    result = vision_service.classify_image(img)

    assert result["riskScore"] == 0.83
    assert "nsfw visual" in result["matchedKeywords"]
    assert "violence visual" in result["matchedKeywords"]


def test_classify_fallback_on_exception() -> None:
    img = Image.new("RGB", (224, 224), color="white")

    def broken_pipe(_image):
        raise RuntimeError("boom")

    vision_service._classifier = broken_pipe
    result = vision_service.classify_image(img)

    assert result == {"riskScore": 0.0, "matchedKeywords": []}
