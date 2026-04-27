jest.mock('axios', () => ({
  post: jest.fn(),
  isAxiosError: jest.fn((err) => Boolean(err?.isAxiosError)),
}));

const axios = require('axios');
const {
  callBehavioralAnalyze,
  AiBehavioralValidationError,
  AiBehavioralFailureError,
  AiBehavioralUnreachableError,
} = require('../aiBehavioralClient');

describe('aiBehavioralClient.callBehavioralAnalyze', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    delete process.env.AI_BEHAVIORAL_URL;
    delete process.env.AI_BEHAVIORAL_TIMEOUT_MS;
  });

  test('200 response returns parsed body', async () => {
    axios.post.mockResolvedValue({
      status: 200,
      data: { addictionScore: 0.5 },
    });

    const out = await callBehavioralAnalyze({ userId: 1 });
    expect(out).toEqual({ addictionScore: 0.5 });
    expect(axios.post).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/behavioral/analyze',
      { userId: 1 },
      expect.objectContaining({ timeout: 10_000 })
    );
  });

  test('400 response throws AiBehavioralValidationError with detail', async () => {
    axios.post.mockRejectedValue({
      isAxiosError: true,
      response: { status: 400, data: { detail: 'bad payload' } },
      message: 'Request failed',
    });
    await expect(callBehavioralAnalyze({})).rejects.toBeInstanceOf(
      AiBehavioralValidationError
    );
    await expect(callBehavioralAnalyze({})).rejects.toMatchObject({
      detail: 'bad payload',
      aiStatus: 400,
    });
  });

  test('422 response throws AiBehavioralValidationError', async () => {
    axios.post.mockRejectedValue({
      isAxiosError: true,
      response: { status: 422, data: { detail: 'validation failed' } },
      message: 'Request failed',
    });
    await expect(callBehavioralAnalyze({})).rejects.toBeInstanceOf(
      AiBehavioralValidationError
    );
  });

  test('500 response throws AiBehavioralFailureError', async () => {
    axios.post.mockRejectedValue({
      isAxiosError: true,
      response: { status: 500, data: { detail: 'internal' } },
      message: 'Request failed',
    });
    await expect(callBehavioralAnalyze({})).rejects.toBeInstanceOf(
      AiBehavioralFailureError
    );
  });

  test('ECONNREFUSED throws AiBehavioralUnreachableError', async () => {
    axios.post.mockRejectedValue({
      isAxiosError: true,
      code: 'ECONNREFUSED',
      request: {},
      message: 'connect ECONNREFUSED',
    });
    await expect(callBehavioralAnalyze({})).rejects.toBeInstanceOf(
      AiBehavioralUnreachableError
    );
  });

  test('ECONNABORTED timeout throws AiBehavioralUnreachableError', async () => {
    axios.post.mockRejectedValue({
      isAxiosError: true,
      code: 'ECONNABORTED',
      request: {},
      message: 'timeout of 10000ms exceeded',
    });
    await expect(callBehavioralAnalyze({})).rejects.toBeInstanceOf(
      AiBehavioralUnreachableError
    );
  });

  test('honors AI_BEHAVIORAL_URL env var override', async () => {
    process.env.AI_BEHAVIORAL_URL = 'http://example.test/behavioral/analyze';
    axios.post.mockResolvedValue({ status: 200, data: { ok: true } });
    await callBehavioralAnalyze({ userId: 2 });
    expect(axios.post).toHaveBeenCalledWith(
      'http://example.test/behavioral/analyze',
      { userId: 2 },
      expect.any(Object)
    );
  });

  test('honors AI_BEHAVIORAL_TIMEOUT_MS env var override', async () => {
    process.env.AI_BEHAVIORAL_TIMEOUT_MS = '2500';
    axios.post.mockResolvedValue({ status: 200, data: { ok: true } });
    await callBehavioralAnalyze({ userId: 3 });
    expect(axios.post).toHaveBeenCalledWith(
      expect.any(String),
      { userId: 3 },
      expect.objectContaining({ timeout: 2500 })
    );
  });
});
