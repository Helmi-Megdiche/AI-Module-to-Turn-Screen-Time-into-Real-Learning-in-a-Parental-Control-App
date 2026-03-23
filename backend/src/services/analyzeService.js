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
  SAFE_POINTS_COOLDOWN_MINUTES,
  SAFE_POINTS_DAILY_CAP,
} = require('../config');

const EMPTY_ANALYSIS = {
  text: '',
  riskScore: 0,
  category: 'safe',
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
  return {
    text,
    riskScore,
    category,
    displayText,
    matchedKeywords,
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

/**
 * Maps continuous risk in [0,1] to a human-readable mission + points (product rule — not the same as ML “category”).
 * Bands: &lt;0.3 low, 0.3–0.7 medium, &gt;0.7 high consequence.
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

function hasAnyLabel(labels, expected) {
  if (!Array.isArray(labels) || labels.length === 0) {
    return false;
  }
  const normalized = new Set(
    labels.filter((x) => typeof x === 'string').map((x) => x.toLowerCase())
  );
  return expected.some((label) => normalized.has(label));
}

function generateInteractiveMission(riskScore, category, age, matchedKeywords = []) {
  if (riskScore > 0.7) {
    if (hasAnyLabel(matchedKeywords, ['hate speech', 'harassment'])) {
      return {
        mission: 'Complete the respectful communication quiz.',
        points: 20,
        type: 'quiz',
        difficulty: 3,
        content: {
          question: 'Which of these is a respectful way to express disagreement?',
          choices: [
            "You're stupid",
            'I disagree with your opinion',
            'Nobody likes what you say',
          ],
          correctAnswer: 1,
        },
      };
    }
    return {
      mission: 'Complete the focus mini-game challenge.',
      points: 18,
      type: 'mini_game',
      difficulty: 3,
      content: {
        game: 'reaction_tap',
        targetHits: 12,
        maxSeconds: 45,
      },
    };
  }

  if (riskScore > 0.3) {
    return {
      mission: 'Complete the puzzle mission.',
      points: 15,
      type: 'puzzle',
      difficulty: 2,
      content: {
        game: 'sudoku4x4',
        grid: [
          [0, 0, 1, 2],
          [0, 0, 0, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0],
        ],
      },
    };
  }

  return {
    mission:
      age < 10
        ? 'Do 10 jumping jacks and share one thing you learned today.'
        : 'Take a 5-minute offline break and write one useful takeaway from your activity.',
    points: 2,
    type: 'real_world',
    difficulty: 1,
    content: {
      description:
        'Do 10 jumping jacks and think about what you learned today.',
    },
  };
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

/**
 * Response shape when **no** rows are written — `analysis.id` is null, mission `status` is `preview`.
 */
async function buildPreviewAnalyzeResult({ userId, age, analysis, mission }) {
  const user = await prisma.user.findUnique({ where: { id: userId } });

  return {
    analysis: {
      id: null,
      userId,
      text: analysis.text,
      displayText: analysis.displayText,
      matchedKeywords: analysis.matchedKeywords,
      riskScore: analysis.riskScore,
      category: analysis.category,
      usedAI: analysis.usedAI,
      createdAt: null,
    },
    mission: {
      id: null,
      mission: mission.mission,
      points: mission.points,
      type: mission.type ?? 'real_world',
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
  };
}

/**
 * Single entry used by the controller: resolves analysis, chooses mission, persists when an image was sent.
 */
async function runAnalyze({ userId, age, image }) {
  const analysis = await resolveAnalysisPayload(image);
  const { text, riskScore, category, usedAI, displayText, matchedKeywords } =
    analysis;
  const generatedMission = generateInteractiveMission(
    riskScore,
    category,
    age,
    matchedKeywords
  );
  const { mission, points, type, content, difficulty } = generatedMission;
  const awardImmediately = type === 'real_world' && riskScore < 0.3;

  if (!hasProvidedImage(image)) {
    return buildPreviewAnalyzeResult({
      userId,
      age,
      analysis,
      mission: { mission, points, type, content, difficulty },
    });
  }

  return prisma.$transaction(async (tx) => {
    let user = await tx.user.findUnique({ where: { id: userId } });

    if (!user) {
      user = await tx.user.create({
        data: {
          id: userId,
          age,
          points: 0,
        },
      });
    }

    const analysis = await tx.analysis.create({
      data: {
        userId: user.id,
        text,
        displayText,
        matchedKeywords,
        riskScore,
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
      const currentSafePointsToday = Number(user.safePointsToday ?? 0);
      const needsDailyReset =
        !user.lastSafeResetDate || user.lastSafeResetDate < today;
      const safePointsToday = needsDailyReset ? 0 : currentSafePointsToday;
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

    return { analysis, mission: missionRecord, user: userUpdated };
  });
}

module.exports = { runAnalyze, missionForRiskScore, generateInteractiveMission };
