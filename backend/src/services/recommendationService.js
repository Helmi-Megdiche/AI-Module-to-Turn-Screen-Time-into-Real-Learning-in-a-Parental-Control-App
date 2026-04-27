const prisma = require('../config/prisma');

async function listRecommendations(userId, status = 'active') {
  return prisma.recommendation.findMany({
    where: { userId, status },
    orderBy: { createdAt: 'desc' },
  });
}

async function markRecommendationStatus(userId, recommendationId, status) {
  return prisma.recommendation.updateMany({
    where: { id: recommendationId, userId },
    data: { status },
  });
}

module.exports = {
  listRecommendations,
  markRecommendationStatus,
};
