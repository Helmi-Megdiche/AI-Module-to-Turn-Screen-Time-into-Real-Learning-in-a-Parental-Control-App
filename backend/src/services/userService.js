/**
 * Database reads for the “parent dashboard”: paginated analyses/missions and roll-up summary stats.
 */
const prisma = require('../config/prisma');

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

/**
 * Aggregate stats: total points, mission count, count of dangerous analyses, average risk over all analyses.
 */
async function getSummary(userId) {
  const user = await getUserById(userId);
  if (!user) {
    return null;
  }

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

  return {
    points: user.points,
    totalMissions,
    dangerousCount,
    averageRiskScore,
  };
}

module.exports = {
  getHistory,
  getMissions,
  getSummary,
  DEFAULT_TAKE,
  MAX_TAKE,
};
