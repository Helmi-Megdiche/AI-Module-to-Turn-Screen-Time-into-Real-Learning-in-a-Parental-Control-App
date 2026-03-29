/** `GET /api/user/:id/history|missions|summary` — `:id` is the child profile id. */
const express = require('express');
const userController = require('../controllers/userController');

const router = express.Router();

router.get('/list', userController.listUsers);
router.get('/:userId/exposure-summary', userController.getExposureSummary);
router.get('/:userId/dashboard', userController.getDashboard);
router.get('/:userId/risk-series', userController.getRiskSeries);
router.get('/:id/history', userController.getHistory);
router.get('/:id/missions', userController.getMissions);
router.get('/:id/badges', userController.getBadges);
router.get('/:id/summary', userController.getSummary);
router.get('/:id/profile', userController.getProfile);
router.put('/:id/interests', userController.updateInterests);
router.put('/:id/age', userController.updateAge);

module.exports = router;
