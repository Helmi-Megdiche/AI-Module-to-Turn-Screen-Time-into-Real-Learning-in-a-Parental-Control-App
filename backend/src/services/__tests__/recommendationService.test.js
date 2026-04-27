jest.mock('../../config/prisma', () => ({
  recommendation: {
    findMany: jest.fn(),
    updateMany: jest.fn(),
  },
}));

const prisma = require('../../config/prisma');
const {
  listRecommendations,
  markRecommendationStatus,
} = require('../recommendationService');

describe('recommendationService.listRecommendations', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('lists active recommendations for user', async () => {
    prisma.recommendation.findMany.mockResolvedValue([{ id: 1, status: 'active' }]);

    const out = await listRecommendations(3, 'active');

    expect(prisma.recommendation.findMany).toHaveBeenCalledWith({
      where: { userId: 3, status: 'active' },
      orderBy: { createdAt: 'desc' },
    });
    expect(out).toHaveLength(1);
  });
});

describe('recommendationService.markRecommendationStatus', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('marks recommendation dismissed', async () => {
    prisma.recommendation.updateMany.mockResolvedValue({ count: 1 });
    const out = await markRecommendationStatus(4, 10, 'dismissed');
    expect(prisma.recommendation.updateMany).toHaveBeenCalledWith({
      where: { id: 10, userId: 4 },
      data: { status: 'dismissed' },
    });
    expect(out.count).toBe(1);
  });

  test('marks recommendation acted', async () => {
    prisma.recommendation.updateMany.mockResolvedValue({ count: 1 });
    const out = await markRecommendationStatus(4, 10, 'acted');
    expect(prisma.recommendation.updateMany).toHaveBeenCalledWith({
      where: { id: 10, userId: 4 },
      data: { status: 'acted' },
    });
    expect(out.count).toBe(1);
  });
});
