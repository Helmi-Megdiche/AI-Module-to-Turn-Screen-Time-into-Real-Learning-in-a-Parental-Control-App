/**
 * Educational score (CDC §4.3): AI normalization, persistence, and mission routing edge cases.
 */

jest.mock('../config/prisma', () => ({
  $transaction: jest.fn(),
  analysis: {
    findMany: jest.fn().mockResolvedValue([]),
    findFirst: jest.fn().mockResolvedValue(null),
  },
  user: { findUnique: jest.fn() },
}));

jest.mock('../services/aiService', () => {
  const actual = jest.requireActual('../services/aiService');
  return {
    ...actual,
    analyzeImage: jest.fn(),
  };
});

jest.mock('../services/badgeService', () => ({
  awardPointBadges: jest.fn(),
}));

const prisma = require('../config/prisma');
const aiService = require('../services/aiService');
const { normalizeAnalyzeResponse } = require('../services/aiService');
const analyzeService = require('../services/analyzeService');
const { runAnalyze } = analyzeService;
const { selectMissionType } = require('../services/personalizationService');
const { RISKY_THRESHOLD } = require('../config');

describe('educational — aiService.normalizeAnalyzeResponse', () => {
  test('forwards educationalScore when present in Python response', () => {
    const raw = {
      riskScore: 0.2,
      category: 'educational',
      educationalScore: 0.72,
      text: 'lesson notes',
      matchedKeywords: [],
      displayText: '',
    };
    expect(normalizeAnalyzeResponse(raw).educationalScore).toBe(0.72);
  });

  test('defaults educationalScore to 0.0 when omitted', () => {
    const raw = {
      riskScore: 0.2,
      category: 'safe',
      text: 'hello there',
      matchedKeywords: [],
      displayText: '',
    };
    const out = normalizeAnalyzeResponse(raw);
    expect(out.educationalScore).toBe(0.0);
    expect(out.educationalScore).not.toBeUndefined();
  });
});

describe('educational — analyzeService.runAnalyze persistence', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(analyzeService, 'getRecentExposureStats').mockResolvedValue({
      total: 0,
      riskyCount: 0,
      dangerousCount: 0,
      exposureRate: 0,
      lastDangerousAt: null,
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  function wireTransaction(tx) {
    prisma.$transaction.mockImplementation(async (cb) => cb(tx));
  }

  test('Analysis.create receives educationalScore from AI', async () => {
    aiService.analyzeImage.mockResolvedValue({
      text: 'learn',
      displayText: 'learn',
      matchedKeywords: [],
      riskScore: 0.2,
      category: 'educational',
      educationalScore: 0.68,
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 0,
          interests: [],
          engagementScore: 0.5,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
        }),
        update: jest.fn().mockResolvedValue({ id: 1, points: 2 }),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 10 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 20 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'Zm9v' });

    expect(tx.analysis.create).toHaveBeenCalledTimes(1);
    const createArg = tx.analysis.create.mock.calls[0][0];
    expect(createArg.data).toMatchObject({ educationalScore: 0.68 });
  });

  test('Analysis.create uses educationalScore 0.0 when AI omits field', async () => {
    aiService.analyzeImage.mockResolvedValue({
      text: 'plain',
      displayText: 'plain',
      matchedKeywords: [],
      riskScore: 0.2,
      category: 'safe',
    });

    const tx = {
      user: {
        findUnique: jest.fn().mockResolvedValue({
          id: 1,
          age: 10,
          points: 0,
          interests: [],
          engagementScore: 0.5,
          lastSafeMissionAt: null,
          safePointsToday: 0,
          lastSafeResetDate: null,
        }),
        update: jest.fn().mockResolvedValue({ id: 1, points: 2 }),
      },
      analysis: { create: jest.fn().mockResolvedValue({ id: 10 }) },
      mission: { create: jest.fn().mockResolvedValue({ id: 20 }) },
    };
    wireTransaction(tx);

    await runAnalyze({ userId: 1, age: 10, image: 'YmFy' });

    const createArg = tx.analysis.create.mock.calls[0][0];
    expect(createArg.data).toMatchObject({ educationalScore: 0.0 });
  });
});

describe('educational — personalizationService.selectMissionType', () => {
  test('category educational with riskScore >= RISKY_THRESHOLD skips strict early-return path', () => {
    const eduQuiz = selectMissionType({ age: 15, interests: [], engagementScore: 0.8 }, 0.2, 'educational');
    const riskRealWorld = selectMissionType({ age: 15, interests: [], engagementScore: 0.8 }, 0.5, 'educational');
    expect(eduQuiz).toBe('quiz');
    expect(riskRealWorld).toBe('real_world');
    expect(0.5).toBeGreaterThanOrEqual(RISKY_THRESHOLD);
  });

  test('category safe with low risk does not use educational early-return', () => {
    const safeResult = selectMissionType({ age: 15, interests: [], engagementScore: 0.8 }, 0.1, 'safe');
    const eduHypothetical = selectMissionType({ age: 15, interests: [], engagementScore: 0.8 }, 0.1, 'educational');
    expect(safeResult).toBe('real_world');
    expect(eduHypothetical).toBe('quiz');
  });
});
