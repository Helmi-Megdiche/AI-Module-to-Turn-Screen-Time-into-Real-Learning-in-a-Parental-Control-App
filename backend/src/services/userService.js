/**
 * Database reads for the “parent dashboard”: paginated analyses/missions and roll-up summary stats.
 */
const prisma = require('../config/prisma');
const { awardAgeBadges } = require('./badgeService');
const { normalizeInterests } = require('./personalizationService');

const DEFAULT_TAKE = 20;
const MAX_TAKE = 100;

function normalizePagination({ skip, take }) {
  return {
    skip: Math.max(0, skip),
    take: Math.min(Math.max(1, take), MAX_TAKE),
  };
}

async function getUserById(userId) {
  return prisma.user.findUnique({ where: { id: userId } });
}

/** Compact profile payload for demo personalization controls. */
async function getProfile(userId) {
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      id: true,
      age: true,
      points: true,
      interests: true,
      engagementScore: true,
    },
  });
  if (!user) {
    return null;
  }

  return {
    id: user.id,
    age: Number(user.age ?? 0),
    points: Number(user.points ?? 0),
    interests: normalizeInterests(user.interests),
    engagementScore: Number(user.engagementScore ?? 0.5),
  };
}

/** Persist sanitized interests for a given user id. */
async function updateInterests(userId, interests) {
  const updated = await prisma.user.update({
    where: { id: userId },
    data: { interests },
    select: {
      id: true,
      interests: true,
      engagementScore: true,
    },
  });

  return {
    id: updated.id,
    interests: normalizeInterests(updated.interests),
    engagementScore: Number(updated.engagementScore ?? 0.5),
  };
}

/** Returns analyses + missions for the user, newest first. `null` if user does not exist. */
async function getHistory(userId, pagination) {
  const user = await getUserById(userId);
  if (!user) {
    return null;
  }

  const { skip, take } = normalizePagination(pagination);

  const [analyses, missions] = await Promise.all([
    prisma.analysis.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      skip,
      take,
    }),
    prisma.mission.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
      skip,
      take,
    }),
  ]);

  return { analyses, missions, skip, take };
}

/** Missions only — same pagination as history. */
async function getMissions(userId, pagination) {
  const user = await getUserById(userId);
  if (!user) {
    return null;
  }

  const { skip, take } = normalizePagination(pagination);

  const missions = await prisma.mission.findMany({
    where: { userId },
    orderBy: { createdAt: 'desc' },
    skip,
    take,
  });

  return { missions, skip, take };
}

/** Earned badges only, latest first. Returns `null` when user does not exist. */
async function getBadges(userId) {
  const user = await getUserById(userId);
  if (!user) {
    return null;
  }

  const userBadges = await prisma.userBadge.findMany({
    where: { userId },
    include: { badge: true },
    orderBy: { awardedAt: 'desc' },
  });

  const badges = userBadges.map((row) => ({
    id: row.badge.id,
    name: row.badge.name,
    description: row.badge.description,
    type: row.badge.type,
    requirementValue: row.badge.requirementValue,
    awardedAt: row.awardedAt,
  }));

  return { badges };
}

/**
 * Aggregate stats: total points, mission count, count of dangerous analyses, average risk over all analyses.
 */
async function getSummary(userId) {
  const user = await getUserById(userId);
  if (!user) {
    return null;
  }

  await awardAgeBadges(user.id, user.age);

  const [totalMissions, dangerousCount, avgAgg] = await Promise.all([
    prisma.mission.count({ where: { userId } }),
    prisma.analysis.count({
      where: {
        userId,
        category: 'dangerous',
      },
    }),
    prisma.analysis.aggregate({
      where: { userId },
      _avg: { riskScore: true },
    }),
  ]);

  const averageRiskScore =
    avgAgg._avg.riskScore === null || avgAgg._avg.riskScore === undefined
      ? null
      : Number(avgAgg._avg.riskScore.toFixed(4));

  const points = Number(user.points ?? 0);
  const baseLevel = Math.floor(Math.sqrt(points / 100));
  const level = baseLevel + 1;
  const pointsToNextLevel = Math.max(0, 100 * (baseLevel + 1) ** 2 - points);

  return {
    points,
    totalMissions,
    dangerousCount,
    averageRiskScore,
    level,
    levelTitle: `Level ${level}`,
    pointsToNextLevel,
  };
}

module.exports = {
  getProfile,
  updateInterests,
  getHistory,
  getMissions,
  getBadges,
  getSummary,
  DEFAULT_TAKE,
  MAX_TAKE,
};
