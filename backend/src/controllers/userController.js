/**
 * User endpoints: history, missions, summary, badges, profile read, interests/age updates for demo.
 * URL shape: `/api/user/:id/...` — `id` must be a positive integer (same id clients send to `/analyze`).
 */
const prisma = require('../config/prisma');
const userService = require('../services/userService');
const {
  getRecentExposureStats,
  getExposureTrend,
} = require('../services/analyzeService');
const {
  getMissionStats,
  getEducationalStats,
  getProgressSnapshot,
  bucketByDay,
  bucketByHour,
} = require('../services/dashboardService');
const ALLOWED_INTERESTS = [
  'games',
  'reading',
  'science',
  'sports',
  'art',
  'music',
  'technology',
  'logic',
  'creativity',
];

/** `GET /api/user/list` — demo/parent picker: all users (lightweight fields). */
async function listUsers(req, res) {
  try {
    const users = await prisma.user.findMany({
      select: {
        id: true,
        age: true,
        points: true,
        engagementScore: true,
        completedMissions: true,
      },
      orderBy: { id: 'asc' },
    });
    return res.status(200).json({ users });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'Failed to list users' });
  }
}

function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

/** Parse `skip` query (pagination offset). */
function parseSkip(value) {
  if (value === undefined || value === '' || value === null) {
    return 0;
  }
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
    return null;
  }
  return n;
}

/** Parse `take` query (page size), capped by `userService.MAX_TAKE`. */
function parseTake(value) {
  if (value === undefined || value === '' || value === null) {
    return userService.DEFAULT_TAKE;
  }
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 1) {
    return null;
  }
  return Math.min(n, userService.MAX_TAKE);
}

/** Reads `:id` from route; responds 400 and returns null if invalid. */
function getUserIdOr400(req, res) {
  const userId = parsePositiveInt(req.params.id);
  if (userId === null) {
    res.status(400).json({
      success: false,
      message: 'Invalid user id (positive integer required)',
    });
    return null;
  }
  return userId;
}

/** Validates `skip` / `take` query params together. */
function getPaginationOr400(req, res) {
  const skip = parseSkip(req.query.skip);
  if (skip === null) {
    res.status(400).json({
      success: false,
      message: 'Invalid skip (non-negative integer required)',
    });
    return null;
  }

  const take = parseTake(req.query.take);
  if (take === null) {
    res.status(400).json({
      success: false,
      message: `Invalid take (integer 1–${userService.MAX_TAKE}, default ${userService.DEFAULT_TAKE})`,
    });
    return null;
  }

  return { skip, take };
}

/** `GET /api/user/:id/history` — recent analyses and missions side by side. */
async function getHistory(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    const pagination = getPaginationOr400(req, res);
    if (pagination === null) {
      return;
    }

    console.log(`[USER] Fetch history for user ${userId}`);

    const data = await userService.getHistory(userId, pagination);
    if (!data) {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }

    return res.json({
      success: true,
      analyses: data.analyses,
      missions: data.missions,
      pagination: {
        skip: data.skip,
        take: data.take,
      },
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to load history',
    });
  }
}

/** `GET /api/user/:id/missions` — mission rows only. */
async function getMissions(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    const pagination = getPaginationOr400(req, res);
    if (pagination === null) {
      return;
    }

    console.log(`[USER] Fetch missions for user ${userId}`);

    const result = await userService.getMissions(userId, pagination);
    if (result === null) {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }

    return res.json({
      success: true,
      missions: result.missions,
      pagination: {
        skip: result.skip,
        take: result.take,
      },
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to load missions',
    });
  }
}

/** `GET /api/user/:id/badges` — earned badges with metadata and award time. */
async function getBadges(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    const result = await userService.getBadges(userId);
    if (result === null) {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }

    return res.json({
      success: true,
      badges: result.badges,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to load badges',
    });
  }
}

