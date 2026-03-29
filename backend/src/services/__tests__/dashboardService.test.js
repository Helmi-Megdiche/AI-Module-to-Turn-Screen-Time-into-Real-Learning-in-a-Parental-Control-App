jest.mock('../../config/prisma', () => ({
  mission: { count: jest.fn() },
  missionResult: { findMany: jest.fn() },
  analysis: { count: jest.fn(), aggregate: jest.fn() },
  user: { findUnique: jest.fn() },
  userBadge: { count: jest.fn() },
}));

const prisma = require('../../config/prisma');
const {
  getMissionStats,
  getEducationalStats,
  getProgressSnapshot,
  bucketByDay,
  bucketByHour,
} = require('../dashboardService');

describe('dashboardService.getMissionStats', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('completionRate = completedInWindow / assignedInWindow', async () => {
    prisma.mission.count.mockResolvedValue(10);
    prisma.missionResult.findMany.mockResolvedValue(
      Array.from({ length: 6 }, () => ({ mission: { type: 'quiz' } }))
    );

    const out = await getMissionStats(1, new Date('2026-01-01T00:00:00Z'));

    expect(out.assignedInWindow).toBe(10);
    expect(out.completedInWindow).toBe(6);
    expect(out.completionRate).toBe(0.6);
  });

  test('completionRate = 0 when no missions assigned', async () => {
    prisma.mission.count.mockResolvedValue(0);
    prisma.missionResult.findMany.mockResolvedValue([]);

    const out = await getMissionStats(1, new Date('2026-01-01T00:00:00Z'));

    expect(out.assignedInWindow).toBe(0);
    expect(out.completedInWindow).toBe(0);
    expect(out.completionRate).toBe(0);
  });

  test('byType aggregates correctly and zero-fills missing types', async () => {
    prisma.mission.count.mockResolvedValue(3);
    prisma.missionResult.findMany.mockResolvedValue([
      { mission: { type: 'quiz' } },
      { mission: { type: 'quiz' } },
      { mission: { type: 'real_world' } },
    ]);

    const out = await getMissionStats(1, new Date('2026-01-01T00:00:00Z'));

    expect(out.byType.quiz).toBe(2);
    expect(out.byType.real_world).toBe(1);
    expect(out.byType.mini_game).toBe(0);
    expect(out.byType.puzzle).toBe(0);
  });
});

describe('dashboardService.getEducationalStats', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('counts and shareOfTotal correct', async () => {
    prisma.analysis.count.mockResolvedValueOnce(10).mockResolvedValueOnce(3);
    prisma.analysis.aggregate.mockResolvedValue({
      _avg: { educationalScore: 0.45 },
    });

    const out = await getEducationalStats(1, new Date('2026-01-01T00:00:00Z'));

    expect(out.educationalCount).toBe(3);
    expect(out.shareOfTotal).toBe(0.3);
    expect(out.avgEducationalScore).toBe(0.45);
  });

  test('all zeros when no analyses in window (null avg → 0.0)', async () => {
    prisma.analysis.count.mockResolvedValueOnce(0).mockResolvedValueOnce(0);
    prisma.analysis.aggregate.mockResolvedValue({
      _avg: { educationalScore: null },
    });

    const out = await getEducationalStats(1, new Date('2026-01-01T00:00:00Z'));

    expect(out.educationalCount).toBe(0);
    expect(out.shareOfTotal).toBe(0);
    expect(out.avgEducationalScore).toBe(0.0);
    expect(out.avgEducationalScore).not.toBeNull();
  });
});

