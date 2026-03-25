package im.zego.media_projection_creator.internal;
//
//  RequestMediaProjectionPermissionActivity.java
//  android
//  im.zego.media_projection_creator
//
//  Created by Patrick Fu on 2020/10/27.
//  Copyright © 2020 Zego. All rights reserved.
//

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.annotation.RequiresApi;

import im.zego.media_projection_creator.RequestMediaProjectionPermissionManager;

public class RequestMediaProjectionPermissionActivity extends Activity {

    private static final String TAG = "MediaProjectionPatch";
    private static final int RequestMediaProjectionPermissionCode = 1001;

    @Override
    protected void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.i(TAG, "PermissionActivity onCreate");

        IntentFilter filter = new IntentFilter();
        filter.addAction("com.media_projection_creator.request_permission_result_succeeded");
        filter.addAction("com.media_projection_creator.request_permission_result_failed_user_canceled");
        filter.addAction("com.media_projection_creator.request_permission_result_failed_system_version_too_low");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(
                    RequestMediaProjectionPermissionManager.getInstance(),
                    filter,
                    Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(RequestMediaProjectionPermissionManager.getInstance(), filter);
        }

        if (Build.VERSION.SDK_INT < 21) {
            Intent low = new Intent("com.media_projection_creator.request_permission_result_failed_system_version_too_low");
            low.setPackage(getPackageName());
            sendBroadcast(low);
            finish();
        } else {
            requestMediaProjectionPermission();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        Log.i(TAG, "PermissionActivity onDestroy");
        unregisterReceiver(RequestMediaProjectionPermissionManager.getInstance());
    }

    @RequiresApi(api = Build.VERSION_CODES.LOLLIPOP)
    private void requestMediaProjectionPermission() {
        MediaProjectionManager manager = (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
        startActivityForResult(manager.createScreenCaptureIntent(), RequestMediaProjectionPermissionCode);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == RequestMediaProjectionPermissionCode) {
            Log.i(TAG, "onActivityResult req=" + requestCode + " resultCode=" + resultCode + " dataNull=" + (data == null));

            if (resultCode == RESULT_OK && data != null) {
                // Explicit package: RECEIVER_NOT_EXPORTED receivers won't get implicit broadcasts (API 33+).
                Intent broadcast = new Intent("com.media_projection_creator.request_permission_result_succeeded");
                broadcast.setPackage(getPackageName());
                broadcast.putExtra("resultCode", resultCode);
                if (data.getExtras() != null) {
                    broadcast.putExtras(data);
                }
                Log.i(TAG, "sendBroadcast SUCCESS pkg=" + getPackageName() + " extras=" + (data.getExtras() != null));
                sendBroadcast(broadcast);
            } else {
                Intent intent = new Intent("com.media_projection_creator.request_permission_result_failed_user_canceled");
                intent.setPackage(getPackageName());
                intent.putExtra("resultCode", resultCode);
                Log.w(TAG, "sendBroadcast CANCELED or null data");
                sendBroadcast(intent);
            }

            finish();
        }
    }
}
