const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

const BADGES = [
  { name: 'Rising Star', description: 'Reach 100 total points.', type: 'POINT', requirementValue: '100' },
  { name: 'Explorer', description: 'Reach 500 total points.', type: 'POINT', requirementValue: '500' },
  { name: 'Guardian', description: 'Reach 2000 total points.', type: 'POINT', requirementValue: '2000' },
  { name: 'Champion', description: 'Reach 5000 total points.', type: 'POINT', requirementValue: '5000' },
  { name: 'Legend', description: 'Reach 10000 total points.', type: 'POINT', requirementValue: '10000' },
  { name: 'First Steps', description: 'Complete your first validated mission.', type: 'MISSION', requirementValue: '1' },
  { name: 'Helper', description: 'Complete 10 validated missions.', type: 'MISSION', requirementValue: '10' },
  { name: 'Hero', description: 'Complete 50 validated missions.', type: 'MISSION', requirementValue: '50' },
  { name: 'Super Hero', description: 'Complete 100 validated missions.', type: 'MISSION', requirementValue: '100' },
  { name: 'Guardian Angel', description: 'Complete 500 validated missions.', type: 'MISSION', requirementValue: '500' },
  { name: 'Little Explorer', description: 'Age badge for children 6-9.', type: 'AGE', requirementValue: '6-9' },
  { name: 'Young Adventurer', description: 'Age badge for children 10-12.', type: 'AGE', requirementValue: '10-12' },
  { name: 'Teen Champion', description: 'Age badge for teens 13-17.', type: 'AGE', requirementValue: '13-17' },
  { name: 'Master', description: 'Age badge for age 18+.', type: 'AGE', requirementValue: '18+' },
];

async function seedBadges() {
  for (const badge of BADGES) {
    await prisma.badge.upsert({
      where: { name: badge.name },
      update: {
        description: badge.description,
        type: badge.type,
        requirementValue: badge.requirementValue,
      },
      create: badge,
    });
  }
}

async function main() {
  await seedBadges();
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
