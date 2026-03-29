/**
 * Mission payload generators with backward-compatible text + Flutter-friendly structure.
 */

function buildMissionContent({ title, instructions, data, game, reward, legacy }) {
  return {
    title,
    instructions,
    data,
    game: game ?? null,
    reward,
    ...legacy,
  };
}

function buildMission({ mission, points, type, game, difficulty, content, reward }) {
  return {
    mission,
    points,
    type,
    game: game ?? null,
    difficulty,
    reward,
    content,
  };
}

function buildQuizMission({ riskScore, matchedKeywords, difficulty }) {
  // Also triggered by educational content detection (CDC §4.3)
  const normalized = Array.isArray(matchedKeywords)
    ? matchedKeywords.filter((x) => typeof x === 'string').map((x) => x.toLowerCase())
    : [];
  const isRespectScenario = normalized.includes('hate speech') || normalized.includes('harassment');
  const question = isRespectScenario
    ? 'Which of these is a respectful way to express disagreement?'
    : 'What is the healthiest next step after seeing risky online content?';
  const choices = isRespectScenario
    ? ["You're stupid", 'I disagree with your opinion', 'Nobody likes what you say']
    : ['Keep scrolling angrily', 'Take a break and talk to a trusted adult', 'Share it with friends to laugh'];
  const correctAnswer = 1;
  const reward = { basePoints: 20, maxBonus: 5 };
  const title = 'Respect & Safety Quiz';
  const instructions = 'Pick the best answer, then submit your result.';
  return buildMission({
    mission: title,
    points: reward.basePoints,
    type: 'quiz',
    game: 'quiz',
    difficulty,
    reward,
    content: buildMissionContent({
      title,
      instructions,
      data: { question, choices, correctAnswer },
      game: 'quiz',
      reward,
      legacy: { question, choices, correctAnswer },
    }),
  });
}

function buildPuzzleMission({ difficulty }) {
  const grid = [
    [0, 0, 1, 2],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
  ];
  const reward = { basePoints: 15, maxBonus: 10 };
  const title = 'Focus Sudoku Challenge';
  const instructions = 'Fill the 4x4 grid and check your solution.';
  return buildMission({
    mission: title,
    points: reward.basePoints,
    type: 'puzzle',
    game: 'sudoku4x4',
    difficulty,
    reward,
    content: buildMissionContent({
      title,
      instructions,
      data: { game: 'sudoku4x4', grid },
      game: 'sudoku4x4',
      reward,
      legacy: { game: 'sudoku4x4', grid },
    }),
  });
}

function buildMiniGameMission({ difficulty }) {
  const reward = { basePoints: 18, maxBonus: 10 };
  const title = 'Tic-Tac-Toe Focus Break';
  const instructions = 'Play one short game, then submit your result.';
  return buildMission({
    mission: title,
    points: reward.basePoints,
    type: 'mini_game',
    game: 'tic_tac_toe',
    difficulty,
    reward,
    content: buildMissionContent({
      title,
      instructions,
      data: { game: 'tic_tac_toe' },
      game: 'tic_tac_toe',
      reward,
      legacy: { game: 'tic_tac_toe', targetHits: 12, maxSeconds: 45 },
    }),
  });
}

function buildRealWorldMission({ age, difficulty }) {
  // Also triggered by educational content detection (CDC §4.3)
  const mission =
    age < 10
      ? 'Do 10 jumping jacks and share one thing you learned today.'
      : 'Take a 5-minute offline break and write one useful takeaway from your activity.';
  const reward = { basePoints: 2, maxBonus: 0 };
  const title = 'Real-World Healthy Break';
  const instructions = 'Complete the activity offline and come back when done.';
  const description = 'Do 10 jumping jacks and think about what you learned today.';
  return buildMission({
    mission,
    points: reward.basePoints,
    type: 'real_world',
    game: null,
    difficulty,
    reward,
    content: buildMissionContent({
      title,
      instructions,
      data: { activity: description },
      game: null,
      reward,
      legacy: { description },
    }),
  });
}

/**
 * Build mission payload from personalized type selection.
 *
 * @param {{ missionType: string, riskScore: number, age: number, matchedKeywords?: string[], difficulty: number }} args
 * @returns {{ mission: string, points: number, type: string, game: string|null, difficulty: number, reward: {basePoints:number,maxBonus:number}, content: Record<string, unknown> }}
 */
function generateMissionPayload(args) {
  const missionType = String(args.missionType || '').toLowerCase();
  if (missionType === 'quiz') {
    return buildQuizMission(args);
  }
  if (missionType === 'mini_game') {
    return buildMiniGameMission(args);
  }
  if (missionType === 'puzzle') {
    return buildPuzzleMission(args);
  }
  return buildRealWorldMission(args);
}

module.exports = {
  generateMissionPayload,
};
