package im.zego.media_projection_creator.internal;
//
//  MediaProjectionService.java
//  flutter_media_projection_creator
//  im.zego.media_projection_creator.internal
//
//  Created by Patrick Fu on 2020/12/30.
//  Copyright © 2020 Zego. All rights reserved.
//

import android.annotation.TargetApi;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import im.zego.media_projection_creator.RequestMediaProjectionPermissionManager;

@TargetApi(Build.VERSION_CODES.LOLLIPOP)
public class MediaProjectionService extends Service {

    private static final String TAG = "MediaProjectionPatch";

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.i(TAG, "MediaProjectionService onStartCommand");

        int resultCode = intent.getIntExtra("code", -1);
        Intent resultData = getMediaProjectionResultIntent(intent);
        Log.i(TAG, "resultCode=" + resultCode + " resultDataNull=" + (resultData == null));

        String notificationText = intent.getStringExtra("notificationText");
        int notificationIcon = intent.getIntExtra("notificationIcon", -1);
        createNotificationChannel(notificationText, notificationIcon);

        if (resultData == null) {
            Log.e(TAG, "resultData null — cannot getMediaProjection");
            RequestMediaProjectionPermissionManager.getInstance().onMediaProjectionCreated(null, RequestMediaProjectionPermissionManager.ERROR_CODE_FAILED_USER_CANCELED);
            return START_NOT_STICKY;
        }

        MediaProjectionManager manager = (MediaProjectionManager)getSystemService(Context.MEDIA_PROJECTION_SERVICE);
        MediaProjection mediaProjection = manager.getMediaProjection(resultCode, resultData);
        Log.i(TAG, "getMediaProjection null=" + (mediaProjection == null));
        RequestMediaProjectionPermissionManager.getInstance().onMediaProjectionCreated(mediaProjection, RequestMediaProjectionPermissionManager.ERROR_CODE_SUCCEED);

        return super.onStartCommand(intent, flags, startId);
    }

    private void createNotificationChannel(String notificationText, int notificationIcon) {
        Notification.Builder builder = new Notification.Builder(this.getApplicationContext()); //获取一个Notification构造器

        if (!notificationText.equals("")) {
            // Set the notification text
            builder.setContentText(notificationText);
        }

        if (notificationIcon != 0) {
            // Set the notification icon
            builder.setSmallIcon(notificationIcon);
        }

        builder.setWhen(System.currentTimeMillis());

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder.setChannelId("MediaProjectionCreatorChannel");
            NotificationManager notificationManager = (NotificationManager)getSystemService(NOTIFICATION_SERVICE);
            NotificationChannel channel = new NotificationChannel("MediaProjectionCreatorChannel", "MediaProjectionCreatorChannelName", NotificationManager.IMPORTANCE_LOW);
            channel.setLockscreenVisibility(Notification.VISIBILITY_PRIVATE);
            notificationManager.createNotificationChannel(channel);
        }

        Notification notification = builder.build();
        notification.defaults = Notification.DEFAULT_SOUND;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION);
        } else {
            startForeground(1, notification);
        }

    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        stopForeground(true);
    }

    private static Intent getMediaProjectionResultIntent(Intent serviceIntent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return serviceIntent.getParcelableExtra("data", Intent.class);
        }
        return serviceIntent.getParcelableExtra("data");
    }
}
