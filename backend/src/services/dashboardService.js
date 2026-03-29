/**
 * Pure aggregations for parent dashboard views (missions, educational signal, progress, time buckets).
 */
const prisma = require('../config/prisma');

function emptyByType() {
  return { quiz: 0, real_world: 0, mini_game: 0, puzzle: 0 };
}

/**
 * @param {number} userId
 * @param {Date} since
 * @returns {Promise<{
 *   assignedInWindow: number,
 *   completedInWindow: number,
 *   completionRate: number,
 *   byType: Record<'quiz'|'real_world'|'mini_game'|'puzzle', number>
 * }>}
 */
async function getMissionStats(userId, since) {
  const [results, assignedInWindow] = await Promise.all([
    prisma.missionResult.findMany({
      where: { userId, createdAt: { gte: since } },
      include: { mission: { select: { type: true } } },
    }),
    prisma.mission.count({
      where: { userId, createdAt: { gte: since } },
    }),
  ]);

  const byType = emptyByType();
  for (const r of results) {
    const t = r.mission?.type;
    if (t && Object.prototype.hasOwnProperty.call(byType, t)) {
      byType[t] += 1;
    }
  }

  const completedInWindow = results.length;
  const completionRate =
    assignedInWindow === 0 ? 0 : completedInWindow / assignedInWindow;

  return {
    assignedInWindow,
    completedInWindow,
    completionRate,
    byType,
  };
}

/**
 * @param {number} userId
 * @param {Date} since
 * @returns {Promise<{ educationalCount: number, avgEducationalScore: number, shareOfTotal: number }>}
 */
async function getEducationalStats(userId, since) {
  const where = { userId, createdAt: { gte: since } };

  const [total, educationalCount, avgAgg] = await Promise.all([
    prisma.analysis.count({ where }),
    prisma.analysis.count({ where: { ...where, category: 'educational' } }),
    prisma.analysis.aggregate({
      where,
      _avg: { educationalScore: true },
    }),
  ]);

  const raw = avgAgg._avg.educationalScore;
  const avgEducationalScore =
    raw === null || raw === undefined ? 0 : Number(Number(raw).toFixed(2));

  const shareOfTotal = total === 0 ? 0 : educationalCount / total;

  return {
    educationalCount,
    avgEducationalScore,
    shareOfTotal,
  };
}

/**
 * Level matches `getSummary` in `userService.js` (no `level` column on `User`).
 *
 * @param {number} userId
 * @returns {Promise<null | {
 *   points: number,
 *   level: number,
 *   completedMissions: number,
 *   badgeCount: number,
 *   engagementScore: number
 * }>}
 */
async function getProgressSnapshot(userId) {
  const user = await prisma.user.findUnique({ where: { id: userId } });
  if (!user) return null;

  const badgeCount = await prisma.userBadge.count({ where: { userId } });

  const points = Number(user.points ?? 0);
  const baseLevel = Math.floor(Math.sqrt(points / 100));
  const level = baseLevel + 1;

  return {
    points,
    level,
    completedMissions: Number(user.completedMissions ?? 0),
    badgeCount,
    engagementScore: Number(user.engagementScore ?? 0.5),
  };
}

/** @param {Date} d */
function startOfUtcDay(d) {
  return new Date(
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
  );
}

/** @param {Date} d @param {number} days */
function addUtcDays(d, days) {
  const x = new Date(d.getTime());
  x.setUTCDate(x.getUTCDate() + days);
  return x;
}

/** @param {Date} d */
function dayKeyUtc(d) {
  return d.toISOString().slice(0, 10);
}

/**
 * @param {Array<{ createdAt: Date, riskScore: number, category: string, educationalScore?: number }>} rows
 * @param {Date} fromDate
 * @param {Date} toDate
 */
function bucketByDay(rows, fromDate, toDate) {
  const start = startOfUtcDay(fromDate);
  const end = startOfUtcDay(toDate);
  if (start.getTime() > end.getTime()) {
    return [];
  }

  const groups = new Map();
  for (const row of rows) {
    const k = dayKeyUtc(row.createdAt);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(row);
  }

  const out = [];
  for (
    let d = new Date(start);
    d.getTime() <= end.getTime();
    d = addUtcDays(d, 1)
  ) {
    const t = dayKeyUtc(d);
    const list = groups.get(t) || [];
    const count = list.length;
    const dangerousCount = list.filter((r) => r.category === 'dangerous').length;
    const educationalCount = list.filter((r) => r.category === 'educational')
      .length;

    let avgRiskScore = 0;
    let maxRiskScore = 0;
    if (count > 0) {
      const scores = list.map((r) => Number(r.riskScore));
      avgRiskScore = scores.reduce((a, b) => a + b, 0) / count;
      maxRiskScore = Math.max(...scores);
    }

    out.push({
      t,
      avgRiskScore,
      maxRiskScore,
      count,
      dangerousCount,
      educationalCount,
    });
  }

  return out;
}

/** @param {Date} d */
function utcHourStart(d) {
  return new Date(
    Date.UTC(
      d.getUTCFullYear(),
      d.getUTCMonth(),
      d.getUTCDate(),
      d.getUTCHours(),
      0,
      0,
      0
    )
  );
}

/** @param {Date} d */
function hourKeyUtc(d) {
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

/** @param {Date} d @param {number} hours */
function addUtcHours(d, hours) {
  return new Date(d.getTime() + hours * 3600000);
}

/**
 * @param {Array<{ createdAt: Date, riskScore: number, category: string, educationalScore?: number }>} rows
 * @param {Date} fromDate
 * @param {Date} toDate
 */
function bucketByHour(rows, fromDate, toDate) {
  const start = utcHourStart(fromDate);
  const end = utcHourStart(toDate);
  if (start.getTime() > end.getTime()) {
    return [];
  }

  const groups = new Map();
  for (const row of rows) {
    const hk = hourKeyUtc(utcHourStart(row.createdAt));
    if (!groups.has(hk)) groups.set(hk, []);
    groups.get(hk).push(row);
  }

  const out = [];
  for (
    let d = new Date(start);
    d.getTime() <= end.getTime();
    d = addUtcHours(d, 1)
  ) {
    const t = hourKeyUtc(d);
    const list = groups.get(t) || [];
    const count = list.length;
    const dangerousCount = list.filter((r) => r.category === 'dangerous').length;
    const educationalCount = list.filter((r) => r.category === 'educational')
      .length;

    let avgRiskScore = 0;
    let maxRiskScore = 0;
    if (count > 0) {
      const scores = list.map((r) => Number(r.riskScore));
      avgRiskScore = scores.reduce((a, b) => a + b, 0) / count;
      maxRiskScore = Math.max(...scores);
    }

    out.push({
      t,
      avgRiskScore,
      maxRiskScore,
      count,
      dangerousCount,
      educationalCount,
    });
  }

  return out;
}

module.exports = {
  getMissionStats,
  getEducationalStats,
  getProgressSnapshot,
  bucketByDay,
  bucketByHour,
};
