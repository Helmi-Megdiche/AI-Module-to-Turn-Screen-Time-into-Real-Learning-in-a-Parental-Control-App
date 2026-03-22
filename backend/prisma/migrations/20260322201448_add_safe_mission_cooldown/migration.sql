-- AlterTable
ALTER TABLE "User" ADD COLUMN     "lastSafeMissionAt" TIMESTAMP(3),
ADD COLUMN     "lastSafeResetDate" TIMESTAMP(3),
ADD COLUMN     "safePointsToday" INTEGER NOT NULL DEFAULT 0;
