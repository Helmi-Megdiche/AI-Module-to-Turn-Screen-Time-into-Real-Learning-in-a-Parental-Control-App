package com.mobilern.usage;

import android.app.AppOpsManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Process;
import android.provider.Settings;
import android.text.TextUtils;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkInfo;
import androidx.work.WorkManager;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableArray;
import com.facebook.react.bridge.WritableMap;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

public class UsageTrackingModule extends ReactContextBaseJavaModule {

    private static final String MODULE_NAME = "UsageTracking";
    /** Logs when RN invokes background-scheduling APIs (distinct from RN_USAGE_BG worker tag). */
    private static final String LOG_TAG_BG_BRIDGE = "RN_USAGE_BG_JS";

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
            Context ctx = getReactApplicationContext();
            long now = System.currentTimeMillis();
            long savedCursor = SyncPrefs.getLastSyncEpochMs(ctx);

            UsageStatsCollector.CollectResult collected =
                    UsageStatsCollector.collect(ctx, savedCursor, now, Integer.MAX_VALUE);

            WritableArray events = jsonEventsToWritable(collected.events);

            WritableMap result = Arguments.createMap();
            result.putArray("events", events);
            result.putString("nextCursor", collected.nextCursor);
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

        SyncPrefs.advanceCursorMonotonic(getReactApplicationContext(), incomingCursor);
        promise.resolve(true);
    }

    @ReactMethod
    public void openUsageAccessSettings() {
        Intent intent = new Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getReactApplicationContext().startActivity(intent);
    }

    /**
     * Mirrors resolved API base URL from JS so WorkManager uploads hit the same host as foreground sync.
     */
    @ReactMethod
    public void setApiBaseUrl(String url, Promise promise) {
        try {
            SyncPrefs.setApiBaseUrl(getReactApplicationContext(), url);
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("SET_API_BASE_URL_FAILED", e.getMessage(), e);
        }
    }

    /**
     * Schedules periodic behavioral sync ({@link UsageSyncWorker#UNIQUE_WORK_NAME}).
     */
    @ReactMethod
    public void enqueuePeriodicSync(int intervalMinutes, Promise promise) {
        try {
            Context ctx = getReactApplicationContext();
            int safe = Math.max(15, intervalMinutes);

            PeriodicWorkRequest periodicWork =
                    new PeriodicWorkRequest.Builder(
                            UsageSyncWorker.class,
                            safe,
                            TimeUnit.MINUTES)
                            .setConstraints(UsageSyncWorker.syncConstraints())
                            .setBackoffCriteria(
                                    UsageSyncWorker.backoffPolicy(),
                                    UsageSyncWorker.backoffSeconds(),
                                    TimeUnit.SECONDS)
                            .build();

            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                    UsageSyncWorker.UNIQUE_WORK_NAME,
                    ExistingPeriodicWorkPolicy.REPLACE,
                    periodicWork);

            SyncPrefs.setBgSchedule(ctx, true, safe);

            Log.d(UsageSyncWorker.LOG_TAG, "enqueue interval=" + safe);

            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("ENQUEUE_PERIODIC_SYNC_FAILED", e.getMessage(), e);
        }
    }

    @ReactMethod
    public void cancelPeriodicSync(Promise promise) {
        try {
            Context ctx = getReactApplicationContext();
            WorkManager.getInstance(ctx).cancelUniqueWork(UsageSyncWorker.UNIQUE_WORK_NAME);
            SyncPrefs.setBgSchedule(ctx, false, SyncPrefs.getBgIntervalMinutes(ctx));

            Log.d(UsageSyncWorker.LOG_TAG, "cancelled tag=" + UsageSyncWorker.UNIQUE_WORK_NAME);

            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("CANCEL_PERIODIC_SYNC_FAILED", e.getMessage(), e);
        }
    }

    @ReactMethod
    public void triggerOneShotSyncNow(Promise promise) {
        try {
            Context ctx = getReactApplicationContext();
            OneTimeWorkRequest oneTime =
                    new OneTimeWorkRequest.Builder(UsageSyncWorker.class)
                            .setConstraints(UsageSyncWorker.syncConstraints())
                            .setBackoffCriteria(
                                    UsageSyncWorker.backoffPolicy(),
                                    UsageSyncWorker.backoffSeconds(),
                                    TimeUnit.SECONDS)
                            .build();

            WorkManager.getInstance(ctx).enqueue(oneTime);

            Log.d(UsageSyncWorker.LOG_TAG, "one_shot enqueued");

            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("ONE_SHOT_SYNC_FAILED", e.getMessage(), e);
        }
    }

    @ReactMethod
    public void getScheduledSyncStatus(Promise promise) {
        Context ctx = getReactApplicationContext();
        WritableMap map = Arguments.createMap();
        boolean prefsEnabled = SyncPrefs.isBgSyncEnabled(ctx);
        int interval = SyncPrefs.getBgIntervalMinutes(ctx);

        boolean wmScheduled = false;
        try {
            List<WorkInfo> infos = WorkManager.getInstance(ctx)
                    .getWorkInfosForUniqueWork(UsageSyncWorker.UNIQUE_WORK_NAME)
                    .get(5, TimeUnit.SECONDS);
            if (!infos.isEmpty()) {
                WorkInfo.State st = infos.get(0).getState();
                wmScheduled = st == WorkInfo.State.ENQUEUED
                        || st == WorkInfo.State.RUNNING
                        || st == WorkInfo.State.BLOCKED;
            }
        } catch (ExecutionException | InterruptedException | TimeoutException e) {
            Log.w(LOG_TAG_BG_BRIDGE, "getScheduledSyncStatus work query failed: " + e.getMessage());
        }

        map.putBoolean("enabled", prefsEnabled && wmScheduled);
        map.putInt("intervalMinutes", interval);
        map.putDouble("lastRunAtMs", (double) SyncPrefs.getBgLastRunAtMs(ctx));
        map.putString("lastResult", SyncPrefs.getBgLastResult(ctx));
        map.putString("lastError", SyncPrefs.getBgLastError(ctx));

        promise.resolve(map);
    }

    /**
     * Optional: persist default analytics user id for native POST bodies (foreground + worker).
     */
    @ReactMethod
    public void setSyncUserId(int userId, Promise promise) {
        try {
            SyncPrefs.setSyncUserId(getReactApplicationContext(), userId);
            promise.resolve(true);
        } catch (Exception e) {
            promise.reject("SET_SYNC_USER_ID_FAILED", e.getMessage(), e);
        }
    }

    private WritableArray jsonEventsToWritable(JSONArray arr) throws JSONException {
        WritableArray wa = Arguments.createArray();
        for (int i = 0; i < arr.length(); i++) {
            JSONObject o = arr.getJSONObject(i);
            WritableMap m = Arguments.createMap();
            m.putString("event_type", o.optString("event_type"));
            m.putString("app_package", o.optString("app_package"));
            m.putDouble("started_at", (double) o.optLong("started_at", 0L));
            m.putDouble("ended_at", (double) o.optLong("ended_at", 0L));
            m.putDouble("duration_sec", o.optDouble("duration_sec", 0d));
            wa.pushMap(m);
        }
        return wa;
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
