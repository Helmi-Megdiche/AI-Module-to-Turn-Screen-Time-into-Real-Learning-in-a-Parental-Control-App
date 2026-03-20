const userService = require('../services/userService');

function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

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

module.exports = {
  getHistory,
  getMissions,
  getSummary,
};
