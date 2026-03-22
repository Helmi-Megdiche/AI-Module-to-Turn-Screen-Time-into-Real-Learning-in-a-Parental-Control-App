const missionService = require('../services/missionService');

function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

function parseNonNegativeInt(value, fallback = 0) {
  if (value === undefined || value === null || value === '') {
    return fallback;
  }

  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) {
    return null;
  }

  return n;
}

async function completeMission(req, res) {
  try {
    const missionId = parsePositiveInt(req.params.id);
    if (missionId === null) {
      return res.status(400).json({
        success: false,
        message: 'Invalid mission id (positive integer required)',
      });
    }

    const bonusPoints = parseNonNegativeInt(req.body?.bonusPoints, 0);
    if (bonusPoints === null) {
      return res.status(400).json({
        success: false,
        message: 'Invalid bonusPoints (non-negative integer required)',
      });
    }

    const mission = await missionService.completeMission(missionId, bonusPoints);
    return res.json({
      success: true,
      mission,
    });
  } catch (err) {
    if (err && err.code === 'MISSION_NOT_FOUND') {
      return res.status(404).json({
        success: false,
        message: err.message,
      });
    }

    if (err && err.code === 'MISSION_ALREADY_COMPLETED') {
      return res.status(409).json({
        success: false,
        message: err.message,
      });
    }

    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to complete mission',
    });
  }
}

module.exports = {
  completeMission,
};
