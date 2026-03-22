/**
 * Thin HTTP client for the Python AI microservice (`POST /analyze`).
 * URL and timeout come from `AI_ANALYZE_URL` and `AI_REQUEST_TIMEOUT_MS` in `.env`.
 */
const axios = require('axios');

const DEFAULT_AI_ANALYZE_URL = 'http://127.0.0.1:8000/analyze';
/** OCR + zero-shot moderation on CPU often exceeds 10s; keep in sync with `.env.example`. */
const DEFAULT_AI_REQUEST_TIMEOUT_MS = 120_000;

function getAiAnalyzeUrl() {
  return process.env.AI_ANALYZE_URL || DEFAULT_AI_ANALYZE_URL;
}

/** Milliseconds for axios; invalid env falls back to default. */
function getAiRequestTimeoutMs() {
  const raw = process.env.AI_REQUEST_TIMEOUT_MS;
  if (raw === undefined || raw === '') {
    return DEFAULT_AI_REQUEST_TIMEOUT_MS;
  }
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) {
    return DEFAULT_AI_REQUEST_TIMEOUT_MS;
  }
  return n;
}

/**
 * Sends raw Base64 (no `data:` prefix) to the AI service; returns `{ text, displayText, matchedKeywords, riskScore, category }`.
 * @throws {Error} on network failure or non-2xx — message includes HTTP status when available.
 */
async function analyzeImage(imageBase64) {
  const url = getAiAnalyzeUrl();
  const timeout = getAiRequestTimeoutMs();

  try {
    const { data } = await axios.post(
      url,
      { image: imageBase64 },
      {
        timeout,
        headers: { 'Content-Type': 'application/json' },
      }
    );

    return data;
  } catch (err) {
    if (axios.isAxiosError(err)) {
      const detail =
        err.response?.data?.detail ??
        err.response?.data?.message ??
        (typeof err.response?.data === 'string' ? err.response.data : null) ??
        err.message;
      const status = err.response?.status;
      const suffix = status ? ` (HTTP ${status})` : '';
      throw new Error(`AI service request failed${suffix}: ${detail}`);
    }
    throw new Error(`AI service request failed: ${err.message}`);
  }
}

module.exports = { analyzeImage };
