/**
 * HTTP tests for dashboard aggregate and risk-series routes.
 */
jest.mock('../config/prisma', () => ({
  analysis: {
    groupBy: jest.fn(),
    findMany: jest.fn(),
  },
}));

jest.mock('../services/analyzeService', () => ({
  getRecentExposureStats: jest.fn(),
  getExposureTrend: jest.fn(),
}));

jest.mock('../services/dashboardService', () => {
  const actual = jest.requireActual('../services/dashboardService');
  return {
    ...actual,
    getMissionStats: jest.fn(),
    getEducationalStats: jest.fn(),
    getProgressSnapshot: jest.fn(),
  };
});

const request = require('supertest');
const app = require('../app');
const prisma = require('../config/prisma');
const analyzeService = require('../services/analyzeService');
const dashboardService = require('../services/dashboardService');

describe('GET /api/user/:userId/dashboard', () => {
  const statsPayload = {
    total: 8,
    riskyCount: 2,
    dangerousCount: 0,
    exposureRate: 0.25,
    lastDangerousAt: null,
  };

  const groupByPayload = [
    { category: 'safe', _count: { category: 5 } },
    { category: 'risky', _count: { category: 2 } },
    { category: 'educational', _count: { category: 1 } },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    analyzeService.getRecentExposureStats.mockResolvedValue(statsPayload);
    analyzeService.getExposureTrend.mockResolvedValue('stable');
    prisma.analysis.groupBy.mockResolvedValue(groupByPayload);
    dashboardService.getMissionStats.mockResolvedValue({
      assignedInWindow: 4,
      completedInWindow: 2,
      completionRate: 0.5,
      byType: { quiz: 1, real_world: 1, mini_game: 0, puzzle: 0 },
    });
    dashboardService.getEducationalStats.mockResolvedValue({
      educationalCount: 2,
      avgEducationalScore: 0.33,
      shareOfTotal: 0.25,
    });
    dashboardService.getProgressSnapshot.mockResolvedValue({
      points: 100,
      level: 2,
      completedMissions: 5,
      badgeCount: 1,
      engagementScore: 0.6,
    });
  });

  test('returns 200 with correct shape', async () => {
    const res = await request(app).get('/api/user/42/dashboard');

    expect(res.status).toBe(200);
    expect(res.body.userId).toBe(42);
    expect(res.body).toEqual(
      expect.objectContaining({
        userId: 42,
        window: '7d',
        exposure: expect.any(Object),
        progress: expect.any(Object),
        missions: expect.any(Object),
        educational: expect.any(Object),
      })
    );
    expect(res.body.exposure.trend).toBe('stable');
    expect(typeof res.body.missions.completionRate).toBe('number');
  });

  test('?window=1h passes 60 minutes to exposure helpers and mission since', async () => {
    const t0 = new Date('2026-03-29T12:00:00.000Z');
    jest.useFakeTimers().setSystemTime(t0);

    const res = await request(app).get('/api/user/42/dashboard?window=1h');

    expect(res.status).toBe(200);
    expect(analyzeService.getRecentExposureStats).toHaveBeenCalledWith(42, 60);
    expect(analyzeService.getExposureTrend).toHaveBeenCalledWith(42, 60);
    const sinceArg = dashboardService.getMissionStats.mock.calls[0][1];
    expect(sinceArg).toBeInstanceOf(Date);
    expect(sinceArg.getTime()).toBe(t0.getTime() - 60 * 60 * 1000);

    jest.useRealTimers();
  });

  test('?window=invalid returns 400', async () => {
    const res = await request(app).get('/api/user/42/dashboard?window=invalid');

    expect(res.status).toBe(400);
    expect(String(res.body.error)).toMatch(/Invalid window/i);
  });

  test('non-numeric user id returns 400', async () => {
    const res = await request(app).get('/api/user/abc/dashboard');

    expect(res.status).toBe(400);
    expect(String(res.body.error)).toMatch(/Invalid user id/i);
  });

  test('getProgressSnapshot throws → 500', async () => {
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    dashboardService.getProgressSnapshot.mockRejectedValue(new Error('DB down'));

    const res = await request(app).get('/api/user/42/dashboard');

    expect(res.status).toBe(500);
    expect(res.body.error).toBe('Failed to fetch dashboard');
    errSpy.mockRestore();
  });
});

describe('GET /api/user/:userId/risk-series', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('returns 200 with series array (day bucket)', async () => {
    prisma.analysis.findMany.mockResolvedValue([
      {
        createdAt: new Date('2026-03-28T10:00:00.000Z'),
        riskScore: 0.2,
        category: 'safe',
        educationalScore: 0,
      },
      {
        createdAt: new Date('2026-03-28T15:00:00.000Z'),
        riskScore: 0.4,
        category: 'safe',
        educationalScore: 0,
      },
      {
        createdAt: new Date('2026-03-29T09:00:00.000Z'),
        riskScore: 0.6,
        category: 'risky',
        educationalScore: 0.1,
      },
    ]);

    const res = await request(app).get(
      '/api/user/42/risk-series?from=2026-03-28T00:00:00.000Z&to=2026-03-29T23:59:59.000Z'
    );

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.series)).toBe(true);
    expect(res.body.bucket).toBe('day');
    expect(res.body.series.every((b) => 'avgRiskScore' in b && 'count' in b)).toBe(
      true
    );
    expect(res.body.userId).toBe(42);
  });

  test('?bucket=hour uses hour keys', async () => {
    prisma.analysis.findMany.mockResolvedValue([
      {
        createdAt: new Date('2026-03-29T11:30:00.000Z'),
        riskScore: 0.3,
        category: 'safe',
        educationalScore: 0,
      },
    ]);

    const res = await request(app).get(
      '/api/user/42/risk-series?bucket=hour&from=2026-03-29T10:00:00.000Z&to=2026-03-29T12:00:00.000Z'
    );

    expect(res.status).toBe(200);
    expect(res.body.bucket).toBe('hour');
    expect(res.body.series.length).toBeGreaterThan(0);
    expect(res.body.series[0].t).toMatch(/T\d{2}:00:00Z$/);
  });

  test('?from=not-a-date returns 400', async () => {
    const res = await request(app).get('/api/user/42/risk-series?from=not-a-date');

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('Invalid from date.');
  });

  test('from after to returns 400', async () => {
    const res = await request(app).get(
      '/api/user/42/risk-series?from=2026-03-29&to=2026-03-22'
    );

    expect(res.status).toBe(400);
    expect(res.body.error).toBe('from must be before to.');
  });

  test('Prisma findMany throws → 500', async () => {
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    prisma.analysis.findMany.mockRejectedValue(new Error('DB down'));

    const res = await request(app).get(
      '/api/user/42/risk-series?from=2026-03-01&to=2026-03-31'
    );

    expect(res.status).toBe(500);
    expect(res.body.error).toBe('Failed to fetch risk series');
    errSpy.mockRestore();
  });
});
