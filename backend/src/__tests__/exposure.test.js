/**
 * Exposure frequency (fréquence d'exposition): stats, trend, analyze boost, mission impact.
 * Prisma mock pattern aligned with `services/__tests__/analyzeService.test.js`.
 */
jest.mock('../config/prisma', () => ({
  $transaction: jest.fn(),
  analysis: {
    findMany: jest.fn(),
    findFirst: jest.fn(),
    groupBy: jest.fn(),
  },
}));

jest.mock('../services/aiService', () => ({
  analyzeImage: jest.fn(),
}));

jest.mock('../services/badgeService', () => ({
  awardPointBadges: jest.fn(),
}));

const prisma = require('../config/prisma');
const aiService = require('../services/aiService');
const {
  getRecentExposureStats,
  getExposureTrend,
  runAnalyze,
} = require('../services/analyzeService');

const FIXED_NOW = new Date('2026-06-15T12:00:00.000Z');

/** Route `findMany` by window: current uses `lte`, previous window uses `lt` (exclusive end). */
function mockTrendWindows({
  currentRows,
  previousRows,
  currentLastDangerous = null,
  previousLastDangerous = null,
}) {
  prisma.analysis.findMany.mockImplementation((args) => {
    const ca = args.where.createdAt;
    if (Object.prototype.hasOwnProperty.call(ca, 'lte')) {
      return Promise.resolve(currentRows);
    }
    if (Object.prototype.hasOwnProperty.call(ca, 'lt')) {
      return Promise.resolve(previousRows);
    }
    return Promise.resolve([]);
  });
  prisma.analysis.findFirst.mockImplementation((args) => {
    const ca = args.where.createdAt;
    if (Object.prototype.hasOwnProperty.call(ca, 'lte')) {
      return Promise.resolve(currentLastDangerous);
    }
    if (Object.prototype.hasOwnProperty.call(ca, 'lt')) {
      return Promise.resolve(previousLastDangerous);
    }
    return Promise.resolve(null);
  });
}

function rowsFromRiskySafe(risky, safe) {
  const out = [];
  for (let i = 0; i < risky; i += 1) out.push({ category: 'risky' });
  for (let i = 0; i < safe; i += 1) out.push({ category: 'safe' });
  return out;
}

function wireTransaction(tx) {
  prisma.$transaction.mockImplementation(async (cb) => cb(tx));
}

describe('Group A — getRecentExposureStats', () => {
  beforeEach(() => {
    jest.useFakeTimers().setSystemTime(FIXED_NOW);
  });

  afterEach(() => {
    jest.useRealTimers();
    prisma.analysis.findMany.mockReset();
    prisma.analysis.findFirst.mockReset();
  });

  test('returns correct counts for mixed data', async () => {
    prisma.analysis.findMany.mockResolvedValue([
      { category: 'safe' },
      { category: 'risky' },
      { category: 'dangerous' },
      { category: 'risky' },
    ]);
    prisma.analysis.findFirst.mockResolvedValue({
      createdAt: new Date('2026-01-01'),
    });

    const stats = await getRecentExposureStats(1, 1440);

    expect(stats.total).toBe(4);
    expect(stats.riskyCount).toBe(2);
    expect(stats.dangerousCount).toBe(1);
    expect(stats.exposureRate).toBe(0.75);
    expect(stats.lastDangerousAt).toBeInstanceOf(Date);
    expect(stats.lastDangerousAt).not.toBeNull();
  });

  test('exposureRate is 0 when no analyses exist', async () => {
    prisma.analysis.findMany.mockResolvedValue([]);
    prisma.analysis.findFirst.mockResolvedValue(null);

    const stats = await getRecentExposureStats(2, 60);

    expect(stats.total).toBe(0);
    expect(stats.exposureRate).toBe(0);
    expect(stats.lastDangerousAt).toBeNull();
  });

  test('only safe content → exposureRate is 0', async () => {
    prisma.analysis.findMany.mockResolvedValue([
      { category: 'safe' },
      { category: 'safe' },
    ]);
    prisma.analysis.findFirst.mockResolvedValue(null);

    const stats = await getRecentExposureStats(3, 1440);

    expect(stats.riskyCount).toBe(0);
    expect(stats.dangerousCount).toBe(0);
    expect(stats.exposureRate).toBe(0);
  });

  test('lastDangerousAt is null when no dangerous rows', async () => {
    prisma.analysis.findMany.mockResolvedValue([{ category: 'risky' }]);
    prisma.analysis.findFirst.mockResolvedValue(null);

    const stats = await getRecentExposureStats(4, 1440);

    expect(stats.lastDangerousAt).toBeNull();
  });
});

