/**
 * Single Prisma client instance for the whole Node process.
 * In development, reuses the same client across hot-reloads to avoid connection exhaustion.
 */
const { PrismaClient } = require('@prisma/client');

const globalForPrisma = globalThis;

const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}

module.exports = prisma;
