package com.example.android_capture

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import im.zego.media_projection_creator.RequestMediaProjectionPermissionManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * Optional: customize MediaProjection foreground notification (Android Q+).
 * The media_projection_screenshot plugin registers the projection callback on the engine;
 * do not replace that callback here.
 */
class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.example.android_capture/system",
        ).setMethodCallHandler { call, result ->
            if (call.method == "getDefaultLauncherPackage") {
                try {
                    val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                    val resolveInfo = packageManager.resolveActivity(intent, PackageManager.MATCH_DEFAULT_ONLY)
                    result.success(resolveInfo?.activityInfo?.packageName)
                } catch (e: Exception) {
                    result.error("launcher_lookup_failed", e.message, null)
                }
            } else {
                result.notImplemented()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        RequestMediaProjectionPermissionManager.getInstance()
            .setForegroundServiceNotificationStyle(
                R.mipmap.ic_launcher,
                "Screen capture active",
            )
    }
}
