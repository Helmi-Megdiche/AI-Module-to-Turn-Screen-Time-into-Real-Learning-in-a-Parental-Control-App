/** `POST /api/analyze` — body: `{ userId, age, image? }`. */
const express = require('express');
const { postAnalyze } = require('../controllers/analyzeController');

const router = express.Router();

router.post('/', postAnalyze);

module.exports = router;
