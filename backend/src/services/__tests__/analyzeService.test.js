jest.mock('../../config/prisma', () => ({
  __esModule: true,
  default: {},
}));

const { missionForRiskScore } = require('../analyzeService');

describe('missionForRiskScore', () => {
  test('below 0.3 → continue mission, 2 points', () => {
    expect(missionForRiskScore(0)).toEqual({
      mission: 'Continue your activity responsibly',
      points: 2,
    });
    expect(missionForRiskScore(0.29)).toEqual({
      mission: 'Continue your activity responsibly',
      points: 2,
    });
  });

  test('0.3 through 0.7 inclusive → 10-minute break, 5 points', () => {
    expect(missionForRiskScore(0.3)).toEqual({
      mission: 'Take a 10-minute break',
      points: 5,
    });
    expect(missionForRiskScore(0.5)).toEqual({
      mission: 'Take a 10-minute break',
      points: 5,
    });
    expect(missionForRiskScore(0.7)).toEqual({
      mission: 'Take a 10-minute break',
      points: 5,
    });
  });

  test('above 0.7 → go outside, 10 points', () => {
    expect(missionForRiskScore(0.71)).toEqual({
      mission: 'Go outside for 20 minutes',
      points: 10,
    });
    expect(missionForRiskScore(0.98)).toEqual({
      mission: 'Go outside for 20 minutes',
      points: 10,
    });
  });
});
