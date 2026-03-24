-- AlterTable
ALTER TABLE "User" ADD COLUMN     "engagementScore" DOUBLE PRECISION NOT NULL DEFAULT 0.5,
ADD COLUMN     "interests" JSONB DEFAULT '[]';
