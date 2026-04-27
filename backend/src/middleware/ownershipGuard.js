const prisma = require('../config/prisma');

function parsePositiveInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || !Number.isInteger(n) || n <= 0) {
    return null;
  }
  return n;
}

function ownershipGuard(options = {}) {
  const { source = 'params', key = 'id' } = options;

  return async function ownershipGuardMiddleware(req, res, next) {
    try {
      const container = req[source] || {};
      const userId = parsePositiveInt(container[key]);

      if (userId === null) {
        return res.status(400).json({
          success: false,
          message: 'Invalid user id (positive integer required)',
        });
      }

      const user = await prisma.user.findUnique({
        where: { id: userId },
        select: { id: true },
      });

      if (!user) {
        return res.status(404).json({
          success: false,
          message: 'User not found',
        });
      }

      // TODO(auth): replace this DB existence guard with real JWT/session ownership checks.
      req.validatedUserId = userId;
      return next();
    } catch (err) {
      console.error(err);
      return res.status(500).json({
        success: false,
        message: 'Failed to validate user ownership',
      });
    }
  };
}

module.exports = { ownershipGuard, parsePositiveInt };
