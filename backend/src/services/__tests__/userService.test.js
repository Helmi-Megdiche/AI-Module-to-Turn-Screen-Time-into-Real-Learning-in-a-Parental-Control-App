jest.mock('../../config/prisma', () => ({
  user: { findUnique: jest.fn() },
  mission: { count: jest.fn() },
  analysis: { count: jest.fn(), aggregate: jest.fn() },
  userBadge: { findMany: jest.fn() },
}));

jest.mock('../badgeService', () => ({
  awardAgeBadges: jest.fn(),
}));

const prisma = require('../../config/prisma');
const { awardAgeBadges } = require('../badgeService');
const { getSummary, getBadges } = require('../userService');

describe('userService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('getSummary returns level fields and awards age badge check', async () => {
    prisma.user.findUnique.mockResolvedValue({ id: 1, age: 11, points: 450 });
    prisma.mission.count.mockResolvedValue(12);
    prisma.analysis.count.mockResolvedValue(2);
    prisma.analysis.aggregate.mockResolvedValue({ _avg: { riskScore: 0.37567 } });

    const summary = await getSummary(1);

    expect(awardAgeBadges).toHaveBeenCalledWith(1, 11);
    expect(summary).toEqual({
      points: 450,
      totalMissions: 12,
      dangerousCount: 2,
      averageRiskScore: 0.3757,
      level: 3,
      levelTitle: 'Level 3',
      pointsToNextLevel: 450,
    });
  });

  test('getBadges maps joined user badges payload', async () => {
    prisma.user.findUnique.mockResolvedValue({ id: 7, age: 10, points: 100 });
    prisma.userBadge.findMany.mockResolvedValue([
      {
        awardedAt: new Date('2026-01-01T10:00:00.000Z'),
        badge: {
          id: 2,
          name: 'Explorer',
          description: 'Reach 500 total points.',
          type: 'POINT',
          requirementValue: '500',
        },
      },
    ]);

    const result = await getBadges(7);

    expect(result).toEqual({
      badges: [
        {
          id: 2,
          name: 'Explorer',
          description: 'Reach 500 total points.',
          type: 'POINT',
          requirementValue: '500',
          awardedAt: new Date('2026-01-01T10:00:00.000Z'),
        },
      ],
    });
  });
});
