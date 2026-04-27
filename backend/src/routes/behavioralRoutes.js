const express = require('express');

const { ownershipGuard } = require('../middleware/ownershipGuard');
const behavioralService = require('../services/behavioralService');
const {
  AiBehavioralValidationError,
  AiBehavioralFailureError,
  AiBehavioralUnreachableError,
} = require('../services/aiBehavioralClient');

const router = express.Router();

function parseNonNegativeNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) {
    return null;
  }
  return n;
}

function parseIntInRange(value, min, max) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < min || n > max) {
    return null;
  }
  return n;
}

function validateSummary(raw, fields, fieldName) {
  if (raw === undefined) {
    return {
      ok: true,
      value: undefined,
    };
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return { ok: false, message: `${fieldName} must be an object` };
  }
  const out = {};
  for (const key of fields) {
    const parsed = parseNonNegativeNumber(raw[key]);
    if (parsed === null) {
      return { ok: false, message: `${fieldName}.${key} must be a number >= 0` };
    }
    out[key] = parsed;
  }
  return { ok: true, value: out };
}

router.post('/:id/behavioral/analyze', ownershipGuard(), async (req, res) => {
  try {
    const ageYears = parseIntInRange(req.body?.ageYears, 2, 25);
    if (ageYears === null) {
      return res.status(400).json({
        error: 'validation_error',
        detail: 'ageYears must be an integer between 2 and 25',
      });
    }

    const rawWindow = req.body?.windowDays;
    const windowDays = rawWindow === undefined ? 14 : parseIntInRange(rawWindow, 7, 30);
    if (windowDays === null) {
      return res.status(400).json({
        error: 'validation_error',
        detail: 'windowDays must be an integer between 7 and 30',
      });
    }

    const contentValidation = validateSummary(
      req.body?.contentSummary,
      ['educationalCount', 'riskyCount', 'dangerousCount', 'total'],
      'contentSummary'
    );
    if (!contentValidation.ok) {
      return res.status(400).json({ error: 'validation_error', detail: contentValidation.message });
    }

    const missionValidation = validateSummary(
      req.body?.missionSummary,
      ['completed', 'assigned'],
      'missionSummary'
    );
    if (!missionValidation.ok) {
      return res.status(400).json({ error: 'validation_error', detail: missionValidation.message });
    }

    const result = await behavioralService.analyzeUserBehavior(req.validatedUserId, {
      ageYears,
      windowDays,
      contentSummary: contentValidation.value,
      missionSummary: missionValidation.value,
    });
    return res.status(200).json(result);
  } catch (err) {
    if (err instanceof AiBehavioralValidationError) {
      return res.status(400).json({ error: 'ai_validation', detail: err.detail });
    }
    if (err instanceof AiBehavioralFailureError) {
      return res.status(502).json({ error: 'ai_failure', detail: err.detail });
    }
    if (err instanceof AiBehavioralUnreachableError) {
      return res.status(503).json({ error: 'ai_unreachable', detail: err.detail });
    }

    console.error(err);
    return res.status(500).json({ error: 'internal_error' });
  }
});

router.get('/:id/recommendations/current', ownershipGuard(), async (req, res) => {
  try {
    const recommendations = await behavioralService.getCurrentRecommendations(req.validatedUserId);
    return res.status(200).json(recommendations);
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'internal_error' });
  }
});

router.get('/:id/missions/current', ownershipGuard(), async (req, res) => {
  try {
    const missions = await behavioralService.getCurrentBehavioralMissions(req.validatedUserId);
    return res.status(200).json(missions);
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: 'internal_error' });
  }
});

module.exports = router;
