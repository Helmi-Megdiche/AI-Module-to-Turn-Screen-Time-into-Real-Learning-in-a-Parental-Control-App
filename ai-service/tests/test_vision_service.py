from __future__ import annotations

from PIL import Image

import app.services.vision_service as vision_service


def test_classify_safe_image() -> None:
    img = Image.new("RGB", (224, 224), color="white")

    def fake_pipe(_image):
        return [{"label": "sfw", "score": 0.99}, {"label": "nsfw", "score": 0.01}]

    vision_service._classifier = fake_pipe
    result = vision_service.classify_image(img)

    assert result["riskScore"] < 0.5
    assert "nsfw visual" not in result["matchedKeywords"]
