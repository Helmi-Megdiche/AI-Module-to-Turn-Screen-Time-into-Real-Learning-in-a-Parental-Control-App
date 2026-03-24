jest.mock('../../config/prisma', () => ({
  $transaction: jest.fn(),
}));

jest.mock('../badgeService', () => ({
  awardPointBadges: jest.fn(),
  awardMissionBadges: jest.fn(),
}));

const prisma = require('../../config/prisma');
const { awardPointBadges, awardMissionBadges } = require('../badgeService');
const {
  calculateBonus,
  submitResult,
  computeEngagementScore,
} = require('../missionResultService');

describe('missionResultService.calculateBonus', () => {
  test('quiz success with score=1 gives bonus 5', () => {
    const bonus = calculateBonus({ type: 'quiz' }, { score: 1, success: true });
    expect(bonus).toBe(5);
  });

  test('puzzle bonus depends on timeSpent', () => {
    const bonus = calculateBonus(
      { type: 'puzzle' },
      { success: true, timeSpent: 20 }
    );
    expect(bonus).toBe(5);
  });

  test('puzzle bonus is capped by reward.maxBonus when provided', () => {
    const bonus = calculateBonus(
      { type: 'puzzle', content: { reward: { maxBonus: 4 } } },
      { success: true, timeSpent: 10 }
    );
    expect(bonus).toBe(4);
  });

  test('mini_game win gives bonus 10', () => {
    const bonus = calculateBonus(
      { type: 'mini_game' },
      { score: 2, success: true }
    );
    expect(bonus).toBe(10);
  });

  test('failed mission returns zero bonus', () => {
    const bonus = calculateBonus(
      { type: 'mini_game' },
      { score: 2, success: false }
    );
    expect(bonus).toBe(0);
  });
});

describe('missionResultService.computeEngagementScore', () => {
  test('returns 0.5 when there are no results', () => {
    expect(computeEngagementScore([])).toBe(0.5);
  });

  test('increases for successful recent streak', () => {
    const score = computeEngagementScore([
      { success: true },
      { success: true },
      { success: false },
      { success: true },
    ]);
    expect(score).toBeGreaterThan(0.5);
  });
});

describe('missionResultService.submitResult', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  function wireTransaction(tx) {
    prisma.$transaction.mockImplementation(async (cb) => cb(tx));
  }

  test('creates result, auto-completes mission, updates points and completedMissions', async () => {
    const tx = {
      mission: {
        findUnique: jest.fn().mockResolvedValue({
          id: 5,
          userId: 1,
          points: 20,
          type: 'quiz',
          status: 'pending',
          user: { id: 1, points: 50, completedMissions: 2 },
        }),
        update: jest.fn().mockResolvedValue({ id: 5, status: 'completed' }),
      },
      missionResult: {
        findFirst: jest.fn().mockResolvedValue(null),
        create: jest.fn().mockResolvedValue({ id: 100, bonusPoints: 5 }),
        findMany: jest.fn().mockResolvedValue([
          { success: true },
          { success: true },
          { success: false },
        ]),
      },
      user: {
        update: jest.fn().mockResolvedValue({
          id: 1,
          points: 75,
          completedMissions: 3,
        }),
      },
    };
    wireTransaction(tx);

    const out = await submitResult(5, 1, { score: 1, success: true, timeSpent: 8 });

    expect(tx.missionResult.create).toHaveBeenCalledWith({
      data: {
        missionId: 5,
        userId: 1,
        score: 1,
        success: true,
        timeSpent: 8,
        bonusPoints: 5,
        earnedPoints: 25,
      },
    });
    expect(tx.mission.update).toHaveBeenCalledWith({
      where: { id: 5 },
      data: { status: 'completed' },
    });
    expect(tx.user.update).toHaveBeenCalledWith({
      where: { id: 1 },
      data: {
        points: { increment: 25 },
        completedMissions: { increment: 1 },
        engagementScore: expect.any(Number),
      },
    });
    expect(awardPointBadges).toHaveBeenCalledWith(1, 50, 75, tx);
    expect(awardMissionBadges).toHaveBeenCalledWith(1, 2, 3, tx);
    expect(out.earnedPoints).toBe(25);
    expect(out.bonusPoints).toBe(5);
  });

  test('throws conflict if mission already completed', async () => {
    const tx = {
      mission: {
        findUnique: jest.fn().mockResolvedValue({
          id: 8,
          userId: 2,
          points: 10,
          type: 'quiz',
          status: 'completed',
          user: { id: 2, points: 10, completedMissions: 0 },
        }),
      },
      missionResult: { findFirst: jest.fn() },
      user: { update: jest.fn() },
    };
    wireTransaction(tx);

    await expect(submitResult(8, 2, { success: true })).rejects.toMatchObject({
      code: 'MISSION_ALREADY_COMPLETED',
    });
  });
});
