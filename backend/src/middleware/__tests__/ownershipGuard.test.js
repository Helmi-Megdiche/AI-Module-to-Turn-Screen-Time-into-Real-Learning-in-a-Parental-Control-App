jest.mock('../../config/prisma', () => ({
  user: {
    findUnique: jest.fn(),
  },
}));

const prisma = require('../../config/prisma');
const { ownershipGuard } = require('../ownershipGuard');

function mockRes() {
  return {
    status: jest.fn().mockReturnThis(),
    json: jest.fn().mockReturnThis(),
  };
}

describe('ownershipGuard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('sets req.validatedUserId and calls next for valid user', async () => {
    prisma.user.findUnique.mockResolvedValue({ id: 1 });
    const req = { params: { id: '1' } };
    const res = mockRes();
    const next = jest.fn();

    await ownershipGuard()(req, res, next);

    expect(req.validatedUserId).toBe(1);
    expect(next).toHaveBeenCalledTimes(1);
  });

  test('returns 400 for invalid user id format', async () => {
    const req = { params: { id: 'abc' } };
    const res = mockRes();
    const next = jest.fn();

    await ownershipGuard()(req, res, next);

    expect(res.status).toHaveBeenCalledWith(400);
    expect(next).not.toHaveBeenCalled();
  });

  test('returns 404 when user is missing', async () => {
    prisma.user.findUnique.mockResolvedValue(null);
    const req = { params: { id: '9' } };
    const res = mockRes();
    const next = jest.fn();

    await ownershipGuard()(req, res, next);

    expect(res.status).toHaveBeenCalledWith(404);
    expect(next).not.toHaveBeenCalled();
  });

  test('reads user id from body when configured', async () => {
    prisma.user.findUnique.mockResolvedValue({ id: 3 });
    const req = { body: { userId: 3 } };
    const res = mockRes();
    const next = jest.fn();

    await ownershipGuard({ source: 'body', key: 'userId' })(req, res, next);

    expect(req.validatedUserId).toBe(3);
    expect(next).toHaveBeenCalledTimes(1);
  });
});
