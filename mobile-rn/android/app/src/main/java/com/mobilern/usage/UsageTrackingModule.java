package com.mobilern.usage;

import android.app.AppOpsManager;
import android.app.usage.UsageStats;
import android.app.usage.UsageStatsManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Process;
import android.provider.Settings;
import android.text.TextUtils;

import androidx.annotation.NonNull;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;

import java.util.List;

public class UsageTrackingModule extends ReactContextBaseJavaModule {
    private static final String MODULE_NAME = "UsageTracking";
    private static final String PREFS_NAME = "usage_tracking_prefs";
    private static final String KEY_LAST_SYNC_EPOCH_MS = "lastSyncEpochMs";

    public UsageTrackingModule(ReactApplicationContext reactContext) {
        super(reactContext);
    }

    @NonNull
    @Override
    public String getName() {
        return MODULE_NAME;
    }

    @ReactMethod
    public void startTracking(Promise promise) {
        if (!hasUsageStatsPermission()) {
            promise.reject(
                    "USAGE_PERMISSION_NOT_GRANTED",
                    "Usage access is required. Enable Usage Access in Android settings."
            );
            return;
        }
        promise.resolve(true);
    }

    @ReactMethod
    public void stopTracking(Promise promise) {
        promise.resolve(true);
    }

    @ReactMethod
    public void getUsageEvents(Promise promise) {
        try {
            long now = System.currentTimeMillis();
            long savedCursor = getSharedPreferences().getLong(KEY_LAST_SYNC_EPOCH_MS, -1L);
            long lastSync = savedCursor > 0 ? savedCursor : now - 24L * 60L * 60L * 1000L;

            UsageStatsManager usageStatsManager =
                    (UsageStatsManager) getReactApplicationContext().getSystemService(Context.USAGE_STATS_SERVICE);
            List<UsageStats> stats = usageStatsManager == null
                    ? null
                    : usageStatsManager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, lastSync, now);

            WritableArray events = Arguments.createArray();
            String selfPackage = getReactApplicationContext().getPackageName();
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

                    WritableMap item = Arguments.createMap();
                    item.putString("event_type", "app_session");
                    item.putString("app_package", packageName);
                    /**
                     * started_at is approximated using lastTimeUsed; it is not a true session start.
                     * Future improvement: derive accurate sessions with UsageEvents API.
                     */
                    item.putDouble("started_at", (double) startedAt);
                    item.putDouble("ended_at", (double) endedAt);
                    item.putDouble("duration_sec", (double) durationSec);
                    events.pushMap(item);
                }
            }

            WritableMap result = Arguments.createMap();
            result.putArray("events", events);
            result.putString("nextCursor", String.valueOf(now));
            promise.resolve(result);
        } catch (Exception e) {
            promise.reject("USAGE_EVENTS_READ_FAILED", e.getMessage(), e);
        }
    }

    @ReactMethod
    public void confirmSync(String cursor, Promise promise) {
        if (cursor == null || cursor.trim().isEmpty()) {
            promise.reject("INVALID_CURSOR", "Cursor must be a non-empty epoch string.");
            return;
        }

        long incomingCursor;
        try {
            incomingCursor = Long.parseLong(cursor.trim());
        } catch (NumberFormatException e) {
            promise.reject("INVALID_CURSOR", "Cursor must be a valid epoch milliseconds string.");
            return;
        }

        if (incomingCursor <= 0) {
            promise.reject("INVALID_CURSOR", "Cursor must be greater than zero.");
            return;
        }

        SharedPreferences preferences = getSharedPreferences();
        long savedCursor = preferences.getLong(KEY_LAST_SYNC_EPOCH_MS, -1L);
        long nextSavedCursor = Math.max(savedCursor, incomingCursor);
        preferences.edit().putLong(KEY_LAST_SYNC_EPOCH_MS, nextSavedCursor).apply();
        promise.resolve(true);
    }

    @ReactMethod
    public void openUsageAccessSettings() {
        Intent intent = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getReactApplicationContext().startActivity(intent);
    }

    private SharedPreferences getSharedPreferences() {
        return getReactApplicationContext().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    private boolean hasUsageStatsPermission() {
        Context context = getReactApplicationContext();
        AppOpsManager appOps = (AppOpsManager) context.getSystemService(Context.APP_OPS_SERVICE);
        if (appOps == null) {
            return false;
        }

        int mode = appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                context.getPackageName()
        );
        if (mode == AppOpsManager.MODE_ALLOWED) {
            return true;
        }
        if (mode == AppOpsManager.MODE_DEFAULT) {
            return context.checkCallingOrSelfPermission("android.permission.PACKAGE_USAGE_STATS")
                    == PackageManager.PERMISSION_GRANTED;
        }
        return false;
    }
}
