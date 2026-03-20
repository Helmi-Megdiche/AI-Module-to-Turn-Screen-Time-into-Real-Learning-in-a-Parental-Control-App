const express = require('express');
const healthRoutes = require('./healthRoutes');
const analyzeRoutes = require('./analyzeRoutes');

const router = express.Router();

router.use('/health', healthRoutes);
router.use('/analyze', analyzeRoutes);

module.exports = router;
