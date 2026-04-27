-- AlterTable
ALTER TABLE "Mission" ADD COLUMN     "scoreSnapshotId" INTEGER,
ADD COLUMN     "targetAudience" TEXT,
ADD COLUMN     "triggeringSubscore" TEXT,
ADD COLUMN     "triggeringValue" DOUBLE PRECISION;
