const ALLOWED_EVENT_TYPES = new Set(['app_session', 'unlock', 'screen_on']);
const MAX_BATCH_SIZE = 500;
const MAX_EVENT_DURATION_SEC = 86400;
const MIN_STARTED_AT_MS = Date.parse('2020-01-01T00:00:00.000Z');

function parseFiniteInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    return null;
  }
  return n;
}

function normalizeEvent(rawEvent, nowMs) {
  if (!rawEvent || typeof rawEvent !== 'object' || Array.isArray(rawEvent)) {
    return { error: 'Each event must be an object' };
  }

  const eventType = typeof rawEvent.event_type === 'string' ? rawEvent.event_type : '';
  if (!ALLOWED_EVENT_TYPES.has(eventType)) {
    return { error: `Unknown event_type "${eventType}"` };
  }

  const startedAtMs = parseFiniteInt(rawEvent.started_at);
  if (startedAtMs === null) {
    return { error: 'started_at must be an integer epoch in milliseconds' };
  }
  if (startedAtMs > nowMs) {
    return { error: 'started_at cannot be in the future' };
  }
  if (startedAtMs < MIN_STARTED_AT_MS) {
    return { error: 'started_at cannot be before 2020-01-01' };
  }

  const endedAtMs =
    rawEvent.ended_at === null || rawEvent.ended_at === undefined
      ? null
      : parseFiniteInt(rawEvent.ended_at);
  if (rawEvent.ended_at !== undefined && rawEvent.ended_at !== null && endedAtMs === null) {
    return { error: 'ended_at must be an integer epoch in milliseconds when provided' };
  }
  if (endedAtMs !== null && endedAtMs < startedAtMs) {
    return { error: 'ended_at cannot be before started_at' };
  }

  const durationSec =
    rawEvent.duration_sec === null || rawEvent.duration_sec === undefined
      ? null
      : parseFiniteInt(rawEvent.duration_sec);
  if (
    rawEvent.duration_sec !== undefined &&
    rawEvent.duration_sec !== null &&
    durationSec === null
  ) {
    return { error: 'duration_sec must be an integer when provided' };
  }
  if (durationSec !== null && durationSec < 0) {
    return { error: 'duration_sec cannot be negative' };
  }
  if (durationSec !== null && durationSec > MAX_EVENT_DURATION_SEC) {
    return { error: `duration_sec cannot exceed ${MAX_EVENT_DURATION_SEC}` };
  }

  if (typeof rawEvent.app_package !== 'undefined' && rawEvent.app_package !== null) {
    if (typeof rawEvent.app_package !== 'string') {
      return { error: 'app_package must be a string when provided' };
    }
  }

  return {
    value: {
      eventType,
      appPackage: rawEvent.app_package ?? null,
      startedAt: new Date(startedAtMs),
      endedAt: endedAtMs === null ? null : new Date(endedAtMs),
      durationSec,
    },
  };
}

function validateUsageEventsPayload(payload, nowMs = Date.now()) {
  const userId = parseFiniteInt(payload?.userId);
  if (userId === null || userId <= 0) {
    return { ok: false, message: 'Invalid or missing userId (positive integer required)' };
  }

  const events = payload?.events;
  if (!Array.isArray(events)) {
    return { ok: false, message: 'events must be an array' };
  }
  if (events.length === 0) {
    return { ok: false, message: 'events cannot be empty' };
  }
  if (events.length > MAX_BATCH_SIZE) {
    return { ok: false, message: `events batch cannot exceed ${MAX_BATCH_SIZE}` };
  }

  const normalized = [];
  let rejected = 0;
  for (let i = 0; i < events.length; i += 1) {
    const parsed = normalizeEvent(events[i], nowMs);
    if (parsed.error) {
      return {
        ok: false,
        message: `Invalid event at index ${i}: ${parsed.error}`,
      };
    }
    normalized.push(parsed.value);
  }

  return {
    ok: true,
    value: { userId, events: normalized },
    rejected,
  };
}

function validateRecommendationStatus(value) {
  if (value === undefined || value === null || value === '') {
    return { ok: true, value: 'active' };
  }
  const normalized = String(value).trim().toLowerCase();
  if (!['active', 'dismissed', 'acted'].includes(normalized)) {
    return { ok: false, message: 'status must be one of active, dismissed, acted' };
  }
  return { ok: true, value: normalized };
}

module.exports = {
  ALLOWED_EVENT_TYPES,
  MAX_BATCH_SIZE,
  MAX_EVENT_DURATION_SEC,
  MIN_STARTED_AT_MS,
  validateUsageEventsPayload,
  validateRecommendationStatus,
  parseFiniteInt,
};
