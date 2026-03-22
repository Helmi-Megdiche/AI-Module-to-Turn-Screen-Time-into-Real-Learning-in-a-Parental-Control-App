jest.mock('../../config/prisma', () => ({
  $transaction: jest.fn(),
}));

const prisma = require('../../config/prisma');
const { completeMission } = require('../missionService');

describe('missionService.completeMission', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  function wireTransaction(tx) {
    prisma.$transaction.mockImplementation(async (cb) => cb(tx));
  }

  test('awards mission points when completing a pending mission', async () => {
    const tx = {
      mission: {
        findUnique: jest.fn().mockResolvedValue({
          id: 5,
          userId: 1,
          points: 10,
          status: 'pending',
          user: { id: 1 },
        }),
        update: jest.fn().mockResolvedValue({ id: 5, status: 'completed' }),
      },
      user: {
        update: jest.fn().mockResolvedValue({ id: 1, points: 10 }),
      },
    };
    wireTransaction(tx);

    const out = await completeMission(5, 0);

    expect(out).toEqual({ id: 5, status: 'completed' });
    expect(tx.user.update).toHaveBeenCalledTimes(1);
    expect(tx.user.update).toHaveBeenCalledWith({
      where: { id: 1 },
      data: { points: { increment: 10 } },
    });
  });

  test('awards mission points plus bonus points', async () => {
    const tx = {
      mission: {
        findUnique: jest.fn().mockResolvedValue({
          id: 6,
          userId: 2,
          points: 5,
          status: 'pending',
          user: { id: 2 },
        }),
        update: jest.fn().mockResolvedValue({ id: 6, status: 'completed' }),
      },
      user: {
        update: jest.fn().mockResolvedValue({ id: 2, points: 7 }),
      },
    };
    wireTransaction(tx);

    await completeMission(6, 2);

    expect(tx.user.update).toHaveBeenCalledTimes(2);
    expect(tx.user.update).toHaveBeenNthCalledWith(1, {
      where: { id: 2 },
      data: { points: { increment: 5 } },
    });
    expect(tx.user.update).toHaveBeenNthCalledWith(2, {
      where: { id: 2 },
      data: { points: { increment: 2 } },
    });
  });

  test('throws MISSION_NOT_FOUND when mission does not exist', async () => {
    const tx = {
      mission: {
        findUnique: jest.fn().mockResolvedValue(null),
      },
      user: { update: jest.fn() },
    };
    wireTransaction(tx);

    await expect(completeMission(999, 0)).rejects.toMatchObject({
      code: 'MISSION_NOT_FOUND',
    });
    expect(tx.user.update).not.toHaveBeenCalled();
  });

  test('throws MISSION_ALREADY_COMPLETED when mission is already completed', async () => {
    const tx = {
      mission: {
        findUnique: jest.fn().mockResolvedValue({
          id: 7,
          userId: 3,
          points: 10,
          status: 'completed',
          user: { id: 3 },
        }),
      },
      user: { update: jest.fn() },
    };
    wireTransaction(tx);

    await expect(completeMission(7, 0)).rejects.toMatchObject({
      code: 'MISSION_ALREADY_COMPLETED',
    });
    expect(tx.user.update).not.toHaveBeenCalled();
  });
});
