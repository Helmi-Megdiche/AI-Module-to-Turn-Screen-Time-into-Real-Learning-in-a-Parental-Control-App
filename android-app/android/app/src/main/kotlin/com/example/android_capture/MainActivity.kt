package com.example.android_capture

import android.os.Bundle
import im.zego.media_projection_creator.RequestMediaProjectionPermissionManager
import io.flutter.embedding.android.FlutterActivity

/**
 * Optional: customize MediaProjection foreground notification (Android Q+).
 * The media_projection_screenshot plugin registers the projection callback on the engine;
 * do not replace that callback here.
 */
class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        RequestMediaProjectionPermissionManager.getInstance()
            .setForegroundServiceNotificationStyle(
                R.mipmap.ic_launcher,
                "Screen capture active",
            )
    }
}
