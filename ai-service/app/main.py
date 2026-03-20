"""
FastAPI entrypoint for screenshot OCR + keyword risk scoring.
Matches the Node backend contract: POST /analyze { "image": "<base64>" }.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services import ocr_service
from app.services.risk_scoring import (
    build_display_text,
    category_from_score,
    compute_risk_score,
    matched_keywords,
)
from app.utils.image_utils import base64_to_pil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up EasyOCR once so the first user request isn't 30s+ on cold start
    try:
        ocr_service.get_reader()
        logger.info("EasyOCR reader ready")
    except Exception as e:
        logger.warning("Could not preload EasyOCR (will load on first request): %s", e)
    yield


app = FastAPI(title="Parental Control AI Service", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Optional so we can return 400 ourselves when the key is absent (instead of 422)
    image: Optional[str] = Field(default=None, description="Base64-encoded image (no data: URL prefix)")


class AnalyzeResponse(BaseModel):
    # Raw OCR (audit / what was actually read)
    text: str
    # Same string with fuzzy tokens replaced by canonical keywords — show this to parents
    displayText: str
    matchedKeywords: list[str]
    riskScore: float
    category: str


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest):
    if body.image is None:
        raise HTTPException(status_code=400, detail="Missing `image` field")
    if not str(body.image).strip():
        raise HTTPException(status_code=400, detail="Empty `image` field")

    try:
        pil = base64_to_pil(body.image.strip())
    except Exception as e:
        logger.exception("Invalid base64 image")
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid base64 image. Paste real base64 bytes (or a data: URL), "
                "not the Swagger placeholder word 'string'. "
                f"Details: {e}"
            ),
        ) from e

    try:
        text = ocr_service.extract_text(pil)
    except Exception as e:
        logger.exception("OCR failed")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}") from e

    raw = text or ""
    matches = matched_keywords(raw)
    risk_score = compute_risk_score(len(matches))
    category = category_from_score(risk_score)

    return AnalyzeResponse(
        text=raw,
        displayText=build_display_text(raw),
        matchedKeywords=matches,
        riskScore=risk_score,
        category=category,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
