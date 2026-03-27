# Android capture client (Flutter)

Flutter **Android** app (Dart package name `android_capture`, folder `android-app/`). It polls usage events for target packages, captures the screen with `media_projection_creator` + `media_projection_screenshot`, compresses a JPEG, and enqueues a **Workmanager** task that POSTs base64 JSON to your backend’s `POST /api/analyze`.

## Requirements

- Flutter SDK (project tested on **3.24.x**)
- Android SDK; **minSdk 26**; `ndkVersion` pinned to **27.0.12077973** in `android/app/build.gradle.kts` to satisfy plugin metadata
- Backend running and reachable (default UI base URL `http://10.0.2.2:3000` from emulator)

## Dependency notes

- **`media_projection_creator`**: vendored under [`packages/media_projection_creator`](packages/media_projection_creator) with an Android patch (`registerReceiver` + `RECEIVER_NOT_EXPORTED` on API 33+) so screen-capture permission works on **Android 14 / 15** (e.g. Honor). The app uses **`dependency_overrides`** in `pubspec.yaml` so `media_projection_screenshot` still resolves.
- **`media_projection_screenshot`**: vendored under [`packages/media_projection_screenshot`](packages/media_projection_screenshot) as **`0.0.6+patched2`** — **`0.0.6`** is missing **`registerCallback`** before **`createVirtualDisplay`** (Android 14+). **`patched2`** reuses one `VirtualDisplay` per consent session and exposes `resetSession()` to fully clear stale `MediaProjection`/`VirtualDisplay`/`ImageReader` state before recovery re-consent.
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
3. **Media projection** — `MediaProjectionScreenshot.requestPermission()` triggers the system capture consent dialog; a foreground notification may appear while projection is active. On **API 34+** with a high `targetSdk`, the manifest must also declare **`FOREGROUND_SERVICE_MEDIA_PROJECTION`** next to `FOREGROUND_SERVICE`; otherwise starting `MediaProjectionService` fails with **`SecurityException`** right after the user taps **Allow** (log may still show `resultCode=-1`, which is **`RESULT_OK`** on Android).
4. **Main UI** — the home screen uses a scrollable body and a **bounded** log panel so the soft keyboard does not trigger a bottom **`RenderFlex` overflow** (`adjustResize`).

Use **Start monitoring** after all are granted. **Refresh status & log** reloads the shared log file under the app documents directory (`event_log.txt`).

## Capture strategy (battery-aware)

- Monitoring polls usage every 5 seconds to detect current foreground package.
- App captures any foreground package except the current launcher package (home screen).
- Launcher package is detected dynamically at runtime via `device_apps`.
- Capture loop starts only when monitoring is active, projection is ready, and foreground app is capturable.
- Captures are serialized with an in-progress guard to prevent overlap when upload is slow.
- Capture loop pauses when app lifecycle is `paused`/`hidden`/`detached` and resumes on `resumed` when capture conditions still hold.
- Hourly capture budget is enforced (`120` captures/hour). Extra attempts are skipped and logged until the hour window resets.
- Upload stays in Workmanager isolate; worker persists latest `riskScore` to `capture_policy.json`.
- UI isolate reads `capture_policy.json` and adapts interval:
  - `riskScore > 0.8` -> 5s
  - `riskScore > 0.5` -> 10s
  - otherwise -> 20s
- If launcher/non-capturable foreground becomes active (or monitoring/projection stops), capture loop stops.
- On projection invalidation (`MediaProjection` / `VirtualDisplay` failures), app runs silent recovery retries with balanced backoff (1s, 2s, 4s). If retries fail, it requests projection consent again and resumes capture loop on success.
- Recovery path explicitly calls plugin `resetSession()` before re-consent so stale native objects from the previous projection session are not reused.

## Backend URL

| Environment   | Base URL example |
|---------------|------------------|
| Android emulator | `http://10.0.2.2:3000` |
| Physical phone + **USB** (adb reverse) | `http://127.0.0.1:3000` — see below |
| Physical device on **Wi‑Fi** (same LAN as PC) | `http://<your-PC-LAN-IP>:3000` |

### Phone plugged in over USB (Honor / any OEM)

1. Enable **Developer options** and **USB debugging** on the phone; accept the PC’s RSA fingerprint when prompted.
2. On the PC, confirm the device:  
   `"$env:LOCALAPPDATA\Android\sdk\platform-tools\adb.exe" devices`  
   You should see `device` (not `unauthorized`).
3. Forward the backend port so the phone can reach your laptop’s `localhost:3000`:  
   `"$env:LOCALAPPDATA\Android\sdk\platform-tools\adb.exe" reverse tcp:3000 tcp:3000`
4. Start the backend on the PC (`backend` listening on port **3000**).
5. In the app, set **Backend base URL** to **`http://127.0.0.1:3000`** (not `10.0.2.2`).

Re-run the `adb reverse` command after replugging USB if uploads stop reaching the server.

If **`127.0.0.1:3000` fails** from the phone, either run `adb reverse` again or switch the base URL to your PC’s **Wi‑Fi IPv4** (same network as the phone), e.g. `http://192.168.x.x:3000`, and ensure the backend listens on `0.0.0.0` (default for Node) and the PC firewall allows port 3000.

Cleartext HTTP is enabled for development in `AndroidManifest.xml` (`usesCleartextTraffic="true"`). Use HTTPS in production.

## Live debugging (USB)

After **`adb reverse tcp:3000 tcp:3000`** and installing a **debug** build:

1. **Flutter / Dart log** (attached run):

   ```bash
   cd android-app
   flutter run -d <deviceId>
   ```

   Look for `[ParentalMonitor]` in the terminal, especially:
   - `capture loop started interval=...`
   - `capture start` / `capture success`
   - `projection failure detected` + retry logs (`projection recovery retry ...`)
   - `projection recovered silently` or `projection recovered via re-consent`
   - `Upload HTTP 200`
   - `risk policy updated riskScore=...`

2. **Native MediaProjection log** (any install):

   ```bash
   adb logcat -c
   adb logcat -s MediaProjectionPatch flutter ParentalMonitor
   ```

   Reproduce: **Start monitoring** → system **Allow** dialog → watch for `onActivityResult`, `onReceive`, `MediaProjectionService`.

3. **In-app file log** — lines prefixed with **`[DEBUG]`** are appended to `event_log.txt`. Tap **Refresh status & log** after each attempt.

## Troubleshooting MediaProjection (Allow does nothing)

On **Android 13+**, after our first patch (`RECEIVER_NOT_EXPORTED`), the plugin must send **package-scoped** broadcasts so the in-process receiver actually runs. That is included in **`1.0.0+patched2`**. If an older APK still misbehaves, rebuild and reinstall (`flutter build apk --debug` + `adb install -r`).

## Legal disclaimer

This code is for **research / thesis demonstration**. Automated screen capture and upload may be restricted by law or platform policy; obtain appropriate consent before any real deployment.
