const analyzeService = require('../services/analyzeService');

function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

function parseNonNegativeInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
    return null;
  }
  return n;
}

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
