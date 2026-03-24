/**
 * HTTP handlers for `POST /api/analyze`.
 * Validates body (`userId`, `age`, optional `image` base64) and delegates to `analyzeService.runAnalyze`.
 */
const analyzeService = require('../services/analyzeService');

/** @param {unknown} value - from JSON body */
function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

/** @param {unknown} value - e.g. child age */
function parseNonNegativeInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
    return null;
  }
  return n;
}

/**
 * Runs screenshot analysis: calls Python AI when `image` is present, else returns a safe preview without DB write.
 * @param {import('express').Request} req
 * @param {import('express').Response} res
 */
async function postAnalyze(req, res) {
  try {
    const userId = parsePositiveInt(req.body.userId);
    const age = parseNonNegativeInt(req.body.age);
    const image = req.body.image;

    if (userId === null) {
      return res.status(400).json({
        success: false,
        message: 'Invalid or missing userId (positive integer required)',
      });
    }

    if (age === null) {
      return res.status(400).json({
        success: false,
        message: 'Invalid or missing age (non-negative integer required)',
      });
    }

    const { analysis, mission, user } = await analyzeService.runAnalyze({
      userId,
      age,
      image,
    });

    return res.json({
      success: true,
      timestamp: new Date().toISOString(),
      analysis,
      mission: {
        id: mission.id ?? null,
        type: mission.type ?? 'real_world',
        game:
          mission.game ??
          (mission.content && typeof mission.content === 'object'
            ? mission.content.game ?? null
            : null),
        reward:
          mission.reward ??
          (mission.content && typeof mission.content === 'object'
            ? mission.content.reward ?? null
            : null),
        content: mission.content ?? null,
        difficulty: mission.difficulty ?? 1,
        text: mission.mission,
        mission: mission.mission,
        points: mission.points,
        status: mission.status,
      },
      user: {
        id: user.id,
        points: user.points,
        createdAt: user.createdAt,
      },
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to process analysis',
    });
  }
}

module.exports = { postAnalyze };
