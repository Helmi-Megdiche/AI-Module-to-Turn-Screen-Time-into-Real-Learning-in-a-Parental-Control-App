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
  test('dangerous risk routes to mini_game when interests include games', () => {
    expect(
      selectMissionType(
        { age: 12, interests: ['games'], engagementScore: 0.1 },
        0.9,
        'dangerous'
      )
    ).toBe('mini_game');
  });

  test('dangerous risk routes to mini_game when engagement is low', () => {
    expect(
      selectMissionType(
        { age: 12, interests: [], engagementScore: 0.2 },
        0.9,
        'dangerous'
      )
    ).toBe('mini_game');
  });

  test('dangerous risk defaults to quiz when no games interest and engagement is not low', () => {
    expect(
      selectMissionType(
        { age: 12, interests: ['reading'], engagementScore: 0.8 },
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

  test('low engagement with safe risk routes to real_world', () => {
    expect(
      selectMissionType(
        { age: 11, interests: [], engagementScore: 0.2 },
        0.2,
        'safe'
      )
    ).toBe('real_world');
  });

  test('age under 10 routes to puzzle when no higher-priority rule matches', () => {
    expect(
      selectMissionType(
        { age: 9, interests: [], engagementScore: 0.8 },
        0.5,
        'risky'
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

  test('educational category with low risk returns quiz for age <= 8', () => {
    expect(
      selectMissionType({ age: 8, interests: [], engagementScore: 0.8 }, 0.2, 'educational')
    ).toBe('quiz');
  });

  test('educational category with low risk returns real_world for age 9–14', () => {
    expect(
      selectMissionType({ age: 10, interests: [], engagementScore: 0.8 }, 0.2, 'educational')
    ).toBe('real_world');
  });

  test('educational category with low risk returns quiz for age > 14', () => {
    expect(
      selectMissionType({ age: 15, interests: [], engagementScore: 0.8 }, 0.2, 'educational')
    ).toBe('quiz');
  });

  test('educational category uses default age 12 when missing', () => {
    expect(
      selectMissionType({ interests: [], engagementScore: 0.8 }, 0.2, 'educational')
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
