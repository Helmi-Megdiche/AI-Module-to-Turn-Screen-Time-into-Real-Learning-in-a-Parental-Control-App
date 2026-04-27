jest.mock('../../config/prisma', () => ({
  usageEvent: { findMany: jest.fn() },
  behavioralScore: { create: jest.fn(), findFirst: jest.fn() },
  recommendation: { create: jest.fn(), findMany: jest.fn() },
  mission: { create: jest.fn(), findMany: jest.fn() },
}));

jest.mock('../aiBehavioralClient', () => ({
  callBehavioralAnalyze: jest.fn(),
  AiBehavioralValidationError: class AiBehavioralValidationError extends Error {},
  AiBehavioralFailureError: class AiBehavioralFailureError extends Error {},
  AiBehavioralUnreachableError: class AiBehavioralUnreachableError extends Error {},
}));

const prisma = require('../../config/prisma');
const aiBehavioralClient = require('../aiBehavioralClient');
const {
  analyzeUserBehavior,
  getCurrentRecommendations,
  getCurrentBehavioralMissions,
  rankRecommendations,
} = require('../behavioralService');

function buildAiResponse(recommendations = [], missions = []) {
  return {
    addictionScore: 0.7,
    wellbeingScore: 0.4,
    addictionSubscores: [{ name: 'intensity', value: 0.8 }],
    wellbeingSubscores: [{ name: 'sleep', value: 0.3 }],
    windowDays: 14,
    computedAt: '2026-04-24T18:00:00.000Z',
    recommendations,
    missions,
  };
}

