# Android capture client (Flutter)

Flutter **Android** app (Dart package name `android_capture`, folder `android-app/`). It polls usage events for target packages, captures the screen with `media_projection_creator` + `media_projection_screenshot`, compresses a JPEG, and enqueues a **Workmanager** task that POSTs base64 JSON to your backend’s `POST /api/analyze`.

## Requirements

- Flutter SDK (project tested on **3.24.x**)
- Android SDK; **minSdk 26**; `ndkVersion` pinned to **27.0.12077973** in `android/app/build.gradle.kts` to satisfy plugin metadata
- Backend running and reachable (default UI base URL `http://10.0.2.2:3000` from emulator)

## Dependency notes

- **`media_projection_screenshot`**: pub.dev has no `1.0.x`; this repo uses **`^0.0.6`** (returns `CapturedImage` with PNG bytes for full-screen capture).
- **`workmanager`**: `0.5.x` does not compile with the current Android toolchain (legacy embedding references). **`^0.7.0`** works with Flutter 3.24; **`0.9.x`** requires a newer Flutter SDK (3.32+).
- **AGP 8 `namespace`**: older plugins omit it; `android/build.gradle.kts` sets `namespace` from each library’s manifest `package` when missing.

## Run

```bash
cd android-app
flutter pub get
flutter run
```

Build debug APK:

```bash
flutter build apk --debug
```

Output: `build/app/outputs/flutter-apk/app-debug.apk`.

## Permissions and flow

1. **Usage access** — `UsageStats.grantUsagePermission()` opens system settings; required for `queryEvents`.
2. **Notifications** — requested for Android 13+ (`POST_NOTIFICATIONS` in manifest).
3. **Media projection** — `MediaProjectionScreenshot.requestPermission()` triggers the system capture consent dialog; a foreground notification may appear while projection is active.

Use **Start monitoring** after all are granted. **Refresh status & log** reloads the shared log file under the app documents directory (`event_log.txt`).

## Backend URL

| Environment   | Base URL example |
|---------------|------------------|
| Android emulator | `http://10.0.2.2:3000` |
| Physical device on LAN | `http://<your-PC-LAN-IP>:3000` |

Cleartext HTTP is enabled for development in `AndroidManifest.xml` (`usesCleartextTraffic="true"`). Use HTTPS in production.

## Legal disclaimer

This code is for **research / thesis demonstration**. Automated screen capture and upload may be restricted by law or platform policy; obtain appropriate consent before any real deployment.
