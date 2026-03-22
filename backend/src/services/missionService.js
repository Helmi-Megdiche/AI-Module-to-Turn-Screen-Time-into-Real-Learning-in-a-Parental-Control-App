const prisma = require('../config/prisma');

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

    await tx.user.update({
      where: { id: mission.userId },
      data: {
        points: { increment: mission.points },
      },
    });

    if (bonusPointsInt > 0) {
      await tx.user.update({
        where: { id: mission.userId },
        data: {
          points: { increment: bonusPointsInt },
        },
      });
    }

    return updatedMission;
  });
}

module.exports = {
  completeMission,
};
