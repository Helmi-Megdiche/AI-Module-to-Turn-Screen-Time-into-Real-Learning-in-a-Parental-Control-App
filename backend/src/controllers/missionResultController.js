const missionResultService = require('../services/missionResultService');

function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

function parseOptionalInt(value) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n)) {
    return null;
  }
  return n;
}

function parseBoolean(value) {
  if (value === true || value === false) {
    return value;
  }
  return null;
}

async function submitResult(req, res) {
  try {
    const missionId = parsePositiveInt(req.body?.missionId);
    const userId = parsePositiveInt(req.body?.userId);
    const success = parseBoolean(req.body?.success);
    const score = parseOptionalInt(req.body?.score);
    const timeSpent = parseOptionalInt(req.body?.timeSpent);

    if (missionId === null) {
      return res
        .status(400)
        .json({ success: false, message: 'missionId must be a positive integer' });
    }
    if (userId === null) {
      return res
        .status(400)
        .json({ success: false, message: 'userId must be a positive integer' });
    }
    if (success === null) {
      return res
        .status(400)
        .json({ success: false, message: 'success must be a boolean' });
    }
    if (score === null) {
      return res.status(400).json({
        success: false,
        message: 'score must be an integer when provided',
      });
    }
    if (timeSpent === null || (timeSpent !== undefined && timeSpent < 0)) {
      return res.status(400).json({
        success: false,
        message: 'timeSpent must be a non-negative integer when provided',
      });
    }

    const result = await missionResultService.submitResult(missionId, userId, {
      score,
      success,
      timeSpent,
    });
    return res.json({ success: true, ...result });
  } catch (err) {
    if (err && err.code === 'MISSION_NOT_FOUND') {
      return res.status(404).json({ success: false, message: err.message });
    }
    if (
      err &&
      (err.code === 'MISSION_ALREADY_COMPLETED' ||
        err.code === 'MISSION_RESULT_ALREADY_SUBMITTED')
    ) {
      return res.status(409).json({ success: false, message: err.message });
    }
    if (err && err.code === 'MISSION_USER_MISMATCH') {
      return res.status(400).json({ success: false, message: err.message });
    }
    console.error(err);
    return res
      .status(500)
      .json({ success: false, message: err.message || 'Failed to submit mission result' });
  }
}

module.exports = { submitResult };
