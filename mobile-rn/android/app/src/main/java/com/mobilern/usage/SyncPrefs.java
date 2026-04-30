package com.mobilern.usage;

import android.content.Context;
import android.content.SharedPreferences;
import android.text.TextUtils;

/**
 * Single source for Phase 1 cursor + background worker prefs.
 * PREFS_NAME and KEY_LAST_SYNC_EPOCH_MS MUST stay aligned with Phase 1 UsageTrackingModule.
 */
public final class SyncPrefs {

    static final String PREFS_NAME = "usage_tracking_prefs";
    static final String KEY_LAST_SYNC_EPOCH_MS = "lastSyncEpochMs";

    private static final String KEY_API_BASE_URL = "api_base_url";
    private static final String KEY_BG_SYNC_ENABLED = "bg_sync_enabled";
    private static final String KEY_BG_INTERVAL_MINUTES = "bg_interval_minutes";
    private static final String KEY_BG_LAST_RUN_AT_MS = "bg_last_run_at_ms";
    private static final String KEY_BG_LAST_RESULT = "bg_last_result";
    private static final String KEY_BG_LAST_ERROR = "bg_last_error";
    private static final String KEY_SYNC_USER_ID = "sync_user_id";

    private SyncPrefs() {}

    static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    /** Reads saved cursor; -1 if unset (caller applies Phase 1 default window). */
    public static long getLastSyncEpochMs(Context ctx) {
        return prefs(ctx).getLong(KEY_LAST_SYNC_EPOCH_MS, -1L);
    }

    /**
     * Monotonic cursor advance — same rule as Phase 1 confirmSync.
     * Must be used by foreground bridge and background worker only after verified 2xx upload.
     */
    public static void advanceCursorMonotonic(Context ctx, long incomingCursorMs) {
        SharedPreferences p = prefs(ctx);
        long saved = p.getLong(KEY_LAST_SYNC_EPOCH_MS, -1L);
        long next = Math.max(saved, incomingCursorMs);
        p.edit().putLong(KEY_LAST_SYNC_EPOCH_MS, next).apply();
    }

    public static void setApiBaseUrl(Context ctx, String url) {
        if (url == null || url.trim().isEmpty()) {
            prefs(ctx).edit().remove(KEY_API_BASE_URL).apply();
            return;
        }
        String normalized = url.trim().replaceAll("/+$", "");
        prefs(ctx).edit().putString(KEY_API_BASE_URL, normalized).apply();
    }

    public static String getApiBaseUrl(Context ctx) {
        return prefs(ctx).getString(KEY_API_BASE_URL, "");
    }

    public static void setBgSchedule(Context ctx, boolean enabled, int intervalMinutes) {
        prefs(ctx).edit()
                .putBoolean(KEY_BG_SYNC_ENABLED, enabled)
                .putInt(KEY_BG_INTERVAL_MINUTES, Math.max(15, intervalMinutes))
                .apply();
    }

    public static boolean isBgSyncEnabled(Context ctx) {
        return prefs(ctx).getBoolean(KEY_BG_SYNC_ENABLED, false);
    }

    public static int getBgIntervalMinutes(Context ctx) {
        return prefs(ctx).getInt(KEY_BG_INTERVAL_MINUTES, 30);
    }

    public static void setSyncUserId(Context ctx, int userId) {
        if (userId > 0) {
            prefs(ctx).edit().putInt(KEY_SYNC_USER_ID, userId).apply();
        }
    }

    public static int getSyncUserId(Context ctx) {
        int id = prefs(ctx).getInt(KEY_SYNC_USER_ID, 1);
        return id > 0 ? id : 1;
    }

    public static void recordWorkerFinished(Context ctx, String result, String errorExcerpt) {
        SharedPreferences.Editor ed = prefs(ctx).edit()
                .putLong(KEY_BG_LAST_RUN_AT_MS, System.currentTimeMillis())
                .putString(KEY_BG_LAST_RESULT, result != null ? result : "pending");
        if (errorExcerpt == null) {
            ed.remove(KEY_BG_LAST_ERROR);
        } else {
            String truncated = TextUtils.isEmpty(errorExcerpt)
                    ? ""
                    : errorExcerpt.substring(0, Math.min(80, errorExcerpt.length()));
            ed.putString(KEY_BG_LAST_ERROR, truncated);
        }
        ed.apply();
    }

    public static long getBgLastRunAtMs(Context ctx) {
        return prefs(ctx).getLong(KEY_BG_LAST_RUN_AT_MS, 0L);
    }

    public static String getBgLastResult(Context ctx) {
        return prefs(ctx).getString(KEY_BG_LAST_RESULT, "pending");
    }

    public static String getBgLastError(Context ctx) {
        return prefs(ctx).getString(KEY_BG_LAST_ERROR, "");
    }
}
