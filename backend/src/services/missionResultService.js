/**
 * Mission game-result workflow:
 * - validates mission ownership/state,
 * - computes performance bonus by mission type,
 * - stores MissionResult,
 * - auto-completes mission and awards points/badges in one transaction.
 */
const prisma = require('../config/prisma');
const { awardMissionBadges, awardPointBadges } = require('./badgeService');

// === Bonus calculation ===

function extractReward(mission) {
  const reward =
    mission?.reward && typeof mission.reward === 'object'
      ? mission.reward
      : mission?.content && typeof mission.content === 'object'
      ? mission.content.reward
      : null;
  const basePoints = Number.isFinite(Number(reward?.basePoints))
    ? Number(reward.basePoints)
    : Number(mission?.points ?? 0);
  const maxBonus = Number.isFinite(Number(reward?.maxBonus))
    ? Math.max(0, Number(reward.maxBonus))
    : null;
  return { basePoints, maxBonus };
}

/**
 * Calculates extra points earned from mission performance.
 *
 * @param {{ type: string }} mission Mission metadata containing interactive type.
 * @param {{ score?: number, success: boolean, timeSpent?: number }} result Submitted game outcome.
 * @returns {number} Bonus points (>= 0) added to mission base points.
 */
function calculateBonus(mission, result) {
  const { score, success, timeSpent } = result;
  if (!success) return 0;

  let bonus = 0;
  switch (mission.type) {
    case 'quiz':
      if (score === 1) bonus = 5;
      break;
    case 'puzzle':
      if (Number.isFinite(Number(timeSpent))) {
        const timeBonus = Math.max(0, 30 - timeSpent);
        bonus = timeBonus / 2;
      }
      break;
    case 'mini_game':
      if (score >= 2) bonus = 10;
      else if (score === 1) bonus = 5;
      break;
    default:
      bonus = 0;
  }
  const { maxBonus } = extractReward(mission);
  const cappedBonus = maxBonus === null ? bonus : Math.min(bonus, maxBonus);
  return Math.max(0, Math.floor(cappedBonus));
}

function computeEngagementScore(recentResults) {
  if (!Array.isArray(recentResults) || recentResults.length === 0) {
    return 0.5;
  }
  const total = recentResults.length;
  const successes = recentResults.filter((row) => Boolean(row.success)).length;
  const completionRate = successes / total;
  const successRate = successes / total;
  let streak = 0;
  for (const row of recentResults) {
    if (!row.success) break;
    streak += 1;
  }
  const streakFactor = Math.min(streak / 10, 1);
  const engagementScore =
    0.4 * completionRate + 0.3 * successRate + 0.3 * streakFactor;
  return Number(engagementScore.toFixed(4));
}

// === Mission result submission ===

/**
 * Persists one interactive mission result and awards points exactly once.
 *
 * @param {number|string} missionId Mission id from request body.
 * @param {number|string} userId User id from request body.
 * @param {{ score?: number, success: boolean, timeSpent?: number }} result Client-submitted mission outcome.
 * @returns {Promise<{
 *   earnedPoints: number,
 *   bonusPoints: number,
 *   missionResult: object,
 *   mission: object
 * }>} Stored mission result details and updated mission status.
 */
async function submitResult(missionId, userId, result) {
  const missionIdInt = Number(missionId);
  const userIdInt = Number(userId);
  const { score, success, timeSpent } = result;

  return prisma.$transaction(async (tx) => {
    const mission = await tx.mission.findUnique({
      where: { id: missionIdInt },
      include: { user: true },
    });
    if (!mission) {
      const err = new Error('Mission not found');
      err.code = 'MISSION_NOT_FOUND';
      throw err;
    }
    if (mission.userId !== userIdInt) {
      const err = new Error('Mission does not belong to user');
      err.code = 'MISSION_USER_MISMATCH';
      throw err;
    }
    if (mission.status === 'completed') {
      const err = new Error('Mission already completed');
      err.code = 'MISSION_ALREADY_COMPLETED';
      throw err;
    }

    const existingResult = await tx.missionResult.findFirst({
      where: { missionId: missionIdInt, userId: userIdInt },
      select: { id: true },
    });
    if (existingResult) {
      const err = new Error('Mission result already submitted');
      err.code = 'MISSION_RESULT_ALREADY_SUBMITTED';
      throw err;
    }

    const reward = extractReward(mission);
    const bonus = calculateBonus(mission, { score, success, timeSpent });
    const earnedPoints = reward.basePoints + bonus;

    const missionResult = await tx.missionResult.create({
      data: {
        missionId: missionIdInt,
        userId: userIdInt,
        score: score ?? null,
        success,
        timeSpent: timeSpent ?? null,
        bonusPoints: bonus,
        earnedPoints,
      },
    });

    const updatedMission = await tx.mission.update({
      where: { id: missionIdInt },
      data: { status: 'completed' },
    });

    const recentResults = await tx.missionResult.findMany({
      where: { userId: userIdInt },
      orderBy: { createdAt: 'desc' },
      take: 10,
      select: { success: true },
    });
    const engagementScore = computeEngagementScore(recentResults);

    const userUpdated = await tx.user.update({
      where: { id: userIdInt },
      data: {
        points: { increment: earnedPoints },
        completedMissions: { increment: 1 },
        engagementScore,
      },
    });

    const previousPoints = Number(mission.user?.points ?? 0);
    const newPoints = Number(userUpdated.points ?? previousPoints);
    const previousCompleted = Number(mission.user?.completedMissions ?? 0);
    const newCompleted = Number(userUpdated.completedMissions ?? previousCompleted);
    // Badge checks are idempotent and use threshold crossing (previous -> new).
    await awardPointBadges(userIdInt, previousPoints, newPoints, tx);
    await awardMissionBadges(userIdInt, previousCompleted, newCompleted, tx);

    return {
      earnedPoints,
      bonusPoints: bonus,
      missionResult,
      mission: updatedMission,
    };
  });
}

module.exports = { calculateBonus, submitResult, computeEngagementScore };
