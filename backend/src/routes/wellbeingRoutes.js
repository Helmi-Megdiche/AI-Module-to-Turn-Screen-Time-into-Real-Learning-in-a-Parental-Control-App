const express = require('express');

const { ownershipGuard, parsePositiveInt } = require('../middleware/ownershipGuard');
const { parseFiniteInt, validateRecommendationStatus } = require('../validators/usageValidators');
const behavioralService = require('../services/behavioralService');
const recommendationService = require('../services/recommendationService');

const router = express.Router();

router.get('/:id/wellbeing', ownershipGuard(), async (req, res) => {
  try {
    const rawWindow = req.query.window;
    const windowDays =
      rawWindow === undefined ? undefined : parseFiniteInt(rawWindow);

    if (rawWindow !== undefined && (windowDays === null || windowDays <= 0)) {
      return res.status(400).json({
        success: false,
        message: 'window must be a positive integer',
      });
    }

    const latest = await behavioralService.getLatestBehavioralScore(
      req.validatedUserId,
      windowDays
    );
    if (!latest) {
      return res.status(404).json({
        success: false,
        message: 'No behavioral score found',
      });
    }
    return res.status(200).json(latest);
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to fetch wellbeing score',
    });
  }
});

router.get('/:id/recommendations', ownershipGuard(), async (req, res) => {
  try {
    const statusValidation = validateRecommendationStatus(req.query.status);
    if (!statusValidation.ok) {
      return res.status(400).json({
        success: false,
        message: statusValidation.message,
      });
    }
    const recommendations = await recommendationService.listRecommendations(
      req.validatedUserId,
      statusValidation.value
    );
    return res.status(200).json(recommendations);
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to list recommendations',
    });
  }
});

router.post(
  '/:id/recommendations/:recId/dismiss',
  ownershipGuard(),
  async (req, res) => {
    try {
      const recId = parsePositiveInt(req.params.recId);
      if (recId === null) {
        return res.status(400).json({
          success: false,
          message: 'Invalid recommendation id (positive integer required)',
        });
      }
      const result = await recommendationService.markRecommendationStatus(
        req.validatedUserId,
        recId,
        'dismissed'
      );
      if (!result.count) {
        return res.status(404).json({
          success: false,
          message: 'Recommendation not found',
        });
      }
      return res.status(200).json({ success: true });
    } catch (err) {
      console.error(err);
      return res.status(500).json({
        success: false,
        message: err.message || 'Failed to dismiss recommendation',
      });
    }
  }
);

router.post('/:id/recommendations/:recId/acted', ownershipGuard(), async (req, res) => {
  try {
    const recId = parsePositiveInt(req.params.recId);
    if (recId === null) {
      return res.status(400).json({
        success: false,
        message: 'Invalid recommendation id (positive integer required)',
      });
    }
    const result = await recommendationService.markRecommendationStatus(
      req.validatedUserId,
      recId,
      'acted'
    );
    if (!result.count) {
      return res.status(404).json({
        success: false,
        message: 'Recommendation not found',
      });
    }
    return res.status(200).json({ success: true });
  } catch (err) {
    console.error(err);
    return res.status(500).json({
      success: false,
      message: err.message || 'Failed to mark recommendation as acted',
    });
  }
});

module.exports = router;
