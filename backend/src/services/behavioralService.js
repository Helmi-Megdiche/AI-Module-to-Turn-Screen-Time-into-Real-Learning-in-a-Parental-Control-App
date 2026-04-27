const prisma = require('../config/prisma');
const {
  callBehavioralAnalyze,
  AiBehavioralValidationError,
  AiBehavioralFailureError,
  AiBehavioralUnreachableError,
} = require('./aiBehavioralClient');

async function getLatestBehavioralScore(userId, windowDays) {
  const where = { userId };
  if (Number.isInteger(windowDays) && windowDays > 0) {
    where.windowDays = windowDays;
  }

  return prisma.behavioralScore.findFirst({
    where,
    orderBy: { computedAt: 'desc' },
  });
}

function normalizeContentSummary(contentSummary) {
  return contentSummary ?? {
    educationalCount: 0,
    riskyCount: 0,
    dangerousCount: 0,
    total: 0,
  };
}

function normalizeMissionSummary(missionSummary) {
  return missionSummary ?? {
    completed: 0,
    assigned: 0,
  };
}

function rankRecommendations(recommendations) {
  const severityRank = { high: 3, medium: 2, low: 1, positive: 0 };
  return [...recommendations]
    .sort((a, b) => {
      const rA = severityRank[a.severity] ?? -1;
      const rB = severityRank[b.severity] ?? -1;
      if (rA !== rB) return rB - rA;
      const tA = a.triggeringValue ?? -Infinity;
      const tB = b.triggeringValue ?? -Infinity;
      return tB - tA;
    })
    .slice(0, 3);
}

function toNaiveIsoString(date) {
  return date.toISOString().replace(/Z$/, '');
}

function _missionDifficultyToInt(value) {
  return { easy: 1, medium: 2, hard: 3 }[value] ?? 1;
}

async function analyzeUserBehavior(userId, options) {
  const ageYears = options?.ageYears;
  const windowDays = options?.windowDays ?? 14;
  const contentSummary = normalizeContentSummary(options?.contentSummary);
  const missionSummary = normalizeMissionSummary(options?.missionSummary);

  const dateTo = new Date();
  const dateFrom = new Date(dateTo.getTime() - windowDays * 86400 * 1000);

  try {
    const usageEvents = await prisma.usageEvent.findMany({
      where: {
        userId,
        startedAt: {
          gte: dateFrom,
          lte: dateTo,
        },
      },
      orderBy: {
        startedAt: 'asc',
      },
    });

    const payload = {
      userId,
      ageYears,
      windowDays,
      events: usageEvents.map((row) => ({
        eventType: row.eventType,
        startedAt: toNaiveIsoString(row.startedAt),
        durationSec: row.durationSec,
        packageName: row.appPackage ?? null,
      })),
      contentAnalysesSummary: contentSummary,
      missionSummary,
    };

    const response = await callBehavioralAnalyze(payload);

    const score = await prisma.behavioralScore.create({
      data: {
        userId,
        addictionScore: response.addictionScore,
        wellbeingScore: response.wellbeingScore,
        windowDays: response.windowDays,
        computedAt: new Date(response.computedAt),
        subscoresJson: {
          addiction: response.addictionSubscores,
          wellbeing: response.wellbeingSubscores,
        },
        recommendationsJson: response.recommendations,
      },
    });

    const topRecommendations = rankRecommendations(response.recommendations ?? []);
    const persistedRecommendations = [];
    for (const rec of topRecommendations) {
      // Snapshot strategy: each scoring run stores a new linked recommendation set.
      // Deduplication is intentionally bounded to the latest snapshot read path.
      const created = await prisma.recommendation.create({
        data: {
          userId,
          scoreSnapshotId: score.id,
          type: rec.type,
          severity: rec.severity,
          messageFr: rec.messageFr,
          actionPayload: rec.actionPayload ?? {},
          targetAudience: rec.targetAudience ?? null,
          triggeringSubscore: rec.triggeringSubscore ?? null,
          triggeringValue: rec.triggeringValue ?? null,
          status: 'active',
        },
      });
      persistedRecommendations.push(created);
    }

    const persistedMissions = [];
    for (const mission of response.missions ?? []) {
      const createdMission = await prisma.mission.create({
        data: {
          userId,
          mission: mission.descriptionFr,
          type: 'real_world',
          difficulty: _missionDifficultyToInt(mission.difficulty),
          points: mission.points,
          scoreSnapshotId: score.id,
          triggeringSubscore: mission.triggeringSubscore,
          triggeringValue: mission.triggeringValue,
          targetAudience: 'child',
          status: 'pending',
          content: null,
        },
      });
      persistedMissions.push(createdMission);
    }

    return {
      score,
      recommendations: persistedRecommendations,
      missions: persistedMissions,
    };
  } catch (err) {
    if (
      err instanceof AiBehavioralValidationError ||
      err instanceof AiBehavioralFailureError ||
      err instanceof AiBehavioralUnreachableError
    ) {
      throw err;
    }
    console.error(err);
    throw err;
  }
}

async function getCurrentRecommendations(userId) {
  const latestScore = await prisma.behavioralScore.findFirst({
    where: { userId },
    orderBy: { computedAt: 'desc' },
  });
  if (!latestScore) {
    return [];
  }
  return prisma.recommendation.findMany({
    where: {
      userId,
      scoreSnapshotId: latestScore.id,
      status: 'active',
    },
    orderBy: { createdAt: 'asc' },
  });
}

async function getCurrentBehavioralMissions(userId) {
  const latestScore = await prisma.behavioralScore.findFirst({
    where: { userId },
    orderBy: { computedAt: 'desc' },
  });
  if (!latestScore) {
    return [];
  }
  return prisma.mission.findMany({
    where: {
      userId,
      scoreSnapshotId: latestScore.id,
      status: 'pending',
    },
    orderBy: { createdAt: 'asc' },
  });
}

module.exports = {
  getLatestBehavioralScore,
  analyzeUserBehavior,
  getCurrentRecommendations,
  getCurrentBehavioralMissions,
  rankRecommendations,
};