describe('dashboardService.getProgressSnapshot', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('returns correct shape for existing user', async () => {
    prisma.user.findUnique.mockResolvedValue({
      points: 400,
      completedMissions: 20,
      engagementScore: 0.8,
    });
    prisma.userBadge.count.mockResolvedValue(5);

    const out = await getProgressSnapshot(1);

    expect(out.points).toBe(400);
    expect(out.completedMissions).toBe(20);
    expect(out.badgeCount).toBe(5);
    expect(out.engagementScore).toBe(0.8);
    expect(out.level).toBe(Math.floor(Math.sqrt(400 / 100)) + 1);
    expect(out.level).toBe(3);
  });

  test('returns null when user does not exist', async () => {
    prisma.user.findUnique.mockResolvedValue(null);

    const out = await getProgressSnapshot(999);

    expect(out).toBeNull();
    expect(prisma.userBadge.count).not.toHaveBeenCalled();
  });
});

describe('dashboardService.bucketByDay', () => {
  test('zero-fills missing days in range', () => {
    const rows = [
      {
        createdAt: new Date('2026-03-25T10:00:00Z'),
        riskScore: 0.5,
        category: 'risky',
        educationalScore: 0,
      },
    ];
    const fromDate = new Date('2026-03-24T00:00:00Z');
    const toDate = new Date('2026-03-26T00:00:00Z');

    const series = bucketByDay(rows, fromDate, toDate);

    expect(series.length).toBe(3);
    expect(series[0].t).toBe('2026-03-24');
    expect(series[0].count).toBe(0);
    expect(series[1].t).toBe('2026-03-25');
    expect(series[1].count).toBe(1);
    expect(series[2].t).toBe('2026-03-26');
    expect(series[2].count).toBe(0);
  });

  test('avgRiskScore and maxRiskScore computed correctly', () => {
    const day = new Date('2026-06-01T12:00:00Z');
    const rows = [
      {
        createdAt: new Date('2026-06-01T08:00:00Z'),
        riskScore: 0.3,
        category: 'safe',
        educationalScore: 0,
      },
      {
        createdAt: new Date('2026-06-01T20:00:00Z'),
        riskScore: 0.7,
        category: 'safe',
        educationalScore: 0,
      },
    ];

    const series = bucketByDay(rows, day, day);
    const bucket = series[0];

    expect(bucket.avgRiskScore).toBe(0.5);
    expect(bucket.maxRiskScore).toBe(0.7);
  });

  test('dangerousCount and educationalCount per bucket', () => {
    const day = new Date('2026-06-10T00:00:00Z');
    const rows = [
      {
        createdAt: new Date('2026-06-10T01:00:00Z'),
        riskScore: 0.9,
        category: 'dangerous',
        educationalScore: 0.0,
      },
      {
        createdAt: new Date('2026-06-10T02:00:00Z'),
        riskScore: 0.1,
        category: 'educational',
        educationalScore: 0.7,
      },
    ];

    const bucket = bucketByDay(rows, day, day)[0];

    expect(bucket.dangerousCount).toBe(1);
    expect(bucket.educationalCount).toBe(1);
  });
});

describe('dashboardService.bucketByHour', () => {
  test('hourly bucket key format', () => {
    const rows = [
      {
        createdAt: new Date('2026-03-29T14:32:00.000Z'),
        riskScore: 0.2,
        category: 'safe',
        educationalScore: 0,
      },
    ];
    const fromDate = new Date('2026-03-29T14:00:00.000Z');
    const toDate = new Date('2026-03-29T14:00:00.000Z');

    const series = bucketByHour(rows, fromDate, toDate);

    expect(series.length).toBe(1);
    expect(series[0].t).toBe('2026-03-29T14:00:00Z');
  });

  test('zero-fills missing hours', () => {
    const fromDate = new Date('2026-03-29T10:00:00.000Z');
    const toDate = new Date('2026-03-29T12:00:00.000Z');
    const rows = [
      {
        createdAt: new Date('2026-03-29T11:30:00.000Z'),
        riskScore: 0.4,
        category: 'safe',
        educationalScore: 0,
      },
    ];

    const series = bucketByHour(rows, fromDate, toDate);

    expect(series.length).toBe(3);
    expect(series[0].count).toBe(0);
    expect(series[1].count).toBe(1);
    expect(series[2].count).toBe(0);
  });
});