/** `GET /api/user/:id/summary` — points, counts, average risk, dangerous analyses count. */
async function getSummary(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    console.log(`[USER] Fetch summary for user ${userId}`);

    const summary = await userService.getSummary(userId);
    if (!summary) {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }

    return res.json({
      success: true,
      summary,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to load summary',
    });
  }
}

/** `GET /api/user/:id/profile` — interests + engagement for demo personalization UI. */
async function getProfile(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    const profile = await userService.getProfile(userId);
    if (!profile) {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }

    return res.json({
      success: true,
      user: profile,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to load profile',
    });
  }
}

/** `PUT /api/user/:id/interests` — update allowed interests list for personalization. */
async function updateInterests(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    const incoming = req.body?.interests;
    if (!Array.isArray(incoming)) {
      return res.status(400).json({
        success: false,
        message: 'interests must be an array',
      });
    }

    const sanitized = Array.from(
      new Set(
        incoming
          .filter((x) => typeof x === 'string')
          .map((x) => x.trim().toLowerCase())
          .filter((x) => ALLOWED_INTERESTS.includes(x))
      )
    );

    const result = await userService.updateInterests(userId, sanitized);
    return res.json({
      success: true,
      interests: result.interests,
      engagementScore: result.engagementScore,
    });
  } catch (err) {
    console.error(err);
    if (err?.code === 'P2025') {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to update interests',
    });
  }
}

const EXPOSURE_WINDOW_MAP = {
  '1h': 60,
  '24h': 1440,
  '7d': 10080,
};

/** `GET /api/user/:userId/exposure-summary` — rolling exposure stats + trend (fréquence d'exposition). */
async function getExposureSummary(req, res) {
  try {
    const userId = parsePositiveInt(req.params.userId);
    if (userId === null) {
      return res.status(400).json({
        error: 'Invalid user id (positive integer required)',
      });
    }

    const rawWindow = req.query.window;
    const windowKey =
      rawWindow === undefined || rawWindow === '' ? '24h' : String(rawWindow);

    const windowMinutes = EXPOSURE_WINDOW_MAP[windowKey];
    if (windowMinutes === undefined) {
      return res.status(400).json({
        error: 'Invalid window. Use 1h, 24h, or 7d.',
      });
    }

    const since = new Date(Date.now() - windowMinutes * 60 * 1000);

    const [stats, trend, grouped] = await Promise.all([
      getRecentExposureStats(userId, windowMinutes),
      getExposureTrend(userId, windowMinutes),
      prisma.analysis.groupBy({
        by: ['category'],
        where: {
          userId,
          createdAt: { gte: since },
        },
        _count: { category: true },
      }),
    ]);

    const categoryBreakdown = {};
    for (const row of grouped) {
      categoryBreakdown[row.category] = row._count.category;
    }

    return res.status(200).json({
      userId,
      window: windowKey,
      totalAnalyses: stats.total,
      riskyCount: stats.riskyCount,
      dangerousCount: stats.dangerousCount,
      exposureRate: stats.exposureRate,
      categoryBreakdown,
      trend,
      lastDangerousAt: stats.lastDangerousAt
        ? stats.lastDangerousAt.toISOString()
        : null,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to fetch exposure summary',
    });
  }
}

