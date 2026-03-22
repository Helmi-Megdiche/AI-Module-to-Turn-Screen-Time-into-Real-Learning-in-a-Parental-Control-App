jest.mock('../../config/prisma', () => ({
  badge: { findMany: jest.fn() },
  userBadge: { createMany: jest.fn() },
}));

const prisma = require('../../config/prisma');
const {
  awardPointBadges,
  awardMissionBadges,
  awardAgeBadges,
} = require('../badgeService');

describe('badgeService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    prisma.userBadge.createMany.mockResolvedValue({ count: 0 });
  });

  test('awardPointBadges awards thresholds crossed once', async () => {
    prisma.badge.findMany.mockResolvedValue([
      { id: 1, name: 'Rising Star', type: 'POINT', requirementValue: '100' },
      { id: 2, name: 'Explorer', type: 'POINT', requirementValue: '500' },
    ]);

    const awarded = await awardPointBadges(9, 90, 520);

    expect(awarded).toEqual(['Rising Star', 'Explorer']);
    expect(prisma.userBadge.createMany).toHaveBeenCalledWith({
      data: [{ userId: 9, badgeId: 1 }, { userId: 9, badgeId: 2 }],
      skipDuplicates: true,
    });
  });

  test('awardMissionBadges does nothing when count does not increase', async () => {
    const awarded = await awardMissionBadges(9, 10, 10);
    expect(awarded).toEqual([]);
    expect(prisma.badge.findMany).not.toHaveBeenCalled();
  });

  test('awardAgeBadges awards matching range badge', async () => {
    prisma.badge.findMany.mockResolvedValue([
      { id: 11, name: 'Little Explorer', type: 'AGE', requirementValue: '6-9' },
      { id: 12, name: 'Young Adventurer', type: 'AGE', requirementValue: '10-12' },
      { id: 14, name: 'Master', type: 'AGE', requirementValue: '18+' },
    ]);

    const awarded = await awardAgeBadges(5, 11);

    expect(awarded).toEqual(['Young Adventurer']);
    expect(prisma.userBadge.createMany).toHaveBeenCalledWith({
      data: [{ userId: 5, badgeId: 12 }],
      skipDuplicates: true,
    });
  });
});
