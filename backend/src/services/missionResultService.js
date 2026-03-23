const prisma = require('../config/prisma');
const { awardMissionBadges, awardPointBadges } = require('./badgeService');

function calculateBonus(mission, result) {
  const { score, success, timeSpent } = result;
  if (!success) return 0;

  let bonus = 0;
  switch (mission.type) {
    case 'quiz':
      if (score === 1) bonus = 5;
      break;
    case 'puzzle':
      if (timeSpent) {
        const timeBonus = Math.max(0, 30 - timeSpent);
        bonus = Math.floor(timeBonus / 2);
      }
      break;
    case 'mini_game':
      if (score >= 2) bonus = 10;
      else if (score === 1) bonus = 5;
      break;
    default:
      bonus = 0;
  }
  return bonus;
}

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

    const bonus = calculateBonus(mission, { score, success, timeSpent });
    const earnedPoints = mission.points + bonus;

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

    const userUpdated = await tx.user.update({
      where: { id: userIdInt },
      data: {
        points: { increment: earnedPoints },
        completedMissions: { increment: 1 },
      },
    });

    const previousPoints = Number(mission.user?.points ?? 0);
    const newPoints = Number(userUpdated.points ?? previousPoints);
    const previousCompleted = Number(mission.user?.completedMissions ?? 0);
    const newCompleted = Number(userUpdated.completedMissions ?? previousCompleted);
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

module.exports = { calculateBonus, submitResult };
