/**
 * Simple liveness probe for monitoring or `curl` checks (`GET /api/health`).
 */
function getHealth(req, res) {
  res.json({
    success: true,
    message: 'API is running',
  });
}

module.exports = { getHealth };
