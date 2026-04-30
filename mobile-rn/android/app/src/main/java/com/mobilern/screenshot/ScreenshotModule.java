package com.mobilern.screenshot;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.WindowManager;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;

import com.facebook.react.bridge.ActivityEventListener;
import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.LifecycleEventListener;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.modules.core.DeviceEventManagerModule;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;
import java.util.concurrent.atomic.AtomicReference;

public class ScreenshotModule extends ReactContextBaseJavaModule implements ActivityEventListener, LifecycleEventListener {
    private static final String MODULE_NAME = "ScreenshotModule";
    private static final String LOG_TAG = "RN_SCREENSHOT";
    private static final int REQ_MEDIA_PROJECTION = 24023;
    private static final int MAX_CAPTURE_RETRIES = 3;
    private static final int RETRY_DELAY_MS = 200;
    private static final int MAX_SERVICE_START_POLLS = 10;
    private static final int SERVICE_POLL_DELAY_MS = 100;

    private final ReactApplicationContext reactContext;
    private Promise consentPromise;
    private MediaProjectionManager projectionManager;
    private MediaProjection mediaProjection;
    private Intent consentData;
    private int consentResultCode = Activity.RESULT_CANCELED;
    private boolean captureEnabled = false;
    private boolean appInForeground = true; // Locked G5 behavior: pause when app is backgrounded.
    private long lastCaptureAt = 0L;
    private String lastError = "";
    private boolean callbackRegistered = false;
    private ImageReader sharedReader;
    private VirtualDisplay sharedVirtualDisplay;
    private final AtomicReference<Image> latestImage = new AtomicReference<>();
    private int captureWidth;
    private int captureHeight;

