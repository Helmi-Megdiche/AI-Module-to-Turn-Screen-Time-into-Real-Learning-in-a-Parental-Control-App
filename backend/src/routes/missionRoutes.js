const express = require('express');
const missionController = require('../controllers/missionController');

const router = express.Router();

router.put('/:id/complete', missionController.completeMission);

module.exports = router;
