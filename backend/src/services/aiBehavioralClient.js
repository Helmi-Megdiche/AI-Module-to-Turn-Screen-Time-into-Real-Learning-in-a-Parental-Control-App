const axios = require('axios');

const DEFAULT_AI_BEHAVIORAL_URL = 'http://127.0.0.1:8000/behavioral/analyze';
const DEFAULT_AI_BEHAVIORAL_TIMEOUT_MS = 10_000;

class AiBehavioralValidationError extends Error {
  constructor(message, detail, aiStatus) {
    super(message);
    this.name = 'AiBehavioralValidationError';
    this.detail = detail;
    this.aiStatus = aiStatus;
  }
}

class AiBehavioralFailureError extends Error {
  constructor(message, detail, aiStatus) {
    super(message);
    this.name = 'AiBehavioralFailureError';
    this.detail = detail;
    this.aiStatus = aiStatus;
  }
}

class AiBehavioralUnreachableError extends Error {
  constructor(message, detail, cause) {
    super(message);
    this.name = 'AiBehavioralUnreachableError';
    this.detail = detail;
    this.cause = cause;
  }
}

function getBehavioralUrl() {
  return process.env.AI_BEHAVIORAL_URL || DEFAULT_AI_BEHAVIORAL_URL;
}

function getBehavioralTimeoutMs() {
  const raw = process.env.AI_BEHAVIORAL_TIMEOUT_MS;
  if (raw === undefined || raw === '') {
    return DEFAULT_AI_BEHAVIORAL_TIMEOUT_MS;
  }
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) {
    return DEFAULT_AI_BEHAVIORAL_TIMEOUT_MS;
  }
  return n;
}

function extractDetail(data) {
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
  }
  if (typeof data === 'string') return data;
  return null;
}

async function callBehavioralAnalyze(payload) {
  const url = getBehavioralUrl();
  const timeout = getBehavioralTimeoutMs();
  try {
    const response = await axios.post(url, payload, {
      timeout,
      headers: { 'Content-Type': 'application/json' },
    });
    if (response?.status !== 200) {
      throw new AiBehavioralFailureError(
        'Behavioral AI service returned non-200 response',
        extractDetail(response?.data) || 'Unexpected response status',
        response?.status
      );
    }
    if (!response?.data || typeof response.data !== 'object') {
      throw new AiBehavioralFailureError(
        'Behavioral AI service returned malformed response',
        'Response body must be an object',
        response?.status
      );
    }
    return response.data;
  } catch (err) {
    if (err instanceof AiBehavioralFailureError) {
      throw err;
    }
    if (!axios.isAxiosError(err)) {
      throw new AiBehavioralFailureError(
        'Behavioral AI request failed',
        err?.message || 'Unknown failure'
      );
    }

    const status = err.response?.status;
    const detail = extractDetail(err.response?.data) || err.message;

    if (status === 400 || status === 422) {
      throw new AiBehavioralValidationError(
        'Behavioral AI payload rejected',
        detail,
        status
      );
    }
    if (status >= 500 && status <= 599) {
      throw new AiBehavioralFailureError(
        'Behavioral AI service error',
        detail,
        status
      );
    }

    const networkCode = String(err.code || '');
    const isUnreachable =
      ['ECONNREFUSED', 'ECONNABORTED', 'ETIMEDOUT', 'ENOTFOUND', 'EAI_AGAIN'].includes(networkCode) ||
      (!status && Boolean(err.request));

    if (isUnreachable) {
      throw new AiBehavioralUnreachableError(
        'Behavioral AI service unreachable',
        detail,
        err
      );
    }

    throw new AiBehavioralFailureError(
      'Behavioral AI request failed',
      detail,
      status
    );
  }
}

module.exports = {
  callBehavioralAnalyze,
  AiBehavioralValidationError,
  AiBehavioralFailureError,
  AiBehavioralUnreachableError,
};