    public ScreenshotModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
        reactContext.addActivityEventListener(this);
        reactContext.addLifecycleEventListener(this);
    }

    @NonNull
    @Override
    public String getName() {
        return MODULE_NAME;
    }

    @ReactMethod
    public void requestProjectionConsent(Promise promise) {
        try {
            if (consentData != null) {
                WritableMap ok = Arguments.createMap();
                ok.putBoolean("granted", true);
                ok.putString("reason", "already_granted");
                Log.d(LOG_TAG, "consent_granted already=true");
                promise.resolve(ok);
                return;
            }
            Activity activity = getCurrentActivity();
            if (activity == null) {
                promise.reject("NO_ACTIVITY", "Current activity is null.");
                return;
            }
            if (projectionManager == null) {
                projectionManager = (MediaProjectionManager) reactContext.getSystemService(Context.MEDIA_PROJECTION_SERVICE);
            }
            if (projectionManager == null) {
                promise.reject("NO_MEDIA_PROJECTION_MANAGER", "MediaProjectionManager not available.");
                return;
            }
            if (consentPromise != null) {
                promise.reject("CONSENT_IN_PROGRESS", "Projection consent flow is already in progress.");
                return;
            }
            consentPromise = promise;
            activity.startActivityForResult(projectionManager.createScreenCaptureIntent(), REQ_MEDIA_PROJECTION);
            Log.d(LOG_TAG, "consent_requested");
        } catch (Exception e) {
            lastError = e.getMessage() == null ? "consent_failed" : e.getMessage();
            promise.reject("CONSENT_REQUEST_FAILED", lastError, e);
        }
    }

    @ReactMethod
    public void startCapture(Promise promise) {
        try {
            if (consentData == null) {
                promise.reject("CONSENT_REQUIRED", "Projection consent is required first.");
                return;
            }
            captureEnabled = true;
            startForegroundService();
            waitForForegroundServiceAndCreateProjection(1, promise);
        } catch (Exception e) {
            lastError = e.getMessage() == null ? "start_capture_failed" : e.getMessage();
            promise.reject("START_CAPTURE_FAILED", lastError, e);
        }
    }

    @ReactMethod
    public void stopCapture(Promise promise) {
        captureEnabled = false;
        releaseProjection();
        stopForegroundService();
        Log.d(LOG_TAG, "capture_stopped");
        promise.resolve(true);
    }

    @ReactMethod
    public void captureFrame(Promise promise) {
        if (!captureEnabled) {
            promise.reject("CAPTURE_NOT_ENABLED", "Capture is disabled. Call startCapture() first.");
            return;
        }
        if (!appInForeground) {
            promise.reject("CAPTURE_PAUSED_BACKGROUND", "Capture is paused while app is in background.");
            return;
        }
        if (consentData == null) {
            promise.reject("CONSENT_REQUIRED", "Projection consent is missing.");
            return;
        }
        runCaptureAttempt(1, promise);
    }

    @ReactMethod
    public void getStatus(Promise promise) {
        WritableMap map = Arguments.createMap();
        map.putBoolean("enabled", captureEnabled);
        map.putBoolean("consentGranted", consentData != null);
        map.putBoolean("capturing", captureEnabled && mediaProjection != null);
        map.putString("lastError", lastError == null ? "" : lastError);
        map.putDouble("lastCaptureAt", (double) lastCaptureAt);
        map.putBoolean("pausedInBackground", !appInForeground);
        map.putInt("maxCaptureRetries", MAX_CAPTURE_RETRIES);
        map.putInt("retryDelayMs", RETRY_DELAY_MS);
        promise.resolve(map);
    }

    private void runCaptureAttempt(int attempt, Promise promise) {
        try {
            if (mediaProjection == null || sharedReader == null || sharedVirtualDisplay == null) {
                throw new IllegalStateException("Capture session is not started. Call startCapture() first.");
            }
            Image image = latestImage.getAndSet(null);
            if (image == null) {
                if (attempt < MAX_CAPTURE_RETRIES) {
                    Log.w(LOG_TAG, "frame_retry attempt=" + attempt + " reason=no_frame_yet");
                    new Handler(Looper.getMainLooper()).postDelayed(
                            () -> runCaptureAttempt(attempt + 1, promise),
                            RETRY_DELAY_MS
                    );
                    return;
                }
                lastError = "No frame available after retries";
                Log.e(LOG_TAG, "frame_failed attempts=" + attempt + " error=" + lastError);
                promise.reject("CAPTURE_FRAME_FAILED", lastError);
                return;
            }

            Bitmap bitmap = toBitmap(image, captureWidth, captureHeight);
            image.close();

            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream);
            byte[] bytes = outputStream.toByteArray();
            bitmap.recycle();
            String b64 = Base64.encodeToString(bytes, Base64.NO_WRAP);

            WritableMap result = Arguments.createMap();
            result.putString("bytesBase64", b64);
            result.putInt("width", captureWidth);
            result.putInt("height", captureHeight);
            result.putString("format", "png");
            result.putDouble("byteSize", (double) bytes.length);

            lastCaptureAt = System.currentTimeMillis();
            lastError = "";
            Log.d(LOG_TAG, "frame_captured bytes=" + bytes.length + " attempt=" + attempt);
            promise.resolve(result);
        } catch (Exception e) {
            if (attempt < MAX_CAPTURE_RETRIES) {
                Log.w(LOG_TAG, "frame_retry attempt=" + attempt + " reason=" + e.getMessage());
                new Handler(Looper.getMainLooper()).postDelayed(
                        () -> runCaptureAttempt(attempt + 1, promise),
                        RETRY_DELAY_MS
                );
            } else {
                lastError = e.getMessage() == null ? "capture_frame_failed" : e.getMessage();
                Log.e(LOG_TAG, "frame_failed attempts=" + attempt + " error=" + lastError);
                promise.reject("CAPTURE_FRAME_FAILED", lastError, e);
            }
        }
    }

    private void ensureProjection() {
        if (mediaProjection != null) {
            return;
        }
        if (projectionManager == null) {
            projectionManager = (MediaProjectionManager) reactContext.getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        }
        if (projectionManager == null || consentData == null) {
            throw new IllegalStateException("Projection manager or consent data missing.");
        }
        mediaProjection = projectionManager.getMediaProjection(consentResultCode, consentData);
        if (mediaProjection == null) {
            throw new IllegalStateException("Failed to create MediaProjection from consent data.");
        }
        if (!callbackRegistered) {
            mediaProjection.registerCallback(new MediaProjection.Callback() {
                @Override
                public void onStop() {
                    super.onStop();
                    Log.w(LOG_TAG, "projection_stopped_by_system");
                    consentData = null;
                    consentResultCode = Activity.RESULT_CANCELED;
                    captureEnabled = false;
                    releaseProjection();
                    stopForegroundService();
                    emitProjectionStoppedEvent();
                }
            }, new Handler(Looper.getMainLooper()));
            callbackRegistered = true;
        }
    }

    private void waitForForegroundServiceAndCreateProjection(int poll, Promise promise) {
        if (ScreenshotCaptureService.isRunning()) {
            try {
                ensureProjection();
                startCaptureSession();
                Log.d(LOG_TAG, "capture_started");
                promise.resolve(true);
            } catch (SecurityException se) {
                lastError = se.getMessage() == null ? "projection_security_exception" : se.getMessage();
                promise.reject("START_CAPTURE_SECURITY_FAILED", lastError, se);
            } catch (Exception e) {
                lastError = e.getMessage() == null ? "projection_create_failed" : e.getMessage();
                promise.reject("START_CAPTURE_FAILED", lastError, e);
            }
            return;
        }
        if (poll >= MAX_SERVICE_START_POLLS) {
            lastError = "Foreground service did not start in time.";
            promise.reject("FGS_START_TIMEOUT", lastError);
            return;
        }
        new Handler(Looper.getMainLooper()).postDelayed(
                () -> waitForForegroundServiceAndCreateProjection(poll + 1, promise),
                SERVICE_POLL_DELAY_MS
        );
    }

    private void startCaptureSession() {
        if (sharedReader != null && sharedVirtualDisplay != null) {
            return;
        }
        DisplayMetrics metrics = getDisplayMetrics();
        captureWidth = metrics.widthPixels;
        captureHeight = metrics.heightPixels;
        int densityDpi = metrics.densityDpi;

        sharedReader = ImageReader.newInstance(captureWidth, captureHeight, PixelFormat.RGBA_8888, 4);
        sharedReader.setOnImageAvailableListener(reader -> {
            try {
                Image incoming = reader.acquireLatestImage();
                if (incoming == null) {
                    return;
                }
                Image old = latestImage.getAndSet(incoming);
                if (old != null) {
                    old.close();
                }
            } catch (Exception ignore) {
            }
        }, new Handler(Looper.getMainLooper()));

        sharedVirtualDisplay = mediaProjection.createVirtualDisplay(
                "rn-screenshot-session",
                captureWidth,
                captureHeight,
                densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                sharedReader.getSurface(),
                null,
                null
        );
        Log.d(LOG_TAG, "capture_session_started w=" + captureWidth + " h=" + captureHeight);
    }

    private DisplayMetrics getDisplayMetrics() {
        WindowManager wm = (WindowManager) reactContext.getSystemService(Context.WINDOW_SERVICE);
        DisplayMetrics metrics = new DisplayMetrics();
        if (wm != null && wm.getDefaultDisplay() != null) {
            wm.getDefaultDisplay().getRealMetrics(metrics);
        }
        if (metrics.widthPixels <= 0 || metrics.heightPixels <= 0) {
            metrics = reactContext.getResources().getDisplayMetrics();
        }
        return metrics;
    }

    private Bitmap toBitmap(Image image, int width, int height) {
        Image.Plane[] planes = image.getPlanes();
        ByteBuffer buffer = planes[0].getBuffer();
        int pixelStride = planes[0].getPixelStride();
        int rowStride = planes[0].getRowStride();
        int rowPadding = rowStride - pixelStride * width;
        int bitmapWidth = width + rowPadding / pixelStride;
        Bitmap full = Bitmap.createBitmap(bitmapWidth, height, Bitmap.Config.ARGB_8888);
        full.copyPixelsFromBuffer(buffer);
        Bitmap cropped = Bitmap.createBitmap(full, 0, 0, width, height);
        full.recycle();
        return cropped;
    }

    private void startForegroundService() {
        Intent i = new Intent(reactContext, ScreenshotCaptureService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ContextCompat.startForegroundService(reactContext, i);
        } else {
            reactContext.startService(i);
        }
    }

    private void stopForegroundService() {
        try {
            reactContext.stopService(new Intent(reactContext, ScreenshotCaptureService.class));
        } catch (Exception ignore) {
        }
    }

    private void releaseProjection() {
        callbackRegistered = false;
        releaseCaptureSession();
        MediaProjection projection = mediaProjection;
        mediaProjection = null;
        try {
            if (projection != null) {
                projection.stop();
            }
        } catch (Exception ignore) {
        }
    }

    private void releaseCaptureSession() {
        try {
            Image old = latestImage.getAndSet(null);
            if (old != null) {
                old.close();
            }
        } catch (Exception ignore) {
        }
        try {
            if (sharedVirtualDisplay != null) {
                sharedVirtualDisplay.release();
            }
        } catch (Exception ignore) {
        }
        try {
            if (sharedReader != null) {
                sharedReader.close();
            }
        } catch (Exception ignore) {
        }
        sharedVirtualDisplay = null;
        sharedReader = null;
        captureWidth = 0;
        captureHeight = 0;
    }

    private void emitProjectionStoppedEvent() {
        if (reactContext.hasActiveCatalystInstance()) {
            reactContext
                    .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class)
                    .emit("RN_SCREENSHOT_PROJECTION_STOPPED", null);
        }
    }

    @Override
    public void onHostResume() {
        appInForeground = true;
    }

    @Override
    public void onHostPause() {
        appInForeground = false;
    }

    @Override
    public void onHostDestroy() {
        appInForeground = false;
    }

    @Override
    public void onActivityResult(Activity activity, int requestCode, int resultCode, Intent data) {
        if (requestCode != REQ_MEDIA_PROJECTION) {
            return;
        }
        if (consentPromise == null) {
            return;
        }
        Promise pending = consentPromise;
        consentPromise = null;

        WritableMap result = Arguments.createMap();
        boolean granted = resultCode == Activity.RESULT_OK && data != null;
        result.putBoolean("granted", granted);
        if (granted) {
            consentResultCode = resultCode;
            consentData = data;
            result.putString("reason", "granted");
            Log.d(LOG_TAG, "consent_granted");
        } else {
            consentResultCode = Activity.RESULT_CANCELED;
            consentData = null;
            result.putString("reason", "user_canceled_or_empty_data");
            Log.w(LOG_TAG, "consent_denied");
        }
        pending.resolve(result);
    }

    @Override
    public void onNewIntent(Intent intent) {
        // no-op
    }
}
