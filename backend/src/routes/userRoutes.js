const express = require('express');
const userController = require('../controllers/userController');

const router = express.Router();

router.get('/:id/history', userController.getHistory);
router.get('/:id/missions', userController.getMissions);
router.get('/:id/summary', userController.getSummary);

module.exports = router;
