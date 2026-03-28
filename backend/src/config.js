const DEFAULT_SAFE_POINTS_COOLDOWN_MINUTES = 5;
const DEFAULT_SAFE_POINTS_DAILY_CAP = 10;
const DEFAULT_DANGEROUS_THRESHOLD = 0.85;

function intFromEnv(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') {
    return fallback;
  }
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value) || value < 0) {
    return fallback;
  }
  return value;
}

function floatFromEnv(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') {
    return fallback;
  }
  const value = Number.parseFloat(raw);
  if (!Number.isFinite(value)) {
    return fallback;
  }
  return value;
}

/** Aligns with `ai-service` `MODERATION_DANGEROUS_THRESHOLD` (zero-shot dangerous band). */
const DANGEROUS_THRESHOLD = floatFromEnv(
  'MODERATION_DANGEROUS_THRESHOLD',
  DEFAULT_DANGEROUS_THRESHOLD
);

const SAFE_POINTS_COOLDOWN_MINUTES = intFromEnv(
  'SAFE_POINTS_COOLDOWN_MINUTES',
  DEFAULT_SAFE_POINTS_COOLDOWN_MINUTES
);

const SAFE_POINTS_DAILY_CAP = intFromEnv(
  'SAFE_POINTS_DAILY_CAP',
  DEFAULT_SAFE_POINTS_DAILY_CAP
);

module.exports = {
  SAFE_POINTS_COOLDOWN_MINUTES,
  SAFE_POINTS_DAILY_CAP,
  DANGEROUS_THRESHOLD,
};
