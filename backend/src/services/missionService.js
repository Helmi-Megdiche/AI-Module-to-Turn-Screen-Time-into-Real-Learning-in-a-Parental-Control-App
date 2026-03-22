const prisma = require('../config/prisma');
const {
  awardMissionBadges,
  awardPointBadges,
} = require('./badgeService');

async function completeMission(missionId, bonusPoints = 0) {
  const missionIdInt = Number(missionId);
  const bonusPointsInt = Number(bonusPoints);

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

    if (mission.status === 'completed') {
      const err = new Error('Mission already completed');
      err.code = 'MISSION_ALREADY_COMPLETED';
      throw err;
    }

    const updatedMission = await tx.mission.update({
      where: { id: missionIdInt },
      data: { status: 'completed' },
    });

    const bonus = bonusPointsInt > 0 ? bonusPointsInt : 0;
    const userUpdated = await tx.user.update({
      where: { id: mission.userId },
      data: {
        points: { increment: mission.points + bonus },
        completedMissions: { increment: 1 },
      },
    });

    const previousPoints = Number(mission.user?.points ?? 0);
    const newPoints = Number(userUpdated.points ?? previousPoints);
    const previousCompleted = Number(mission.user?.completedMissions ?? 0);
    const newCompleted = Number(userUpdated.completedMissions ?? previousCompleted);
    await awardPointBadges(mission.userId, previousPoints, newPoints, tx);
    await awardMissionBadges(mission.userId, previousCompleted, newCompleted, tx);

    return updatedMission;
  });
}

module.exports = {
  completeMission,
};
