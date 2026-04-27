const prisma = require('../config/prisma');

async function insertUsageEvents(userId, events) {
  if (!events.length) {
    return { inserted: 0, rejected: 0 };
  }

  const data = events.map((event) => ({
    userId,
    eventType: event.eventType,
    appPackage: event.appPackage,
    startedAt: event.startedAt,
    endedAt: event.endedAt,
    durationSec: event.durationSec,
  }));

  const result = await prisma.usageEvent.createMany({ data });
  return {
    inserted: result.count ?? 0,
    rejected: events.length - (result.count ?? 0),
  };
}

async function cleanupOldUsageEvents(now = new Date()) {
  const cutoff = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  const result = await prisma.usageEvent.deleteMany({
    where: {
      createdAt: {
        lt: cutoff,
      },
    },
  });
  return result.count ?? 0;
}

module.exports = {
  insertUsageEvents,
  cleanupOldUsageEvents,
};
