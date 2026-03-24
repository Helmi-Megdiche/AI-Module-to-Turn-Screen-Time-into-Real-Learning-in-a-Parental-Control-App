const {
  normalizeInterests,
  selectMissionType,
  computeDifficulty,
} = require('../personalizationService');

describe('personalizationService.normalizeInterests', () => {
  test('normalizes and deduplicates string interests', () => {
    expect(normalizeInterests([' Games ', 'reading', 'GAMES', 1, null])).toEqual([
      'games',
      'reading',
    ]);
  });

  test('returns empty array for non-array values', () => {
    expect(normalizeInterests(null)).toEqual([]);
    expect(normalizeInterests('games')).toEqual([]);
  });
});

describe('personalizationService.selectMissionType', () => {
  test('dangerous risk always routes to quiz', () => {
    expect(
      selectMissionType(
        { age: 12, interests: ['games'], engagementScore: 0.1 },
        0.9,
        'dangerous'
      )
    ).toBe('quiz');
  });

  test('games interest routes to mini_game when risk is not dangerous', () => {
    expect(
      selectMissionType(
        { age: 12, interests: ['games'], engagementScore: 0.6 },
        0.5,
        'risky'
      )
    ).toBe('mini_game');
  });

  test('reading interest routes to quiz when risk is not dangerous', () => {
    expect(
      selectMissionType(
        { age: 11, interests: ['reading'], engagementScore: 0.6 },
        0.4,
        'risky'
      )
    ).toBe('quiz');
  });

  test('low engagement routes to mini_game', () => {
    expect(
      selectMissionType(
        { age: 11, interests: [], engagementScore: 0.2 },
        0.2,
        'safe'
      )
    ).toBe('mini_game');
  });

  test('age under 10 routes to puzzle when no higher-priority rule matches', () => {
    expect(
      selectMissionType(
        { age: 9, interests: [], engagementScore: 0.8 },
        0.2,
        'safe'
      )
    ).toBe('puzzle');
  });

  test('defaults to real_world otherwise', () => {
    expect(
      selectMissionType(
        { age: 12, interests: [], engagementScore: 0.8 },
        0.2,
        'safe'
      )
    ).toBe('real_world');
  });
});

describe('personalizationService.computeDifficulty', () => {
  test('returns bounded integer from 1 to 3', () => {
    expect(computeDifficulty({ engagementScore: 0.0 })).toBe(1);
    expect(computeDifficulty({ engagementScore: 0.5 })).toBe(2);
    expect(computeDifficulty({ engagementScore: 1.0 })).toBe(3);
    expect(computeDifficulty({ engagementScore: 2.0 })).toBe(3);
  });
});
