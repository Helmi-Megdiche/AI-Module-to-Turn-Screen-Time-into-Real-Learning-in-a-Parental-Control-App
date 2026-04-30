package com.mobilern.usage;

import android.app.usage.UsageStats;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.text.TextUtils;

import androidx.annotation.NonNull;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;

/**
 * Shared UsageStats extraction for foreground RN bridge and WorkManager worker.
 * Mirrors Phase 1 UsageTrackingModule mapping (same filters and event shape).
 */
public final class UsageStatsCollector {

    private UsageStatsCollector() {}

    public static final class CollectResult {
        public final JSONArray events;
        /** Epoch millis string, same semantics as Phase 1 nextCursor */
        public final String nextCursor;

        CollectResult(JSONArray events, String nextCursor) {
            this.events = events;
            this.nextCursor = nextCursor;
        }
    }

    @NonNull
    public static CollectResult collect(Context context, long lastSyncEpochMs, long nowEpochMs, int maxEvents)
            throws JSONException {
        long savedCursor = lastSyncEpochMs;
        long lastSync = savedCursor > 0 ? savedCursor : nowEpochMs - 24L * 60L * 60L * 1000L;

        UsageStatsManager usageStatsManager =
                (UsageStatsManager) context.getSystemService(Context.USAGE_STATS_SERVICE);
        List<UsageStats> stats = usageStatsManager == null
                ? null
                : usageStatsManager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, lastSync, nowEpochMs);

        JSONArray events = new JSONArray();
        String selfPackage = context.getPackageName();
        if (stats != null) {
            for (UsageStats usage : stats) {
                String packageName = usage.getPackageName();
                if (TextUtils.isEmpty(packageName)) {
                    continue;
                }
                if (packageName.equals(selfPackage)) {
                    continue;
                }
                if (packageName.startsWith("android.")
                        || packageName.startsWith("com.android.")
                        || packageName.startsWith("com.google.android.")) {
                    continue;
                }

                long totalForegroundMs = usage.getTotalTimeInForeground();
                if (totalForegroundMs <= 0) {
                    continue;
                }

                long startedAt = usage.getLastTimeUsed();
                int durationSec = (int) Math.floor(totalForegroundMs / 1000.0d);
                long endedAt = startedAt + (durationSec * 1000L);

                JSONObject item = new JSONObject();
                item.put("event_type", "app_session");
                item.put("app_package", packageName);
                item.put("started_at", startedAt);
                item.put("ended_at", endedAt);
                item.put("duration_sec", durationSec);
                events.put(item);

                if (events.length() >= maxEvents) {
                    break;
                }
            }
        }

        return new CollectResult(events, String.valueOf(nowEpochMs));
    }
}
