const prisma = require('../config/prisma');
const aiService = require('./aiService');

const EMPTY_ANALYSIS = {
  text: '',
  riskScore: 0,
  category: 'safe',
};

function hasProvidedImage(image) {
  return typeof image === 'string' && image.trim().length > 0;
}

function isValidAiResponse(data) {
  if (!data || typeof data !== 'object') return false;
  if (typeof data.text !== 'string') return false;
  if (typeof data.category !== 'string') return false;
  const r = Number(data.riskScore);
  if (!Number.isFinite(r)) return false;
  return true;
}

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
  } catch {
    throw new Error('AI analysis failed');
  }

  if (!isValidAiResponse(raw)) {
    throw new Error('AI analysis failed');
  }

  return { ...normalizeAiResponse(raw), usedAI: true };
}

function missionForRiskScore(riskScore) {
  if (riskScore < 0.3) {
    return { mission: 'Continue your activity responsibly', points: 2 };
  }
  if (riskScore <= 0.7) {
    return { mission: 'Take a 10-minute break', points: 5 };
  }
  return { mission: 'Go outside for 20 minutes', points: 10 };
}

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
      mission: mission.mission,
      points: mission.points,
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

async function runAnalyze({ userId, age, image }) {
  const analysis = await resolveAnalysisPayload(image);
  const { text, riskScore, category, usedAI, displayText, matchedKeywords } =
    analysis;
  const { mission, points } = missionForRiskScore(riskScore);

  if (!hasProvidedImage(image)) {
    return buildPreviewAnalyzeResult({
      userId,
      age,
      analysis,
      mission: { mission, points },
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

    console.log(`[ANALYSIS] User ${userId} - Risk processed`);

    const missionRecord = await tx.mission.create({
      data: {
        userId: user.id,
        mission,
        points,
      },
    });

    const userUpdated = await tx.user.update({
      where: { id: user.id },
      data: {
        points: { increment: points },
      },
    });

    return { analysis, mission: missionRecord, user: userUpdated };
  });
}

module.exports = { runAnalyze };
