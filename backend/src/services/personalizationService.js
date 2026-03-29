/**
 * Personalization helpers for mission-type routing and adaptive difficulty.
 */

const { RISKY_THRESHOLD } = require('../config');

/**
 * Normalize user interests into a lowercased unique array.
 *
 * @param {unknown} rawInterests
 * @returns {string[]}
 */
function normalizeInterests(rawInterests) {
  if (!Array.isArray(rawInterests)) return [];
  const normalized = rawInterests
    .filter((x) => typeof x === 'string')
    .map((x) => x.trim().toLowerCase())
    .filter(Boolean);
  return Array.from(new Set(normalized));
}

/**
 * Select mission type using risk, interests, engagement, and age.
 *
 * @param {{ interests?: unknown, engagementScore?: number, age?: number }} user
 * @param {number} riskScore
 * @param {string} category
 * @returns {'quiz'|'mini_game'|'puzzle'|'real_world'}
 */
function selectMissionType(user, riskScore, category) {
  if (category === 'educational' && riskScore < RISKY_THRESHOLD) {
    const age = user?.age ?? 12;
    if (age <= 8) return 'quiz';
    if (age <= 14) return 'real_world';
    return 'quiz';
  }

  const interests = normalizeInterests(user?.interests);
  const engagementScore = Number(user?.engagementScore ?? 0.5);
  const age = Number(user?.age ?? 0);

  // For dangerous content (risk > 0.7)
  if (riskScore > 0.7) {
    if (interests.includes('games')) return 'mini_game';
    if (engagementScore < 0.4) return 'mini_game';
    return 'quiz';
  }

  // For medium risk (0.3–0.7)
  if (riskScore > 0.3) {
    if (interests.includes('games')) return 'mini_game';
    if (interests.includes('reading')) return 'quiz';
    if (engagementScore < 0.4) return 'mini_game';
    if (Number.isFinite(age) && age < 10) return 'puzzle';
    return 'real_world';
  }

  // Safe content (<0.3)
  return 'real_world';
}

/**
 * Difficulty from engagement score, constrained to 1..3.
 *
 * @param {{ engagementScore?: number }} user
 * @returns {number}
 */
function computeDifficulty(user) {
  const engagementScore = Number(user?.engagementScore ?? 0.5);
  const safeScore = Number.isFinite(engagementScore) ? engagementScore : 0.5;
  return 1 + Math.min(2, Math.floor(safeScore * 2));
}

module.exports = {
  normalizeInterests,
  selectMissionType,
  computeDifficulty,
};
