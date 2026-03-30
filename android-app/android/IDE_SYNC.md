# Gradle / Java diagnostics in the IDE

If your editor reports **`Namespace not specified`** for:

`...\Pub\Cache\hosted\pub.dev\media_projection_creator-1.0.0\android\build.gradle`,

it is looking at the **pub.dev copy**, not the **vendored** plugin under `android-app/packages/media_projection_creator`. Flutter builds use `.flutter-plugins` after `flutter pub get`, which points `media_projection_creator` at the local package.

**What to do**

1. Open the **Flutter project root** `android-app/` (not only `android-app/android/`) in your IDE when working on Dart + plugins.
2. Run **`flutter pub get`** from `android-app/`.
3. In Android Studio: **File → Sync Project with Gradle Files** using the project opened via the Flutter tooling (or “Open Android module in Android Studio” from VS Code/Android Studio Flutter menu).

The repo already injects `namespace` for legacy plugins from `AndroidManifest.xml` in `android/build.gradle.kts`; the vendored `media_projection_creator` also declares `namespace` in its own `build.gradle`.
