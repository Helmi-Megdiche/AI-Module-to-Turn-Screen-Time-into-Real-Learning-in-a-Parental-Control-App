/**
 * Core “analyze” workflow: optional AI call, mission selection from risk score, Prisma persistence.
 *
 * - **No image:** returns a neutral “preview” response (no DB write) — used by the demo when skipping upload.
 * - **With image:** calls Python `/analyze`, then stores `Analysis` + `Mission` and increments `User.points` in one transaction.
 */
const prisma = require('../config/prisma');
const aiService = require('./aiService');
const { awardPointBadges } = require('./badgeService');
const {
  selectMissionType,
  computeDifficulty,
} = require('./personalizationService');
const { generateMissionPayload } = require('./missionGenerators');
const {
  SAFE_POINTS_COOLDOWN_MINUTES,
  SAFE_POINTS_DAILY_CAP,
  DANGEROUS_THRESHOLD,
} = require('../config');

// === Analysis payload guards and normalization ===

const EMPTY_ANALYSIS = {
  text: '',
  riskScore: 0,
  category: 'safe',
  educationalScore: 0.0,
};

/** True when the client sent a non-empty base64 string. */
function hasProvidedImage(image) {
  return typeof image === 'string' && image.trim().length > 0;
}

/** Minimal shape check on the Python JSON before trusting it. */
function isValidAiResponse(data) {
  if (!data || typeof data !== 'object') return false;
  if (typeof data.text !== 'string') return false;
  if (typeof data.category !== 'string') return false;
  const r = Number(data.riskScore);
  if (!Number.isFinite(r)) return false;
  return true;
}

/** Picks typed fields and coerces `matchedKeywords` to a string array. */
function normalizeAiResponse(data) {
  const text = data.text;
  const riskScore = Number(data.riskScore);
  const category = data.category;
  const displayText =
    typeof data.displayText === 'string' ? data.displayText : text;
  const matchedKeywords = Array.isArray(data.matchedKeywords)
    ? data.matchedKeywords.filter((x) => typeof x === 'string')
    : [];
  const educationalScore =
    typeof data.educationalScore === 'number' ? data.educationalScore : 0.0;
  return {
    text,
    riskScore,
    category,
    displayText,
    matchedKeywords,
    educationalScore,
  };
}

/**
 * Either builds an empty “no AI” analysis, or calls `aiService.analyzeImage` and normalizes the result.
 */
async function resolveAnalysisPayload(image) {
  if (!hasProvidedImage(image)) {
    return {
      ...EMPTY_ANALYSIS,
      usedAI: false,
      displayText: '',
      matchedKeywords: [],
    };
  }

  let raw;
  try {
    raw = await aiService.analyzeImage(image.trim());
  } catch (err) {
    throw err instanceof Error ? err : new Error(String(err));
  }

  if (!isValidAiResponse(raw)) {
    throw new Error('AI analysis failed: invalid response from AI service');
  }

  return { ...normalizeAiResponse(raw), usedAI: true };
}

// === Exposure frequency (fréquence d'exposition) ===

/**
 * @param {number} userId
 * @param {Date} start Inclusive lower bound on `createdAt`.
 * @param {Date} end Upper bound on `createdAt` (inclusive if `endExclusive` is false, else exclusive).
 * @param {{ endExclusive?: boolean }} [opts]
 * @returns {Promise<{
 *   total: number,
 *   riskyCount: number,
 *   dangerousCount: number,
 *   exposureRate: number,
 *   lastDangerousAt: Date | null
 * }>}
 */
async function _getExposureStatsForWindow(userId, start, end, opts = {}) {
  const endExclusive = Boolean(opts.endExclusive);
  const createdAt = endExclusive ? { gte: start, lt: end } : { gte: start, lte: end };

  const rows = await prisma.analysis.findMany({
    where: { userId, createdAt },
    select: { category: true },
  });

  const total = rows.length;
  let riskyCount = 0;
  let dangerousCount = 0;
  for (const row of rows) {
    if (row.category === 'risky') riskyCount += 1;
    else if (row.category === 'dangerous') dangerousCount += 1;
  }

  const exposureRate =
    total === 0 ? 0 : (riskyCount + dangerousCount) / total;

  const lastDangerous = await prisma.analysis.findFirst({
    where: {
      userId,
      createdAt,
      category: 'dangerous',
    },
    orderBy: { createdAt: 'desc' },
    select: { createdAt: true },
  });

  return {
    total,
    riskyCount,
    dangerousCount,
    exposureRate,
    lastDangerousAt: lastDangerous ? lastDangerous.createdAt : null,
  };
}

