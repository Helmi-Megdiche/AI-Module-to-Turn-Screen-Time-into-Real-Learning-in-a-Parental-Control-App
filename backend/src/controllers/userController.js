/**
 * Read-only user endpoints: history (analyses + missions), missions list, aggregated summary.
 * URL shape: `/api/user/:id/...` — `id` must be a positive integer (same id clients send to `/analyze`).
 */
const userService = require('../services/userService');
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

module.exports = {
  getHistory,
  getMissions,
  getBadges,
  getSummary,
  getProfile,
  updateInterests,
};