describe('Group B — getExposureTrend', () => {
  beforeEach(() => {
    jest.useFakeTimers().setSystemTime(FIXED_NOW);
  });

  afterEach(() => {
    jest.useRealTimers();
    prisma.analysis.findMany.mockReset();
    prisma.analysis.findFirst.mockReset();
  });

  test('returns "increasing" when current > previous * 1.1', async () => {
    mockTrendWindows({
      currentRows: rowsFromRiskySafe(3, 1),
      previousRows: rowsFromRiskySafe(1, 3),
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('increasing');
  });

  test('returns "stable" when rates are within ±10%', async () => {
    mockTrendWindows({
      currentRows: rowsFromRiskySafe(2, 2),
      previousRows: rowsFromRiskySafe(2, 2),
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('stable');
  });

  test('returns "decreasing" when current < previous * 0.9', async () => {
    mockTrendWindows({
      currentRows: rowsFromRiskySafe(1, 3),
      previousRows: rowsFromRiskySafe(3, 1),
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('decreasing');
  });

  test('returns "increasing" when previous window is empty and current > 0', async () => {
    mockTrendWindows({
      currentRows: rowsFromRiskySafe(1, 1),
      previousRows: [],
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('increasing');
  });

  test('returns "stable" when both windows are empty', async () => {
    mockTrendWindows({
      currentRows: [],
      previousRows: [],
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('stable');
  });
});

describe('Group C — Exposure boost in runAnalyze', () => {
  const now = new Date('2026-03-22T10:00:00.000Z');

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers().setSystemTime(now);
    delete process.env.SAFE_POINTS_COOLDOWN_MINUTES;
    delete process.env.SAFE_POINTS_DAILY_CAP;
    prisma.analysis.findMany.mockResolvedValue([]);
    prisma.analysis.findFirst.mockResolvedValue(null);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('exposureBoost is true when exposureRate > 0.5 and riskScore < DANGEROUS_THRESHOLD', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(3, 1));
    aiService.analyzeImage.mockResolvedValue({
      text: 'x',
      displayText: 'x',
      matchedKeywords: [],
      riskScore: 0.5,
      category: 'risky',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: [],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 10 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 20 }) },
    };
    wireTransaction(tx);

    const result = await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(result.exposureBoost).toBe(true);
  });

  test('exposureBoost is false when exposureRate <= 0.5', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(1, 3));
    aiService.analyzeImage.mockResolvedValue({
      text: 'x',
      displayText: 'x',
      matchedKeywords: [],
      riskScore: 0.5,
      category: 'risky',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: [],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 11 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 21 }) },
    };
    wireTransaction(tx);

    const result = await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(result.exposureBoost).toBe(false);
  });

  test('original riskScore is persisted in DB regardless of boost', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(3, 1));
    aiService.analyzeImage.mockResolvedValue({
      text: 'x',
      displayText: 'x',
      matchedKeywords: [],
      riskScore: 0.5,
      category: 'risky',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: [],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 12 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 22 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(tx.analysis.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        riskScore: 0.5,
      }),
    });
  });
});

