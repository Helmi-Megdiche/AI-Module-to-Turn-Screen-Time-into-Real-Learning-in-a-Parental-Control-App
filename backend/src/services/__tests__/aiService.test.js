const axios = require('axios');
const { analyzeImage } = require('../aiService');

describe('analyzeImage', () => {
  beforeEach(() => {
    jest.spyOn(axios, 'post').mockReset();
    delete process.env.AI_ANALYZE_URL;
    delete process.env.AI_REQUEST_TIMEOUT_MS;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('POSTs trimmed base64 to default URL and returns response data', async () => {
    const payload = {
      text: 'hello',
      displayText: 'hello',
      matchedKeywords: [],
      riskScore: 0.1,
      category: 'safe',
    };
    axios.post.mockResolvedValue({ data: payload });

    const out = await analyzeImage('  abcd  ');

    expect(axios.post).toHaveBeenCalledTimes(1);
    expect(axios.post).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/analyze',
      { image: '  abcd  ' },
      expect.objectContaining({
        timeout: 120_000,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    expect(out).toEqual({ ...payload, educationalScore: 0.0 });
  });

  test('uses AI_ANALYZE_URL and AI_REQUEST_TIMEOUT_MS when set', async () => {
    process.env.AI_ANALYZE_URL = 'http://example.test/x';
    process.env.AI_REQUEST_TIMEOUT_MS = '5000';
    axios.post.mockResolvedValue({
      data: { text: '', category: 'safe', riskScore: 0 },
    });

    const out = await analyzeImage('eA==');
    expect(out.educationalScore).toBe(0);

    expect(axios.post).toHaveBeenCalledWith(
      'http://example.test/x',
      { image: 'eA==' },
      expect.objectContaining({ timeout: 5000 })
    );
  });

  test('wraps axios errors with message', async () => {
    const err = new Error('Network Error');
    err.isAxiosError = true;
    err.response = { status: 503, data: { detail: 'busy' } };
    axios.post.mockRejectedValue(err);

    await expect(analyzeImage('Zg==')).rejects.toThrow(
      /AI service request failed \(HTTP 503\)/
    );
    await expect(analyzeImage('Zg==')).rejects.toThrow(/busy/);
  });
});