/**
 * Rolling-window exposure stats for a user (CDC §4.4 style signal).
 *
 * @param {number} userId
 * @param {number} [windowMinutes=1440] Lookback window in minutes (e.g. 60, 1440, 10080).
 * @returns {Promise<{
 *   total: number,
 *   riskyCount: number,
 *   dangerousCount: number,
 *   exposureRate: number,
 *   lastDangerousAt: Date | null
 * }>}
 */
async function getRecentExposureStats(userId, windowMinutes = 1440) {
  const now = new Date();
  const start = new Date(now.getTime() - windowMinutes * 60 * 1000);
  return _getExposureStatsForWindow(userId, start, now, { endExclusive: false });
}

/**
 * Compares exposure rate in the latest window vs the immediately preceding window of equal length.
 *
 * @param {number} userId
 * @param {number} [windowMinutes=1440]
 * @returns {Promise<'increasing'|'decreasing'|'stable'>}
 */
async function getExposureTrend(userId, windowMinutes = 1440) {
  const now = new Date();
  const windowMs = windowMinutes * 60 * 1000;
  const currentStart = new Date(now.getTime() - windowMs);
  const prevStart = new Date(now.getTime() - 2 * windowMs);

  const [current, previous] = await Promise.all([
    _getExposureStatsForWindow(userId, currentStart, now, { endExclusive: false }),
    _getExposureStatsForWindow(userId, prevStart, currentStart, { endExclusive: true }),
  ]);

  const cur = current.exposureRate;
  const prev = previous.exposureRate;

  if (cur > prev * 1.1) return 'increasing';
  if (cur < prev * 0.9) return 'decreasing';
  return 'stable';
}

// === Mission generation ===

/**
 * Maps continuous risk in [0,1] to a human-readable mission + points (product rule — not the same as ML “category”).
 * Bands: &lt;0.3 low, 0.3–0.7 medium, &gt;0.7 high consequence.
 *
 * @param {number} riskScore Risk value in [0, 1].
 * @returns {{ mission: string, points: number }} Legacy mission text and base points.
 */
function missionForRiskScore(riskScore) {
  if (riskScore < 0.3) {
    return { mission: 'Continue your activity responsibly', points: 2 };
  }
  if (riskScore <= 0.7) {
    return { mission: 'Take a 10-minute break', points: 5 };
  }
  return { mission: 'Go outside for 20 minutes', points: 10 };
}

/**
 * Builds a mission payload (legacy + interactive metadata) from the current analysis.
 *
 * @param {number} riskScore Continuous risk score from AI/fallback moderation.
 * @param {string} category Risk category label (`safe`, `risky`, `dangerous`).
 * @param {number} age Child age, used as default when no user profile exists.
 * @param {string[]} [matchedKeywords=[]] Moderation labels used for specialized mission selection.
 * @param {{ age?: number, interests?: unknown, engagementScore?: number }} [userProfile={}] Optional user profile for personalization.
 * @returns {{
 *   mission: string,
 *   points: number,
 *   type: string,
 *   game: string|null,
 *   difficulty: number,
 *   reward: { basePoints: number, maxBonus: number },
 *   content: Record<string, unknown>
 * }} Mission payload to store and return to the frontend.
 */
function generateInteractiveMission(
  riskScore,
  category,
  age,
  matchedKeywords = [],
  userProfile = {}
) {
  const profile = {
    age: Number.isFinite(Number(userProfile?.age)) ? Number(userProfile.age) : age,
    interests: userProfile?.interests ?? [],
    engagementScore: Number.isFinite(Number(userProfile?.engagementScore))
      ? Number(userProfile.engagementScore)
      : 0.5,
  };
  const missionType = selectMissionType(profile, riskScore, category);
  const difficulty = computeDifficulty(profile);
  return generateMissionPayload({
    missionType,
    riskScore,
    age: profile.age,
    matchedKeywords,
    difficulty,
  });
}

// === Safe mission anti-farming helpers ===

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

// === Public service entrypoint ===

/**
 * Response shape when **no** rows are written — `analysis.id` is null, mission `status` is `preview`.
 */
async function buildPreviewAnalyzeResult({
  userId,
  age,
  analysis,
  mission,
  exposureBoost = false,
}) {
  const user = await prisma.user.findUnique({ where: { id: userId } });

  return {
    analysis: {
      id: null,
      userId,
      text: analysis.text,
      displayText: analysis.displayText,
      matchedKeywords: analysis.matchedKeywords,
      riskScore: analysis.riskScore,
      educationalScore: analysis.educationalScore ?? 0.0,
      category: analysis.category,
      usedAI: analysis.usedAI,
      createdAt: null,
    },
    mission: {
      id: null,
      mission: mission.mission,
      points: mission.points,
      type: mission.type ?? 'real_world',
      game: mission.game ?? null,
      reward: mission.reward ?? null,
      content: mission.content ?? null,
      difficulty: mission.difficulty ?? 1,
      status: 'preview',
    },
    user: user ?? {
      id: userId,
      age,
      points: 0,
      createdAt: null,
    },
    exposureBoost,
  };
}

