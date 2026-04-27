const express = require('express');

const { ownershipGuard } = require('../middleware/ownershipGuard');
const { validateUsageEventsPayload } = require('../validators/usageValidators');
const usageService = require('../services/usageService');

const router = express.Router();

router.post(
  '/events',
  ownershipGuard({ source: 'body', key: 'userId' }),
  async (req, res) => {
    try {
      const validation = validateUsageEventsPayload(req.body);
      if (!validation.ok) {
        return res.status(400).json({
          success: false,
          message: validation.message,
        });
      }

      const userId = req.validatedUserId;
      const { events } = validation.value;
      const result = await usageService.insertUsageEvents(userId, events);
      return res.status(200).json(result);
    } catch (err) {
      console.error(err);
      return res.status(500).json({
        success: false,
        message: err.message || 'Failed to ingest usage events',
      });
    }
  }
);

module.exports = router;