/** `GET /api/user/:userId/dashboard` — aggregate parent dashboard (exposure, progress, missions, educational). */
async function getDashboard(req, res) {
  try {
    const userId = parsePositiveInt(req.params.userId);
    if (userId === null) {
      return res.status(400).json({
        error: 'Invalid user id (positive integer required)',
      });
    }

    const rawWindow = req.query.window;
    const windowKey =
      rawWindow === undefined || rawWindow === '' ? '7d' : String(rawWindow);

    const windowMinutes = EXPOSURE_WINDOW_MAP[windowKey];
    if (windowMinutes === undefined) {
      return res.status(400).json({
        error: 'Invalid window. Use 1h, 24h, or 7d.',
      });
    }

    const since = new Date(Date.now() - windowMinutes * 60 * 1000);

    const [
      stats,
      trend,
      grouped,
      missionStats,
      educationalStats,
      progressSnapshot,
    ] = await Promise.all([
      getRecentExposureStats(userId, windowMinutes),
      getExposureTrend(userId, windowMinutes),
      prisma.analysis.groupBy({
        by: ['category'],
        where: {
          userId,
          createdAt: { gte: since },
        },
        _count: { category: true },
      }),
      getMissionStats(userId, since),
      getEducationalStats(userId, since),
      getProgressSnapshot(userId),
    ]);

    const categoryBreakdown = {};
    for (const row of grouped) {
      categoryBreakdown[row.category] = row._count.category;
    }

    return res.status(200).json({
      userId,
      window: windowKey,
      exposure: {
        totalAnalyses: stats.total,
        riskyCount: stats.riskyCount,
        dangerousCount: stats.dangerousCount,
        exposureRate: stats.exposureRate,
        trend,
        categoryBreakdown,
        lastDangerousAt: stats.lastDangerousAt,
      },
      progress: progressSnapshot,
      missions: missionStats,
      educational: educationalStats,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to fetch dashboard',
    });
  }
}

/** `GET /api/user/:userId/risk-series` — bucketed risk time series for charts. */
async function getRiskSeries(req, res) {
  try {
    const userId = parsePositiveInt(req.params.userId);
    if (userId === null) {
      return res.status(400).json({
        error: 'Invalid user id (positive integer required)',
      });
    }

    const bucket = req.query.bucket ?? 'day';
    if (bucket !== 'day' && bucket !== 'hour') {
      return res.status(400).json({
        error: 'Invalid bucket. Use day or hour.',
      });
    }

    const fromDate = req.query.from
      ? new Date(req.query.from)
      : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    const toDate = req.query.to ? new Date(req.query.to) : new Date();

    if (Number.isNaN(fromDate.getTime())) {
      return res.status(400).json({ error: 'Invalid from date.' });
    }
    if (Number.isNaN(toDate.getTime())) {
      return res.status(400).json({ error: 'Invalid to date.' });
    }
    if (fromDate.getTime() >= toDate.getTime()) {
      return res.status(400).json({ error: 'from must be before to.' });
    }

    const rows = await prisma.analysis.findMany({
      where: {
        userId,
        createdAt: { gte: fromDate, lte: toDate },
      },
      select: {
        createdAt: true,
        riskScore: true,
        category: true,
        educationalScore: true,
      },
    });

    const series =
      bucket === 'hour'
        ? bucketByHour(rows, fromDate, toDate)
        : bucketByDay(rows, fromDate, toDate);

    return res.status(200).json({
      userId,
      from: fromDate.toISOString(),
      to: toDate.toISOString(),
      bucket,
      series,
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      error: 'Failed to fetch risk series',
    });
  }
}

/** `PUT /api/user/:id/age` — set child age for personalization (and badge ranges). */
async function updateAge(req, res) {
  try {
    const userId = getUserIdOr400(req, res);
    if (userId === null) {
      return;
    }

    const age = req.body?.age;
    if (typeof age !== 'number' || !Number.isInteger(age) || age < 0 || age > 120) {
      return res.status(400).json({
        success: false,
        message: 'Age must be a number between 0 and 120',
      });
    }

    const user = await userService.updateAge(userId, age);
    return res.json({ success: true, user });
  } catch (err) {
    console.error(err);
    if (err?.code === 'P2025') {
      return res.status(404).json({
        success: false,
        message: 'User not found',
      });
    }
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to update age',
    });
  }
}

module.exports = {
  listUsers,
  getHistory,
  getMissions,
  getBadges,
  getSummary,
  getProfile,
  updateInterests,
  updateAge,
  getExposureSummary,
  getDashboard,
  getRiskSeries,
};
