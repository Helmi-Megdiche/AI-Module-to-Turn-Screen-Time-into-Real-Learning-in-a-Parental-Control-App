jest.mock('../../config/prisma', () => ({
  $transaction: jest.fn(),
}));

jest.mock('../aiService', () => ({
  analyzeImage: jest.fn(),
}));

jest.mock('../badgeService', () => ({
  awardPointBadges: jest.fn(),
}));

const prisma = require('../../config/prisma');
const aiService = require('../aiService');
const { awardPointBadges } = require('../badgeService');
const {
  missionForRiskScore,
  generateInteractiveMission,
  runAnalyze,
} = require('../analyzeService');

describe('missionForRiskScore', () => {
  test('below 0.3 → continue mission, 2 points', () => {
    expect(missionForRiskScore(0)).toEqual({
      mission: 'Continue your activity responsibly',
      points: 2,
    });
    expect(missionForRiskScore(0.29)).toEqual({
      mission: 'Continue your activity responsibly',
      points: 2,
    });
  });

  test('0.3 through 0.7 inclusive → 10-minute break, 5 points', () => {
    expect(missionForRiskScore(0.3)).toEqual({
      mission: 'Take a 10-minute break',
      points: 5,
    });
    expect(missionForRiskScore(0.5)).toEqual({
      mission: 'Take a 10-minute break',
      points: 5,
    });
    expect(missionForRiskScore(0.7)).toEqual({
      mission: 'Take a 10-minute break',
      points: 5,
    });
  });

  test('above 0.7 → go outside, 10 points', () => {
    expect(missionForRiskScore(0.71)).toEqual({
      mission: 'Go outside for 20 minutes',
      points: 10,
    });
    expect(missionForRiskScore(0.98)).toEqual({
      mission: 'Go outside for 20 minutes',
      points: 10,
    });
  });
});

describe('generateInteractiveMission', () => {
  test('returns quiz mission for dangerous hate/harassment signals', () => {
    const mission = generateInteractiveMission(0.9, 'dangerous', 12, [
      'hate speech',
    ]);
    expect(mission).toEqual(
      expect.objectContaining({
        type: 'quiz',
        points: 20,
        difficulty: 3,
      })
    );
  });

  test('returns puzzle mission for mid risk', () => {
    const mission = generateInteractiveMission(0.5, 'risky', 10, []);
    expect(mission).toEqual(
      expect.objectContaining({
        type: 'puzzle',
        points: 15,
        difficulty: 2,
      })
    );
  });

  test('returns real_world mission for safe risk', () => {
    const mission = generateInteractiveMission(0.1, 'safe', 9, []);
    expect(mission).toEqual(
      expect.objectContaining({
        type: 'real_world',
        points: 2,
        difficulty: 1,
      })
    );
  });
});