describe('behavioralService.analyzeUserBehavior', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    prisma.usageEvent.findMany.mockResolvedValue([
      {
        eventType: 'app_session',
        startedAt: new Date('2026-04-20T10:00:00.000Z'),
        durationSec: 120,
        appPackage: 'com.chat.app',
      },
      {
        eventType: 'unlock',
        startedAt: new Date('2026-04-20T11:00:00.000Z'),
        durationSec: null,
        appPackage: null,
      },
      {
        eventType: 'screen_on',
        startedAt: new Date('2026-04-20T12:00:00.000Z'),
        durationSec: 30,
        appPackage: 'com.game.app',
      },
    ]);
    prisma.behavioralScore.create.mockResolvedValue({ id: 99, userId: 42 });
    prisma.recommendation.create.mockImplementation(async ({ data }) => ({
      id: Math.floor(Math.random() * 1000),
      ...data,
    }));
    prisma.mission.create.mockImplementation(async ({ data }) => ({
      id: Math.floor(Math.random() * 1000),
      ...data,
    }));
  });

  test('happy path fetches events, calls AI, creates score + 3 recs + 2 missions, returns all', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([
        { type: 'screen_curfew', severity: 'high', messageFr: 'a', triggeringValue: 0.9 },
        { type: 'weekly_escalation_alert', severity: 'high', messageFr: 'b', triggeringValue: 0.8 },
        { type: 'daily_limit_reminder', severity: 'medium', messageFr: 'c', triggeringValue: 0.6 },
        { type: 'session_break', severity: 'low', messageFr: 'd', triggeringValue: 0.7 },
      ], [
        {
          descriptionFr: "Pose ton téléphone à 21h ce soir et lis 15 minutes avant de dormir.",
          difficulty: 'hard',
          points: 30,
          triggeringSubscore: 'nocturnal',
          triggeringValue: 0.95,
          targetAudience: 'child',
        },
        {
          descriptionFr: "Va jouer dehors ou bouger pendant 30 minutes aujourd'hui.",
          difficulty: 'medium',
          points: 20,
          triggeringSubscore: 'real_activity',
          triggeringValue: 0.2,
          targetAudience: 'child',
        },
      ])
    );

    const out = await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });

    expect(prisma.usageEvent.findMany).toHaveBeenCalledTimes(1);
    expect(aiBehavioralClient.callBehavioralAnalyze).toHaveBeenCalledTimes(1);
    expect(prisma.behavioralScore.create).toHaveBeenCalledTimes(1);
    expect(prisma.recommendation.create).toHaveBeenCalledTimes(3);
    expect(prisma.mission.create).toHaveBeenCalledTimes(2);
    expect(out).toHaveProperty('score');
    expect(out.recommendations).toHaveLength(3);
    expect(out.missions).toHaveLength(2);
  });

  test('maps appPackage to packageName in AI payload', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(buildAiResponse([]));
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    const payload = aiBehavioralClient.callBehavioralAnalyze.mock.calls[0][0];
    expect(payload.events[0].packageName).toBe('com.chat.app');
    expect(payload.events[1].packageName).toBeNull();
    expect(payload.events[0].startedAt.endsWith('Z')).toBe(false);
  });

  test('filters events by windowDays in where clause', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(buildAiResponse([]));
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 7 });
    const args = prisma.usageEvent.findMany.mock.calls[0][0];
    expect(args.where.userId).toBe(42);
    expect(args.where.startedAt.gte).toBeInstanceOf(Date);
    expect(args.where.startedAt.lte).toBeInstanceOf(Date);
  });

  test('response with 5 recs persists only top 3', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([
        { type: 'a', severity: 'high', messageFr: '1', triggeringValue: 0.8 },
        { type: 'b', severity: 'medium', messageFr: '2', triggeringValue: 0.9 },
        { type: 'c', severity: 'low', messageFr: '3', triggeringValue: 0.9 },
        { type: 'd', severity: 'positive', messageFr: '4', triggeringValue: 0.9 },
        { type: 'e', severity: 'high', messageFr: '5', triggeringValue: 0.7 },
      ])
    );
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.recommendation.create).toHaveBeenCalledTimes(3);
  });

  test('response with 2 recs persists both', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([
        { type: 'a', severity: 'high', messageFr: '1', triggeringValue: 0.8 },
        { type: 'b', severity: 'medium', messageFr: '2', triggeringValue: 0.9 },
      ])
    );
    const out = await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.recommendation.create).toHaveBeenCalledTimes(2);
    expect(out.recommendations).toHaveLength(2);
  });

  test('AI response with zero missions does not persist mission rows', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(buildAiResponse([], []));
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.mission.create).not.toHaveBeenCalled();
  });

  test('AI response with one mission persists one mission row', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([], [
        {
          descriptionFr: "Fais une pause sans écran d'une heure cet après-midi.",
          difficulty: 'easy',
          points: 10,
          triggeringSubscore: 'intensity',
          triggeringValue: 0.55,
          targetAudience: 'child',
        },
      ])
    );
    const out = await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.mission.create).toHaveBeenCalledTimes(1);
    expect(out.missions).toHaveLength(1);
  });

  test('BehavioralScore.recommendationsJson stores all recommendations', async () => {
    const allRecs = [
      { type: 'a', severity: 'high', messageFr: '1' },
      { type: 'b', severity: 'medium', messageFr: '2' },
      { type: 'c', severity: 'low', messageFr: '3' },
      { type: 'd', severity: 'positive', messageFr: '4' },
      { type: 'e', severity: 'high', messageFr: '5' },
    ];
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(buildAiResponse(allRecs));
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    const createArg = prisma.behavioralScore.create.mock.calls[0][0];
    expect(createArg.data.recommendationsJson).toEqual(allRecs);
  });

  test('persisted recommendations have scoreSnapshotId from created score', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([{ type: 'a', severity: 'high', messageFr: '1' }])
    );
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.recommendation.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          scoreSnapshotId: 99,
        }),
      })
    );
  });

  test('persisted mission has scoreSnapshotId from created score and expected shape', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([], [
        {
          descriptionFr: "Pose ton téléphone dans une autre pièce pendant 2 heures.",
          difficulty: 'hard',
          points: 30,
          triggeringSubscore: 'compulsivity',
          triggeringValue: 0.91,
          targetAudience: 'child',
        },
      ])
    );
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.mission.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          scoreSnapshotId: 99,
          status: 'pending',
          targetAudience: 'child',
          type: 'real_world',
          triggeringSubscore: 'compulsivity',
          triggeringValue: 0.91,
        }),
      })
    );
  });

  test("persisted recommendations have status='active'", async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(
      buildAiResponse([{ type: 'a', severity: 'high', messageFr: '1' }])
    );
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    expect(prisma.recommendation.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          status: 'active',
        }),
      })
    );
  });

  test('subscoresJson shape stores addiction and wellbeing arrays', async () => {
    aiBehavioralClient.callBehavioralAnalyze.mockResolvedValue(buildAiResponse([]));
    await analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 });
    const createArg = prisma.behavioralScore.create.mock.calls[0][0];
    expect(createArg.data.subscoresJson).toEqual({
      addiction: [{ name: 'intensity', value: 0.8 }],
      wellbeing: [{ name: 'sleep', value: 0.3 }],
    });
  });

  test('AI client error is re-thrown unchanged', async () => {
    const err = new aiBehavioralClient.AiBehavioralValidationError('bad payload');
    aiBehavioralClient.callBehavioralAnalyze.mockRejectedValue(err);
    await expect(analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 })).rejects.toBe(err);
  });

  test('Prisma error is re-thrown', async () => {
    const errSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    prisma.usageEvent.findMany.mockRejectedValue(new Error('db down'));
    await expect(analyzeUserBehavior(42, { ageYears: 10, windowDays: 14 })).rejects.toThrow(
      'db down'
    );
    errSpy.mockRestore();
  });
});