/**
 * Single entry used by the controller: resolves analysis, chooses mission, persists when an image was sent.
 *
 * @param {{ userId: number, age: number, image?: string }} input Analyze payload from controller.
 * @returns {Promise<{
 *   analysis: object,
 *   mission: object,
 *   user: object,
 *   exposureBoost: boolean,
 *   educationalScore: number
 * }>} Created DB rows (or preview-shaped objects when no image is sent).
 */
async function runAnalyze({ userId, age, image }) {
  const analysis = await resolveAnalysisPayload(image);
  const {
    text,
    riskScore,
    category,
    usedAI,
    displayText,
    matchedKeywords,
    educationalScore,
  } = analysis;

  if (!hasProvidedImage(image)) {
    const existingUser = await prisma.user.findUnique({ where: { id: userId } });
    const generatedMission = generateInteractiveMission(
      riskScore,
      category,
      age,
      matchedKeywords,
      existingUser ?? { age, interests: [], engagementScore: 0.5 }
    );
    const { mission, points, type, game, reward, content, difficulty } = generatedMission;
    return buildPreviewAnalyzeResult({
      userId,
      age,
      analysis,
      mission: { mission, points, type, game, reward, content, difficulty },
      exposureBoost: false,
    });
  }

  // Exposure boost (CDC §4.4 — fréquence d'exposition)
  const stats = await getRecentExposureStats(userId, 60);
  const BOOST_THRESHOLD = 0.5;
  const BOOST_AMOUNT = 0.15;
  const exposureBoost =
    stats.exposureRate > BOOST_THRESHOLD && riskScore < DANGEROUS_THRESHOLD;
  const adjustedRiskScore = exposureBoost
    ? Math.min(riskScore + BOOST_AMOUNT, 0.99)
    : riskScore;

  return prisma.$transaction(async (tx) => {
    let user = await tx.user.findUnique({ where: { id: userId } });

    if (!user) {
      user = await tx.user.create({
        data: {
          id: userId,
          age,
          points: 0,
          interests: [],
          engagementScore: 0.5,
        },
      });
    }

    const generatedMission = generateInteractiveMission(
      adjustedRiskScore,
      category,
      age,
      matchedKeywords,
      user
    );
    const { mission, points, type, content, difficulty } = generatedMission;
    const awardImmediately = type === 'real_world' && riskScore < 0.3;

    const analysis = await tx.analysis.create({
      data: {
        userId: user.id,
        text,
        displayText,
        matchedKeywords,
        riskScore,
        educationalScore,
        category,
        usedAI,
      },
    });

    const missionRecord = await tx.mission.create({
      data: {
        userId: user.id,
        mission,
        points,
        type,
        content,
        difficulty,
      },
    });

    let userUpdated = user;
    if (awardImmediately) {
      const now = new Date();
      const today = startOfDay(now);
      // Reset daily safe counters once per new day before evaluating cooldown/cap.
      const currentSafePointsToday = Number(user.safePointsToday ?? 0);
      const needsDailyReset =
        !user.lastSafeResetDate || user.lastSafeResetDate < today;
      const safePointsToday = needsDailyReset ? 0 : currentSafePointsToday;
      // Safe points are awarded only when both the cooldown and daily cap allow it.
      const cooldownMs = SAFE_POINTS_COOLDOWN_MINUTES * 60 * 1000;
      const cooldownPassed =
        !user.lastSafeMissionAt || now - user.lastSafeMissionAt >= cooldownMs;
      const withinDailyCap = safePointsToday + points <= SAFE_POINTS_DAILY_CAP;
      const shouldAward = cooldownPassed && withinDailyCap;

      const userUpdateData = {};
      if (needsDailyReset) {
        userUpdateData.safePointsToday = 0;
        userUpdateData.lastSafeResetDate = today;
      }
      if (shouldAward) {
        userUpdateData.points = { increment: points };
        userUpdateData.lastSafeMissionAt = now;
        userUpdateData.safePointsToday = safePointsToday + points;
        userUpdateData.lastSafeResetDate = today;
      }

      if (Object.keys(userUpdateData).length > 0) {
        userUpdated = await tx.user.update({
          where: { id: user.id },
          data: userUpdateData,
        });
        if (shouldAward) {
          await awardPointBadges(user.id, Number(user.points ?? 0), Number(userUpdated.points ?? 0), tx);
        }
      }
    }

    return {
      analysis,
      mission: missionRecord,
      user: userUpdated,
      exposureBoost,
      educationalScore,
    };
  });
}

module.exports = {
  runAnalyze,
  missionForRiskScore,
  generateInteractiveMission,
  getRecentExposureStats,
  getExposureTrend,
};
