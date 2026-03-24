/**
 * Badge awarding utilities.
 *
 * This service centralizes threshold-based badge assignment for:
 * - point milestones,
 * - completed mission milestones,
 * - age-range badges.
 *
 * All award helpers are idempotent (via createMany + skipDuplicates).
 */
const prisma = require('../config/prisma');

// === Internal parsing/range helpers ===

function getClient(tx) {
  return tx ?? prisma;
}

function parseRequirementAsInt(value) {
  const n = Number.parseInt(String(value), 10);
  return Number.isFinite(n) ? n : null;
}

function inAgeRange(age, requirementValue) {
  const v = String(requirementValue || '').trim();
  if (!v) return false;

  if (v.endsWith('+')) {
    const min = Number.parseInt(v.slice(0, -1), 10);
    return Number.isFinite(min) && age >= min;
  }

  const [minRaw, maxRaw] = v.split('-');
  const min = Number.parseInt(minRaw, 10);
  const max = Number.parseInt(maxRaw, 10);
  return Number.isFinite(min) && Number.isFinite(max) && age >= min && age <= max;
}

// === Generic award engine ===

/**
 * Awards all badges of a given type that match the provided predicate.
 *
 * @param {number} userId User receiving badges.
 * @param {'POINT'|'MISSION'|'AGE'} type Badge type to evaluate.
 * @param {(badge: { id: number, name: string, requirementValue: string }) => boolean} predicate Selection rule.
 * @param {import('@prisma/client').Prisma.TransactionClient} [tx] Optional transaction client.
 * @returns {Promise<string[]>} Names of badges that matched the predicate.
 */
async function awardByType(userId, type, predicate, tx) {
  const db = getClient(tx);
  const badges = await db.badge.findMany({ where: { type } });
  const earnable = badges.filter(predicate);
  if (!earnable.length) return [];

  await db.userBadge.createMany({
    data: earnable.map((badge) => ({
      userId,
      badgeId: badge.id,
    })),
    skipDuplicates: true,
  });

  return earnable.map((badge) => badge.name);
}

// === Public badge award APIs ===

/**
 * Awards point badges crossed between two point totals.
 *
 * @param {number} userId User receiving badges.
 * @param {number} previousPoints Points before update.
 * @param {number} newPoints Points after update.
 * @param {import('@prisma/client').Prisma.TransactionClient} [tx] Optional transaction client.
 * @returns {Promise<string[]>} Names of newly satisfied point badges.
 */
async function awardPointBadges(userId, previousPoints, newPoints, tx) {
  const prev = Number(previousPoints ?? 0);
  const next = Number(newPoints ?? 0);
  if (!Number.isFinite(prev) || !Number.isFinite(next) || next <= prev) {
    return [];
  }

  return awardByType(
    userId,
    'POINT',
    (badge) => {
      const requirement = parseRequirementAsInt(badge.requirementValue);
      return requirement !== null && requirement > prev && requirement <= next;
    },
    tx
  );
}

/**
 * Awards mission badges crossed between two completed-mission totals.
 *
 * @param {number} userId User receiving badges.
 * @param {number} previousCount Completed missions before update.
 * @param {number} newCount Completed missions after update.
 * @param {import('@prisma/client').Prisma.TransactionClient} [tx] Optional transaction client.
 * @returns {Promise<string[]>} Names of newly satisfied mission badges.
 */
async function awardMissionBadges(userId, previousCount, newCount, tx) {
  const prev = Number(previousCount ?? 0);
  const next = Number(newCount ?? 0);
  if (!Number.isFinite(prev) || !Number.isFinite(next) || next <= prev) {
    return [];
  }

  return awardByType(
    userId,
    'MISSION',
    (badge) => {
      const requirement = parseRequirementAsInt(badge.requirementValue);
      return requirement !== null && requirement > prev && requirement <= next;
    },
    tx
  );
}

/**
 * Awards age badges that match the user's current age bracket.
 *
 * @param {number} userId User receiving badges.
 * @param {number} age User age.
 * @param {import('@prisma/client').Prisma.TransactionClient} [tx] Optional transaction client.
 * @returns {Promise<string[]>} Names of age badges matching the provided age.
 */
async function awardAgeBadges(userId, age, tx) {
  const numericAge = Number(age);
  if (!Number.isFinite(numericAge) || numericAge < 0) {
    return [];
  }

  return awardByType(
    userId,
    'AGE',
    (badge) => inAgeRange(numericAge, badge.requirementValue),
    tx
  );
}

module.exports = {
  awardPointBadges,
  awardMissionBadges,
  awardAgeBadges,
};
