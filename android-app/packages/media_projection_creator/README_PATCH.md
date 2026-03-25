# Vendored `media_projection_creator`

Upstream: [pub.dev/packages/media_projection_creator](https://pub.dev/packages/media_projection_creator) (MIT).

**Patch:** On Android 13+ (API 33), dynamically registered `BroadcastReceiver`s must specify `RECEIVER_EXPORTED` or `RECEIVER_NOT_EXPORTED`. Upstream called `registerReceiver(receiver, filter)` and crashes on Android 14/15 with `SecurityException`.

This fork uses `Context.RECEIVER_NOT_EXPORTED` when `SDK_INT >= TIRAMISU`.

**Second patch (Android 13–15):** Implicit `sendBroadcast(action)` is not delivered to non-exported receivers. `RequestMediaProjectionPermissionActivity` now sends **explicit** broadcasts via `intent.setPackage(getPackageName())` so `onReceive` runs after the user taps **Allow** (including “Entire screen” / “Single app”).

`MediaProjectionService` uses `getParcelableExtra("data", Intent.class)` on API 33+ when reading the nested result intent.