describe('behavioralService.rankRecommendations', () => {
  test('sorts by severity high > medium > low > positive', () => {
    const out = rankRecommendations([
      { type: 'a', severity: 'positive', triggeringValue: 0.9 },
      { type: 'b', severity: 'low', triggeringValue: 0.9 },
      { type: 'c', severity: 'high', triggeringValue: 0.1 },
      { type: 'd', severity: 'medium', triggeringValue: 0.9 },
    ]);
    expect(out.map((r) => r.type)).toEqual(['c', 'd', 'b']);
  });

  test('within same severity sorts by triggeringValue descending', () => {
    const out = rankRecommendations([
      { type: 'a', severity: 'high', triggeringValue: 0.5 },
      { type: 'b', severity: 'high', triggeringValue: 0.8 },
      { type: 'c', severity: 'high', triggeringValue: 0.2 },
    ]);
    expect(out.map((r) => r.type)).toEqual(['b', 'a', 'c']);
  });

  test('null triggeringValue sorts last within severity tier', () => {
    const out = rankRecommendations([
      { type: 'a', severity: 'high', triggeringValue: null },
      { type: 'b', severity: 'high', triggeringValue: 0.3 },
      { type: 'c', severity: 'high', triggeringValue: 0.2 },
    ]);
    expect(out.map((r) => r.type)).toEqual(['b', 'c', 'a']);
  });

  test('returns at most 3 items', () => {
    const out = rankRecommendations([
      { type: 'a', severity: 'high' },
      { type: 'b', severity: 'high' },
      { type: 'c', severity: 'high' },
      { type: 'd', severity: 'high' },
    ]);
    expect(out).toHaveLength(3);
  });

  test('returns all items when input has fewer than 3', () => {
    const out = rankRecommendations([
      { type: 'a', severity: 'medium' },
      { type: 'b', severity: 'low' },
    ]);
    expect(out).toHaveLength(2);
  });
});

describe('behavioralService.getCurrentRecommendations', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('returns [] when no BehavioralScore exists', async () => {
    prisma.behavioralScore.findFirst.mockResolvedValue(null);
    const out = await getCurrentRecommendations(7);
    expect(out).toEqual([]);
    expect(prisma.recommendation.findMany).not.toHaveBeenCalled();
  });

  test('returns only active recs linked to latest snapshot', async () => {
    prisma.behavioralScore.findFirst.mockResolvedValue({ id: 10, userId: 7 });
    prisma.recommendation.findMany.mockResolvedValue([{ id: 1 }, { id: 2 }]);
    const out = await getCurrentRecommendations(7);
    expect(prisma.recommendation.findMany).toHaveBeenCalledWith({
      where: { userId: 7, scoreSnapshotId: 10, status: 'active' },
      orderBy: { createdAt: 'asc' },
    });
    expect(out).toHaveLength(2);
  });

  test('does not return dismissed or acted recs', async () => {
    prisma.behavioralScore.findFirst.mockResolvedValue({ id: 10, userId: 7 });
    prisma.recommendation.findMany.mockResolvedValue([{ id: 1, status: 'active' }]);
    const out = await getCurrentRecommendations(7);
    expect(out.every((r) => r.status === 'active' || r.status === undefined)).toBe(true);
  });

  test('does not return recs from older snapshots', async () => {
    prisma.behavioralScore.findFirst.mockResolvedValue({ id: 25, userId: 7 });
    prisma.recommendation.findMany.mockResolvedValue([{ id: 9, scoreSnapshotId: 25 }]);
    const out = await getCurrentRecommendations(7);
    expect(prisma.recommendation.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({ scoreSnapshotId: 25 }),
      })
    );
    expect(out[0].scoreSnapshotId).toBe(25);
  });
});

describe('behavioralService.getCurrentBehavioralMissions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('returns [] when no BehavioralScore exists', async () => {
    prisma.behavioralScore.findFirst.mockResolvedValue(null);
    const out = await getCurrentBehavioralMissions(7);
    expect(out).toEqual([]);
    expect(prisma.mission.findMany).not.toHaveBeenCalled();
  });

  test('returns pending missions linked to latest snapshot', async () => {
    prisma.behavioralScore.findFirst.mockResolvedValue({ id: 21, userId: 7 });
    prisma.mission.findMany.mockResolvedValue([{ id: 11 }, { id: 12 }]);
    const out = await getCurrentBehavioralMissions(7);
    expect(prisma.mission.findMany).toHaveBeenCalledWith({
      where: { userId: 7, scoreSnapshotId: 21, status: 'pending' },
      orderBy: { createdAt: 'asc' },
    });
    expect(out).toHaveLength(2);
  });
});
