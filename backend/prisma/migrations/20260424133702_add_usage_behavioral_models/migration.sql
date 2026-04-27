-- CreateTable
CREATE TABLE "UsageEvent" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "eventType" TEXT NOT NULL,
    "appPackage" TEXT,
    "startedAt" TIMESTAMP(3) NOT NULL,
    "endedAt" TIMESTAMP(3),
    "durationSec" INTEGER,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "UsageEvent_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "BehavioralScore" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "computedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "windowDays" INTEGER NOT NULL DEFAULT 7,
    "addictionScore" DOUBLE PRECISION NOT NULL,
    "wellbeingScore" DOUBLE PRECISION NOT NULL,
    "subscoresJson" JSONB NOT NULL,
    "recommendationsJson" JSONB,

    CONSTRAINT "BehavioralScore_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Recommendation" (
    "id" SERIAL NOT NULL,
    "userId" INTEGER NOT NULL,
    "scoreSnapshotId" INTEGER,
    "type" TEXT NOT NULL,
    "severity" TEXT NOT NULL,
    "messageFr" TEXT NOT NULL,
    "actionPayload" JSONB,
    "status" TEXT NOT NULL DEFAULT 'active',
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Recommendation_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "UsageEvent_userId_startedAt_idx" ON "UsageEvent"("userId", "startedAt");

-- CreateIndex
CREATE INDEX "UsageEvent_createdAt_idx" ON "UsageEvent"("createdAt");

-- CreateIndex
CREATE INDEX "BehavioralScore_userId_computedAt_idx" ON "BehavioralScore"("userId", "computedAt");

-- CreateIndex
CREATE INDEX "Recommendation_userId_status_idx" ON "Recommendation"("userId", "status");

-- AddForeignKey
ALTER TABLE "UsageEvent" ADD CONSTRAINT "UsageEvent_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "BehavioralScore" ADD CONSTRAINT "BehavioralScore_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Recommendation" ADD CONSTRAINT "Recommendation_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
