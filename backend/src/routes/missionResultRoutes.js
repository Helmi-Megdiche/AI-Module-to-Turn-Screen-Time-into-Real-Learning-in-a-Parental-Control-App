const express = require('express');
const missionResultController = require('../controllers/missionResultController');

const router = express.Router();

router.post('/result', missionResultController.submitResult);

module.exports = router;
