package com.mobilern.usage;

import android.app.AppOpsManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Process;
import android.text.TextUtils;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.NetworkType;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * Background usage batch upload via WorkManager.
 * <p>
 * Not a covert or “spy” tracker: uploads only aggregates already exposed by
 * {@code UsageStatsManager} under {@code PACKAGE_USAGE_STATS} — the same data the parent
 * explicitly enabled in-app. No screenshots, no extra identifiers beyond usage fields.
 * Runs only when the device is on a network ({@link NetworkType#CONNECTED}) and battery is
 * not low; payloads go to the same parent-configured API base as foreground sync.
 */
public class UsageSyncWorker extends Worker {

    static final String UNIQUE_WORK_NAME = "behavioral-sync";
    static final String LOG_TAG = "RN_USAGE_BG";

    private static final MediaType JSON_MEDIA = MediaType.get("application/json; charset=utf-8");
    private static final int MAX_EVENTS_PER_RUN = 500;

    public UsageSyncWorker(@NonNull Context context, @NonNull WorkerParameters workerParams) {
        super(context, workerParams);
    }

    static Constraints syncConstraints() {
        return new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build();
    }

    static OkHttpClient httpClient() {
        return new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .writeTimeout(15, TimeUnit.SECONDS)
                .build();
    }

    @NonNull
    @Override
    public Result doWork() {
        Context ctx = getApplicationContext();
        int attempt = getRunAttemptCount();
        Log.d(LOG_TAG, "worker started attempt=" + attempt);

        String baseUrl = SyncPrefs.getApiBaseUrl(ctx);
        if (TextUtils.isEmpty(baseUrl)) {
            Log.d(LOG_TAG, "worker no_url_skip");
            SyncPrefs.recordWorkerFinished(ctx, "skipped_no_url", null);
            return Result.success();
        }

        if (!hasUsageStatsPermission(ctx)) {
            Log.e(LOG_TAG, "worker error permission message=no PACKAGE_USAGE_STATS");
            SyncPrefs.recordWorkerFinished(ctx, "failed", "usage_permission");
            return Result.failure();
        }

        long now = System.currentTimeMillis();
        long lastCursor = SyncPrefs.getLastSyncEpochMs(ctx);

        UsageStatsCollector.CollectResult collected;
        try {
            collected = UsageStatsCollector.collect(ctx, lastCursor, now, MAX_EVENTS_PER_RUN);
        } catch (Exception e) {
            String msg = e.getMessage() != null ? e.getMessage() : e.toString();
            Log.e(LOG_TAG, "worker error collect message=" + msg);
            SyncPrefs.recordWorkerFinished(ctx, "failed", msg);
            return Result.retry();
        }

        JSONArray events = collected.events;
        if (events.length() == 0) {
            Log.d(LOG_TAG, "worker no_events_skip");
            SyncPrefs.recordWorkerFinished(ctx, "skipped_no_events", null);
            return Result.success();
        }

        Log.d(LOG_TAG, "worker fetched events=" + events.length());

        JSONObject root = new JSONObject();
        try {
            // Must match backend ownershipGuard + validateUsageEventsPayload (camelCase userId).
            root.put("userId", SyncPrefs.getSyncUserId(ctx));
            root.put("events", events);
        } catch (Exception e) {
            String msg = e.getMessage() != null ? e.getMessage() : e.toString();
            Log.e(LOG_TAG, "worker error payload message=" + msg);
            SyncPrefs.recordWorkerFinished(ctx, "failed", msg);
            return Result.retry();
        }

        String payload = root.toString();
        String url = baseUrl + "/api/usage/events";
        Uri parsed = Uri.parse(url);
        String requestHost = parsed.getHost();
        Log.d(LOG_TAG, "worker request_url=" + (requestHost != null ? requestHost : url));

        Request request = new Request.Builder()
                .url(url)
                .post(RequestBody.create(JSON_MEDIA, payload))
                .build();

        OkHttpClient client = httpClient();
        try (Response response = client.newCall(request).execute()) {
            int code = response.code();
            String bodyStr = "";
            ResponseBody rb = response.body();
            if (rb != null) {
                bodyStr = rb.string();
            }

            if (code >= 200 && code < 300) {
                int inserted = -1;
                int rejected = -1;
                if (!TextUtils.isEmpty(bodyStr)) {
                    try {
                        JSONObject respJson = new JSONObject(bodyStr);
                        if (respJson.has("inserted")) {
                            inserted = respJson.optInt("inserted", -1);
                        }
                        if (respJson.has("rejected")) {
                            rejected = respJson.optInt("rejected", -1);
                        }
                    } catch (Exception ignored) {
                        // Non-JSON success body — still treat as confirmed upload window.
                    }
                }

                Log.d(LOG_TAG, "worker posted inserted=" + inserted + " rejected=" + rejected + " http_status=" + code);

                long incomingCursor = Long.parseLong(collected.nextCursor);
                SyncPrefs.advanceCursorMonotonic(ctx, incomingCursor);

                Log.d(LOG_TAG, "worker confirmed cursor=" + incomingCursor);

                SyncPrefs.recordWorkerFinished(ctx, "success", null);
                return Result.success();
            }

            Log.e(LOG_TAG, "worker error http http_status=" + code + " message=" + excerpt(bodyStr));
            SyncPrefs.recordWorkerFinished(ctx, "failed", "http_" + code);
            Log.d(LOG_TAG, "worker retry next_attempt=" + (attempt + 1));
            return Result.retry();
        } catch (IOException e) {
            String msg = e.getMessage() != null ? e.getMessage() : e.toString();
            Log.e(LOG_TAG, "worker error network message=" + excerpt(msg));
            SyncPrefs.recordWorkerFinished(ctx, "failed", msg);
            Log.d(LOG_TAG, "worker retry next_attempt=" + (attempt + 1));
            return Result.retry();
        }
    }

    private static String excerpt(String s) {
        if (s == null) {
            return "";
        }
        return s.substring(0, Math.min(80, s.length()));
    }

    private static boolean hasUsageStatsPermission(Context context) {
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

    /** Initial backoff for periodic work configuration (matches Phase 2.2 plan). */
    static long backoffSeconds() {
        return 30L;
    }

    static BackoffPolicy backoffPolicy() {
        return BackoffPolicy.EXPONENTIAL;
    }
}