describe('runAnalyze safe-point controls', () => {
  const now = new Date('2026-03-22T10:00:00.000Z');
  const today = new Date('2026-03-22T00:00:00.000Z');
  const sixMinutesAgo = new Date(now.getTime() - 6 * 60 * 1000);
  const oneMinuteAgo = new Date(now.getTime() - 1 * 60 * 1000);
  const yesterday = new Date('2026-03-21T00:00:00.000Z');

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers().setSystemTime(now);
    delete process.env.SAFE_POINTS_COOLDOWN_MINUTES;
    delete process.env.SAFE_POINTS_DAILY_CAP;
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  function wireTransaction(tx) {
    prisma.$transaction.mockImplementation(async (cb) => cb(tx));
  }

  function safeAiPayload() {
    return {
      text: 'all good',
      displayText: 'all good',
      matchedKeywords: [],
      riskScore: 0.2,
      category: 'safe',
    };
  }

  function dangerousAiPayload() {
    return {
      text: 'dangerous text',
      displayText: 'dangerous text',
      matchedKeywords: ['violence'],
      riskScore: 0.9,
      category: 'dangerous',
    };
  }

  test('first safe mission awards points and updates safe tracking fields', async () => {
    aiService.analyzeImage.mockResolvedValue(safeAiPayload());

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
        }),
        create: jest.fn(),
        update: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 2,
          lastSafeMissionAt: now,
          safePointsToday: 2,
          lastSafeResetDate: today,
        }),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 10 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 20 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'abc' });

    expect(tx.analysis.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'real_world',
        difficulty: 1,
      }),
    });
    expect(tx.user.update).toHaveBeenCalledWith({
      where: { id: 1 },
      data: expect.objectContaining({
        points: { increment: 2 },
        safePointsToday: 2,
        lastSafeMissionAt: now,
        lastSafeResetDate: expect.any(Date),
      }),
    });
    expect(awardPointBadges).toHaveBeenCalledWith(1, 0, 2, tx);
  });

  test('second safe mission within cooldown does not award points', async () => {
    aiService.analyzeImage.mockResolvedValue(safeAiPayload());

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 2,
          lastSafeMissionAt: oneMinuteAgo,
          safePointsToday: 2,
          lastSafeResetDate: today,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 11 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 21 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'abc' });

    expect(tx.analysis.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'real_world',
      }),
    });
    expect(tx.user.update).not.toHaveBeenCalled();
    expect(awardPointBadges).not.toHaveBeenCalled();
  });

  test('safe mission after cooldown awards points again', async () => {
    aiService.analyzeImage.mockResolvedValue(safeAiPayload());

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 2,
          lastSafeMissionAt: sixMinutesAgo,
          safePointsToday: 2,
          lastSafeResetDate: today,
        }),
        create: jest.fn(),
        update: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 4,
          lastSafeMissionAt: now,
          safePointsToday: 4,
          lastSafeResetDate: today,
        }),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 12 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 22 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'abc' });

    expect(tx.user.update).toHaveBeenCalledWith({
      where: { id: 1 },
      data: expect.objectContaining({
        points: { increment: 2 },
        safePointsToday: 4,
        lastSafeMissionAt: now,
      }),
    });
    expect(awardPointBadges).toHaveBeenCalledWith(1, 2, 4, tx);
  });

  test('daily cap reached blocks safe point award until next reset', async () => {
    aiService.analyzeImage.mockResolvedValue(safeAiPayload());

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 10,
          lastSafeMissionAt: sixMinutesAgo,
          safePointsToday: 10,
          lastSafeResetDate: today,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 13 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 23 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'abc' });

    expect(tx.analysis.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'real_world',
      }),
    });
    expect(tx.user.update).not.toHaveBeenCalled();
    expect(awardPointBadges).not.toHaveBeenCalled();
  });

  test('safe mission on a new day resets daily counter and can award', async () => {
    aiService.analyzeImage.mockResolvedValue(safeAiPayload());

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 10,
          lastSafeMissionAt: null,
          safePointsToday: 10,
          lastSafeResetDate: yesterday,
        }),
        create: jest.fn(),
        update: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 12,
          lastSafeMissionAt: now,
          safePointsToday: 2,
          lastSafeResetDate: today,
        }),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 14 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 24 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'abc' });

    expect(tx.user.update).toHaveBeenCalledWith({
      where: { id: 1 },
      data: expect.objectContaining({
        points: { increment: 2 },
        safePointsToday: 2,
        lastSafeResetDate: expect.any(Date),
      }),
    });
    expect(awardPointBadges).toHaveBeenCalledWith(1, 10, 12, tx);
  });

  test('dangerous mission does not award immediate points', async () => {
    aiService.analyzeImage.mockResolvedValue(dangerousAiPayload());

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 15 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 25 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'abc' });

    expect(tx.analysis.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledTimes(1);
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'mini_game',
        difficulty: 3,
      }),
    });
    expect(tx.user.update).not.toHaveBeenCalled();
    expect(awardPointBadges).not.toHaveBeenCalled();
  });
});