describe('Group E — Trend boundary precision', () => {
  beforeEach(() => {
    jest.useFakeTimers().setSystemTime(FIXED_NOW);
    delete process.env.MODERATION_DANGEROUS_THRESHOLD;
  });

  afterEach(() => {
    jest.useRealTimers();
    prisma.analysis.findMany.mockReset();
    prisma.analysis.findFirst.mockReset();
  });

  test('current === previous * 1.1 exactly → "stable" (not "increasing")', async () => {
    mockTrendWindows({
      currentRows: rowsFromRiskySafe(11, 9),
      previousRows: rowsFromRiskySafe(5, 5),
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('stable');
  });

  test('current === previous * 0.9 exactly → "stable" (not "decreasing")', async () => {
    mockTrendWindows({
      currentRows: rowsFromRiskySafe(9, 11),
      previousRows: rowsFromRiskySafe(5, 5),
    });

    const trend = await getExposureTrend(1, 1440);
    expect(trend).toBe('stable');
  });

  test('riskScore >= DANGEROUS_THRESHOLD → boost NOT applied even if exposureRate > 0.5', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(3, 1));
    aiService.analyzeImage.mockResolvedValue({
      text: 'bad',
      displayText: 'bad',
      matchedKeywords: ['violence'],
      riskScore: 0.86,
      category: 'dangerous',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: [],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 15 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 25 }) },
    };
    wireTransaction(tx);

    const result = await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(result.exposureBoost).toBe(false);
    expect(tx.analysis.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        riskScore: 0.86,
      }),
    });
  });
});

describe('Group F — Mission impact of boost', () => {
  const now = new Date('2026-03-22T10:00:00.000Z');

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers().setSystemTime(now);
    delete process.env.SAFE_POINTS_COOLDOWN_MINUTES;
    delete process.env.SAFE_POINTS_DAILY_CAP;
    prisma.analysis.findMany.mockResolvedValue([]);
    prisma.analysis.findFirst.mockResolvedValue(null);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('boost raises adjusted score and drives a higher-tier mission', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(3, 1));
    aiService.analyzeImage.mockResolvedValue({
      text: 's',
      displayText: 's',
      matchedKeywords: [],
      riskScore: 0.25,
      category: 'safe',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: ['games'],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 30 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 40 }) },
    };
    wireTransaction(tx);

    const result = await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(result.exposureBoost).toBe(true);
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'mini_game',
        points: expect.any(Number),
      }),
    });
    expect(tx.mission.create.mock.calls[0][0].data.points).toBeGreaterThan(2);
  });

  test('boost does not affect mission when exposureRate is low', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(0, 4));
    aiService.analyzeImage.mockResolvedValue({
      text: 's',
      displayText: 's',
      matchedKeywords: [],
      riskScore: 0.25,
      category: 'safe',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: ['games'],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 2,
          lastSafeMissionAt: now,
          safePointsToday: 2,
          lastSafeResetDate: new Date(now.getFullYear(), now.getMonth(), now.getDate()),
        }),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 31 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 41 }) },
    };
    wireTransaction(tx);

    const result = await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(result.exposureBoost).toBe(false);
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'real_world',
        points: 2,
      }),
    });
  });

  test('DB persists original score even when boost changes mission tier', async () => {
    prisma.analysis.findMany.mockResolvedValue(rowsFromRiskySafe(3, 1));
    aiService.analyzeImage.mockResolvedValue({
      text: 's',
      displayText: 's',
      matchedKeywords: [],
      riskScore: 0.25,
      category: 'safe',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 12,
          points: 0,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
          interests: ['games'],
          engagementScore: 0.5,
        }),
        create: jest.fn(),
        update: jest.fn(),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 32 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 42 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 12, image: 'abc' });

    expect(tx.analysis.create).toHaveBeenCalledWith({
      data: expect.objectContaining({ riskScore: 0.25 }),
    });
    expect(tx.mission.create).toHaveBeenCalledWith({
      data: expect.objectContaining({
        type: 'mini_game',
      }),
    });
  });
});
