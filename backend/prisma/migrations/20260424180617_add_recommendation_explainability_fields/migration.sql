-- AlterTable
ALTER TABLE "Recommendation" ADD COLUMN     "targetAudience" TEXT,
ADD COLUMN     "triggeringSubscore" TEXT,
ADD COLUMN     "triggeringValue" DOUBLE PRECISION;
