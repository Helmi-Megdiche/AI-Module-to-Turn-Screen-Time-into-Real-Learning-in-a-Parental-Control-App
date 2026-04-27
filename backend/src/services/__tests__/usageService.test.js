jest.mock('../../config/prisma', () => ({
  usageEvent: {
    createMany: jest.fn(),
    deleteMany: jest.fn(),
  },
}));

const prisma = require('../../config/prisma');
const { insertUsageEvents, cleanupOldUsageEvents } = require('../usageService');

describe('usageService.insertUsageEvents', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('inserts usage event batch', async () => {
    prisma.usageEvent.createMany.mockResolvedValue({ count: 2 });
    const events = [
      {
        eventType: 'unlock',
        appPackage: null,
        startedAt: new Date('2026-04-20T10:00:00.000Z'),
        endedAt: null,
        durationSec: null,
      },
      {
        eventType: 'app_session',
        appPackage: 'com.example.app',
        startedAt: new Date('2026-04-20T10:05:00.000Z'),
        endedAt: new Date('2026-04-20T10:10:00.000Z'),
        durationSec: 300,
      },
    ];

    const out = await insertUsageEvents(7, events);

    expect(prisma.usageEvent.createMany).toHaveBeenCalledWith({
      data: expect.arrayContaining([
        expect.objectContaining({
          userId: 7,
          eventType: 'unlock',
        }),
      ]),
    });
    expect(out).toEqual({ inserted: 2, rejected: 0 });
  });
});

describe('usageService.cleanupOldUsageEvents', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('deletes rows older than 30 days', async () => {
    prisma.usageEvent.deleteMany.mockResolvedValue({ count: 5 });

    const now = new Date('2026-04-20T00:00:00.000Z');
    const deleted = await cleanupOldUsageEvents(now);

    const whereArg = prisma.usageEvent.deleteMany.mock.calls[0][0].where;
    expect(whereArg.createdAt.lt.toISOString()).toBe('2026-03-21T00:00:00.000Z');
    expect(deleted).toBe(5);
  });
});
