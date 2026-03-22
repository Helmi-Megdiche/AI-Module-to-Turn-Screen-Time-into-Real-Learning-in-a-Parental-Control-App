"""
FastAPI entrypoint for **screenshot → OCR → moderation → JSON** used by the Node backend.

Contract (must stay stable for ``backend/src/services/aiService.js``):

- ``POST /analyze`` with JSON ``{ "image": "<base64>" }`` (raw base64 or ``data:...;base64,...``).
- Response: ``text``, ``displayText``, ``matchedKeywords``, ``riskScore``, ``category``.
"""

import logging
from typing import Optional

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.analysis_orchestrator import build_analyze_response_from_plain_text
from app.services import ocr_service
from app.services.moderation_service import initialize_moderation
from app.utils.image_utils import base64_to_pil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="Parental Control AI Service")


@app.on_event("startup")
def startup_event() -> None:
    """Preload EasyOCR and the Hugging Face zero-shot model (or log degraded mode if load fails)."""
    _cuda = torch.cuda.is_available()
    _device = torch.cuda.get_device_name(0) if _cuda else "cpu"
    # Use logger (not only print) so uvicorn always shows this — prints can be easy to miss in some consoles.
    logger.info("AI_STARTUP | torch=%s | cuda=%s | device=%s", torch.__version__, _cuda, _device)
    if _cuda:
        try:
            torch.cuda.init()
            torch.ones(1, device="cuda")
        except Exception as exc:
            logger.warning("CUDA warm-up failed (EasyOCR may stay on CPU): %s", exc)
    # Block startup until OCR and moderation are initialized.
    try:
        ocr_service.get_reader()
        logger.info("EasyOCR reader ready")
    except Exception as e:
        logger.warning("Could not preload EasyOCR (will load on first request): %s", e)
    if not initialize_moderation():
        logger.error("Moderation model unavailable at startup; service running in degraded fallback-only mode")


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
    """Decode image → orchestrated OCR + moderation → API JSON."""
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

    result = build_analyze_response_from_plain_text(text or "")

    return AnalyzeResponse(
        text=result.text,
        displayText=result.display_text,
        matchedKeywords=result.matched_keywords,
        riskScore=result.risk_score,
        category=result.category,
    )


@app.get("/health")
async def health():
    """Process up-check; does not guarantee the transformer finished loading."""
    return {"status": "ok"}
