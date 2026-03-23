-- AlterTable
ALTER TABLE "Mission" ADD COLUMN     "content" JSONB,
ADD COLUMN     "difficulty" INTEGER NOT NULL DEFAULT 1,
ADD COLUMN     "type" TEXT NOT NULL DEFAULT 'real_world';

-- CreateTable
CREATE TABLE "MissionResult" (
    "id" SERIAL NOT NULL,
    "missionId" INTEGER NOT NULL,
    "userId" INTEGER NOT NULL,
    "score" INTEGER,
    "success" BOOLEAN NOT NULL,
    "timeSpent" INTEGER,
    "bonusPoints" INTEGER NOT NULL DEFAULT 0,
    "earnedPoints" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "MissionResult_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "MissionResult" ADD CONSTRAINT "MissionResult_missionId_fkey" FOREIGN KEY ("missionId") REFERENCES "Mission"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "MissionResult" ADD CONSTRAINT "MissionResult_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
