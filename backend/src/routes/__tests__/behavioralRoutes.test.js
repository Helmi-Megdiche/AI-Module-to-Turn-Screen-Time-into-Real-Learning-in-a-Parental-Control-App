jest.mock('../../middleware/ownershipGuard', () => ({
  ownershipGuard:
    () =>
    (req, res, next) => {
      const parsed = Number(req.params.id);
      if (!Number.isInteger(parsed) || parsed <= 0) {
        return res.status(400).json({
          success: false,
          message: 'Invalid user id (positive integer required)',
        });
      }
      if (parsed === 404) {
        return res.status(404).json({ success: false, message: 'User not found' });
      }
      req.validatedUserId = parsed;
      return next();
    },
}));

jest.mock('../../services/behavioralService', () => ({
  analyzeUserBehavior: jest.fn(),
  getCurrentRecommendations: jest.fn(),
  getCurrentBehavioralMissions: jest.fn(),
}));

const express = require('express');
const request = require('supertest');
const behavioralService = require('../../services/behavioralService');
const {
  AiBehavioralValidationError,
  AiBehavioralFailureError,
  AiBehavioralUnreachableError,
} = require('../../services/aiBehavioralClient');
const behavioralRoutes = require('../behavioralRoutes');

function buildApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/user', behavioralRoutes);
  return app;
}

describe('behavioralRoutes', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('POST /api/user/:id/behavioral/analyze happy path returns 200', async () => {
    behavioralService.analyzeUserBehavior.mockResolvedValue({
      score: { id: 1 },
      recommendations: [{ id: 2 }],
    });
    const res = await request(buildApp()).post('/api/user/42/behavioral/analyze').send({
      ageYears: 10,
      windowDays: 14,
      contentSummary: { educationalCount: 20, riskyCount: 5, dangerousCount: 0, total: 30 },
      missionSummary: { completed: 7, assigned: 10 },
    });
    expect(res.status).toBe(200);
    expect(res.body.score.id).toBe(1);
    expect(res.body.recommendations).toHaveLength(1);
  });

  test('POST missing ageYears returns 400', async () => {
    const res = await request(buildApp()).post('/api/user/42/behavioral/analyze').send({});
    expect(res.status).toBe(400);
  });

  test('POST ageYears out of range returns 400', async () => {
    const resLow = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 1 });
    const resHigh = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 26 });
    expect(resLow.status).toBe(400);
    expect(resHigh.status).toBe(400);
  });

  test('POST windowDays out of range returns 400', async () => {
    const resLow = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 10, windowDays: 6 });
    const resHigh = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 10, windowDays: 31 });
    expect(resLow.status).toBe(400);
    expect(resHigh.status).toBe(400);
  });

  test('POST ownershipGuard rejects wrong userId', async () => {
    const res = await request(buildApp())
      .post('/api/user/abc/behavioral/analyze')
      .send({ ageYears: 10 });
    expect(res.status).toBe(400);
  });

  test('POST maps AiBehavioralValidationError to 400', async () => {
    behavioralService.analyzeUserBehavior.mockRejectedValue(
      new AiBehavioralValidationError('bad', 'bad payload', 400)
    );
    const res = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 10 });
    expect(res.status).toBe(400);
    expect(res.body.error).toBe('ai_validation');
  });

  test('POST maps AiBehavioralFailureError to 502', async () => {
    behavioralService.analyzeUserBehavior.mockRejectedValue(
      new AiBehavioralFailureError('ai fail', 'internal', 500)
    );
    const res = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 10 });
    expect(res.status).toBe(502);
    expect(res.body.error).toBe('ai_failure');
  });

  test('POST maps AiBehavioralUnreachableError to 503', async () => {
    behavioralService.analyzeUserBehavior.mockRejectedValue(
      new AiBehavioralUnreachableError('down', 'timeout')
    );
    const res = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 10 });
    expect(res.status).toBe(503);
    expect(res.body.error).toBe('ai_unreachable');
  });

  test('POST maps generic service error to 500', async () => {
    behavioralService.analyzeUserBehavior.mockRejectedValue(new Error('boom'));
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const res = await request(buildApp())
      .post('/api/user/42/behavioral/analyze')
      .send({ ageYears: 10 });
    expect(res.status).toBe(500);
    expect(res.body.error).toBe('internal_error');
    errSpy.mockRestore();
  });

  test('GET /api/user/:id/recommendations/current happy path returns 200 array', async () => {
    behavioralService.getCurrentRecommendations.mockResolvedValue([{ id: 1 }]);
    const res = await request(buildApp()).get('/api/user/42/recommendations/current');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([{ id: 1 }]);
  });

  test('GET /api/user/:id/recommendations/current no snapshot returns empty array', async () => {
    behavioralService.getCurrentRecommendations.mockResolvedValue([]);
    const res = await request(buildApp()).get('/api/user/42/recommendations/current');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  test('GET /api/user/:id/recommendations/current ownershipGuard rejects wrong user', async () => {
    const res = await request(buildApp()).get('/api/user/abc/recommendations/current');
    expect(res.status).toBe(400);
  });

  test('GET /api/user/:id/missions/current happy path returns 200 array', async () => {
    behavioralService.getCurrentBehavioralMissions.mockResolvedValue([{ id: 99 }]);
    const res = await request(buildApp()).get('/api/user/42/missions/current');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([{ id: 99 }]);
  });

  test('GET /api/user/:id/missions/current no snapshot returns empty array', async () => {
    behavioralService.getCurrentBehavioralMissions.mockResolvedValue([]);
    const res = await request(buildApp()).get('/api/user/42/missions/current');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  test('GET /api/user/:id/missions/current ownershipGuard rejects wrong user', async () => {
    const res = await request(buildApp()).get('/api/user/abc/missions/current');
    expect(res.status).toBe(400);
  });
});
