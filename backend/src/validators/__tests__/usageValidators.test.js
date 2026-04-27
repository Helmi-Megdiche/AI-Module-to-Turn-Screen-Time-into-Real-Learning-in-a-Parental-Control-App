const {
  MAX_BATCH_SIZE,
  MAX_EVENT_DURATION_SEC,
  validateUsageEventsPayload,
  validateRecommendationStatus,
} = require('../usageValidators');

describe('usageValidators.validateUsageEventsPayload', () => {
  const nowMs = Date.parse('2026-04-20T00:00:00.000Z');
  const validPayload = {
    userId: 1,
    events: [
      {
        event_type: 'app_session',
        app_package: 'com.example.app',
        started_at: nowMs - 60_000,
        ended_at: nowMs - 10_000,
        duration_sec: 50,
      },
    ],
  };

  test('accepts valid payload', () => {
    const out = validateUsageEventsPayload(validPayload, nowMs);
    expect(out.ok).toBe(true);
    expect(out.value.events).toHaveLength(1);
  });

  test('rejects empty batch', () => {
    const out = validateUsageEventsPayload({ userId: 1, events: [] }, nowMs);
    expect(out.ok).toBe(false);
    expect(out.message).toMatch(/cannot be empty/i);
  });

  test('rejects oversized batch', () => {
    const events = Array.from({ length: MAX_BATCH_SIZE + 1 }, () => ({
      event_type: 'unlock',
      started_at: nowMs - 10_000,
    }));
    const out = validateUsageEventsPayload({ userId: 1, events }, nowMs);
    expect(out.ok).toBe(false);
    expect(out.message).toMatch(/cannot exceed/i);
  });

  test('rejects unknown event type', () => {
    const out = validateUsageEventsPayload(
      {
        userId: 1,
        events: [{ event_type: 'mystery', started_at: nowMs - 10_000 }],
      },
      nowMs
    );
    expect(out.ok).toBe(false);
    expect(out.message).toMatch(/Unknown event_type/i);
  });

  test('rejects future started_at', () => {
    const out = validateUsageEventsPayload(
      {
        userId: 1,
        events: [{ event_type: 'unlock', started_at: nowMs + 1 }],
      },
      nowMs
    );
    expect(out.ok).toBe(false);
    expect(out.message).toMatch(/future/i);
  });

  test('rejects too-old started_at', () => {
    const out = validateUsageEventsPayload(
      {
        userId: 1,
        events: [{ event_type: 'unlock', started_at: Date.parse('2019-12-31T00:00:00.000Z') }],
      },
      nowMs
    );
    expect(out.ok).toBe(false);
    expect(out.message).toMatch(/before 2020-01-01/i);
  });

  test('rejects overlong duration', () => {
    const out = validateUsageEventsPayload(
      {
        userId: 1,
        events: [
          {
            event_type: 'app_session',
            started_at: nowMs - 1000,
            duration_sec: MAX_EVENT_DURATION_SEC + 1,
          },
        ],
      },
      nowMs
    );
    expect(out.ok).toBe(false);
    expect(out.message).toMatch(/cannot exceed/i);
  });
});

describe('usageValidators.validateRecommendationStatus', () => {
  test('defaults to active', () => {
    expect(validateRecommendationStatus(undefined)).toEqual({
      ok: true,
      value: 'active',
    });
  });

  test('accepts valid status', () => {
    expect(validateRecommendationStatus('dismissed')).toEqual({
      ok: true,
      value: 'dismissed',
    });
  });

  test('rejects invalid status', () => {
    const out = validateRecommendationStatus('other');
    expect(out.ok).toBe(false);
  });
});
