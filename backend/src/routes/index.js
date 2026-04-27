/**
 * Central API router mounted at `/api` in `app.js`.
 * - `/api/health` — liveness
 * - `/api/analyze` — screenshot analysis
 * - `/api/user` — history / missions / summary
 */
const express = require('express');
const healthRoutes = require('./healthRoutes');
const analyzeRoutes = require('./analyzeRoutes');
const userRoutes = require('./userRoutes');
const missionRoutes = require('./missionRoutes');
const missionResultRoutes = require('./missionResultRoutes');
const usageRoutes = require('./usageRoutes');
const behavioralRoutes = require('./behavioralRoutes');
const wellbeingRoutes = require('./wellbeingRoutes');

const router = express.Router();

router.use('/health', healthRoutes);
router.use('/analyze', analyzeRoutes);
router.use('/user', userRoutes);
router.use('/mission', missionRoutes);
router.use('/mission', missionResultRoutes);
router.use('/usage', usageRoutes);
router.use('/user', behavioralRoutes);
router.use('/user', wellbeingRoutes);

module.exports = router;
