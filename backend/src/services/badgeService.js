const prisma = require('../config/prisma');

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
