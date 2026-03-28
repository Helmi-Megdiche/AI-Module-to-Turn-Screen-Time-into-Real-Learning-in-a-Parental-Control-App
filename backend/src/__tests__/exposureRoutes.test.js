/**
 * HTTP tests for `GET /api/user/:userId/exposure-summary`.
 * Mocks Prisma + analyzeService stats helpers; loads Express app via supertest.
 */
jest.mock('../config/prisma', () => ({
  analysis: {
    groupBy: jest.fn(),
  },
}));

jest.mock('../services/analyzeService', () => ({
  getRecentExposureStats: jest.fn(),
  getExposureTrend: jest.fn(),
}));

const request = require('supertest');
const app = require('../app');
const prisma = require('../config/prisma');
const analyzeService = require('../services/analyzeService');

describe('Group D — GET /api/user/:userId/exposure-summary', () => {
  const statsPayload = {
    total: 10,
    riskyCount: 3,
    dangerousCount: 1,
    exposureRate: 0.4,
    lastDangerousAt: new Date('2026-03-01T00:00:00.000Z'),
  };

  const groupByPayload = [
    { category: 'safe', _count: { category: 6 } },
    { category: 'risky', _count: { category: 3 } },
    { category: 'dangerous', _count: { category: 1 } },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    analyzeService.getRecentExposureStats.mockResolvedValue(statsPayload);
    analyzeService.getExposureTrend.mockResolvedValue('stable');
    prisma.analysis.groupBy.mockResolvedValue(groupByPayload);
  });

  test('returns 200 with correct shape', async () => {
    const res = await request(app).get('/api/user/42/exposure-summary');

    expect(res.status).toBe(200);
    expect(res.body.userId).toBe(42);
    expect(res.body.window).toBe('24h');
    expect(res.body.totalAnalyses).toBe(10);
    expect(res.body.exposureRate).toBe(0.4);
    expect(res.body.trend).toBe('stable');
    expect(res.body.categoryBreakdown).toEqual({
      safe: 6,
      risky: 3,
      dangerous: 1,
    });
    expect(typeof res.body.lastDangerousAt).toBe('string');
    expect(res.body.lastDangerousAt).not.toBeNull();
  });

  test('?window=1h uses 60-minute window', async () => {
    const res = await request(app).get('/api/user/42/exposure-summary?window=1h');

    expect(res.status).toBe(200);
    expect(analyzeService.getRecentExposureStats).toHaveBeenCalledWith(42, 60);
    expect(analyzeService.getExposureTrend).toHaveBeenCalledWith(42, 60);
  });

  test('?window=7d uses 10080-minute window', async () => {
    const res = await request(app).get('/api/user/42/exposure-summary?window=7d');

    expect(res.status).toBe(200);
    expect(analyzeService.getRecentExposureStats).toHaveBeenCalledWith(42, 10080);
  });

  test('?window=invalid returns 400', async () => {
    const res = await request(app).get('/api/user/42/exposure-summary?window=invalid');

    expect(res.status).toBe(400);
    expect(String(res.body.error)).toMatch(/Invalid window/i);
  });

  test('non-numeric user id returns 400', async () => {
    const res = await request(app).get('/api/user/abc/exposure-summary');

    expect(res.status).toBe(400);
    expect(String(res.body.error)).toMatch(/Invalid user id/i);
  });

  test('Prisma groupBy failure returns 500', async () => {
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    prisma.analysis.groupBy.mockRejectedValue(new Error('DB down'));

    const res = await request(app).get('/api/user/42/exposure-summary');

    expect(res.status).toBe(500);
    expect(res.body.error).toBe('Failed to fetch exposure summary');
    errSpy.mockRestore();
  });
});
