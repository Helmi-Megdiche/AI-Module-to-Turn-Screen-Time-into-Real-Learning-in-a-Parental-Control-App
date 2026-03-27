import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:io';
import 'dart:ui';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:media_projection_creator/media_projection_creator.dart';
import 'package:media_projection_screenshot/captured_image.dart';
import 'package:media_projection_screenshot/media_projection_screenshot.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:usage_stats/usage_stats.dart';
import 'package:workmanager/workmanager.dart';

/// Android [UsageEvents.Event.MOVE_TO_FOREGROUND](https://developer.android.com/reference/android/app/usage/UsageEvents.Event#MOVE_TO_FOREGROUND).
const String _kMoveToForeground = '1';

const List<String> kTargetApps = [
  'com.google.android.youtube',
  'com.instagram.android',
  'com.facebook.katana',
];

const String kLogFileName = 'event_log.txt';
const String kUploadTaskName = 'uploadAnalyzeTask';
const String kCapturePolicyFileName = 'capture_policy.json';

/// Terminal: `flutter run` → stdout / Run tab. APK only: `adb logcat -s flutter MediaProjectionPatch`.
void _trace(String message, {Object? error, StackTrace? stackTrace}) {
  final line = '[ParentalMonitor] $message';
  debugPrint(line);
  developer.log(
    message,
    name: 'ParentalMonitor',
    error: error,
    stackTrace: stackTrace,
  );
}

Future<void> _traceToFile(String message, {Object? error, StackTrace? stackTrace}) async {
  _trace(message, error: error, stackTrace: stackTrace);
  try {
    final err = error != null ? ' | err=$error' : '';
    await appendEventLog('[DEBUG] $message$err');
  } catch (_) {}
}

Future<File> _logFile() async {
  final dir = await getApplicationDocumentsDirectory();
  return File('${dir.path}/$kLogFileName');
}

Future<File> _capturePolicyFile() async {
  final dir = await getApplicationDocumentsDirectory();
  return File('${dir.path}/$kCapturePolicyFileName');
}

Future<void> appendEventLog(String message) async {
  final f = await _logFile();
  final ts = DateTime.now().toIso8601String();
  await f.writeAsString('$ts $message\n', mode: FileMode.append, flush: true);
}

double? _parseRiskScoreFromResponse(Map<String, dynamic>? data) {
  if (data == null) {
    return null;
  }

  dynamic v = data['riskScore'];
  if (v == null) {
    final analysis = data['analysis'];
    if (analysis is Map) {
      v = analysis['riskScore'] ?? analysis['risk'];
    }
  }

  if (v is num) {
    return v.toDouble().clamp(0.0, 1.0);
  }
  if (v is String) {
    final parsed = double.tryParse(v);
    if (parsed != null) {
      return parsed.clamp(0.0, 1.0);
    }
  }
  return null;
}

Future<void> _persistRiskScore(double riskScore) async {
  final policy = await _capturePolicyFile();
  final payload = <String, dynamic>{
    'riskScore': riskScore,
    'updatedAt': DateTime.now().toIso8601String(),
  };
  await policy.writeAsString(jsonEncode(payload), flush: true);
}

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    WidgetsFlutterBinding.ensureInitialized();
    DartPluginRegistrant.ensureInitialized();

    await _traceToFile('Workmanager task=$task keys=${inputData?.keys.toList()}');

    if (task != kUploadTaskName || inputData == null) {
      await _traceToFile('Workmanager skip: wrong task or null data');
      return Future.value(true);
    }

    final filePath = inputData['filePath'] as String?;
    final baseUrl = (inputData['baseUrl'] as String?)?.replaceAll(RegExp(r'/+$'), '');
    final userId = inputData['userId'];
    final age = inputData['age'];

    if (filePath == null || baseUrl == null || userId == null || age == null) {
      await _traceToFile('Upload error: missing inputData');
      return Future.value(true);
    }

    await _traceToFile('upload started');
    await _traceToFile('Upload POST $baseUrl/api/analyze file=$filePath');

    final file = File(filePath);
    if (!await file.exists()) {
      await _traceToFile('Upload error: file missing ($filePath)');
      return Future.value(true);
    }

    try {
      final bytes = await file.readAsBytes();
      final imageB64 = base64Encode(bytes);
      final dio = Dio(
        BaseOptions(
          connectTimeout: const Duration(seconds: 60),
          receiveTimeout: const Duration(seconds: 120),
          sendTimeout: const Duration(seconds: 120),
          contentType: Headers.jsonContentType,
        ),
      );

      final response = await dio.post<Map<String, dynamic>>(
        '$baseUrl/api/analyze',
        data: <String, dynamic>{
          'userId': userId is int ? userId : int.parse(userId.toString()),
          'age': age is int ? age : int.parse(age.toString()),
          'image': imageB64,
        },
      );

      final data = response.data;
      await _traceToFile('Upload HTTP ${response.statusCode}');
      await _traceToFile('upload success');

      final riskScore = _parseRiskScoreFromResponse(data);
      if (riskScore != null) {
        try {
          await _persistRiskScore(riskScore);
          await _traceToFile('risk policy updated riskScore=$riskScore');
        } catch (e, st) {
          await _traceToFile(
            'risk policy write failed: $e',
            error: e,
            stackTrace: st,
          );
        }
      } else {
        await _traceToFile('risk policy skipped: no risk score in response');
      }

      if (data != null && data['success'] == true) {
        final mission = data['mission'];
        String missionText = '';
        if (mission is Map) {
          missionText = (mission['text'] ?? mission['mission'] ?? '').toString();
        }
        final analysis = data['analysis'];
        String riskBit = '';
        if (analysis is Map && analysis['risk'] != null) {
          riskBit = ' risk: ${analysis['risk']}';
        } else if (analysis != null) {
          riskBit = ' analysis: ${analysis.toString()}';
          if (riskBit.length > 120) {
            riskBit = '${riskBit.substring(0, 120)}...';
          }
        }
        await appendEventLog('Uploaded: mission: $missionText$riskBit');
        await file.delete();
      } else {
        await appendEventLog('Upload error: bad response $data');
      }
    } on DioException catch (e) {
      final msg = e.response?.data?.toString() ?? e.message;
      await _traceToFile('DioException: $msg', error: e);
      return Future.value(false);
    } catch (e, st) {
      await _traceToFile('Upload exception: $e', error: e, stackTrace: st);
      return Future.value(false);
    }

    return Future.value(true);
  });
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  _trace('main(): kDebugMode=$kDebugMode initializing Workmanager');
  await Workmanager().initialize(
    callbackDispatcher,
    isInDebugMode: kDebugMode,
  );
  _trace('main(): runApp');
  runApp(const ParentalMonitorApp());
}

class ParentalMonitorApp extends StatelessWidget {
  const ParentalMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Screen monitor (demo)',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const MonitorHomePage(),
    );
  }
}

class MonitorHomePage extends StatefulWidget {
  const MonitorHomePage({super.key});

  @override
  State<MonitorHomePage> createState() => _MonitorHomePageState();
}

class _MonitorHomePageState extends State<MonitorHomePage> with WidgetsBindingObserver {
  final TextEditingController _userIdController = TextEditingController(text: '1');
  final TextEditingController _ageController = TextEditingController(text: '10');
  final TextEditingController _baseUrlController = TextEditingController(text: 'http://10.0.2.2:3000');
  final MediaProjectionScreenshot _screenshot = MediaProjectionScreenshot();

  Timer? _pollTimer;
  Timer? _captureTimer;
  String? _lastForegroundPackage;
  String? _activeTargetPackage;
  bool _monitoring = false;
  bool _projectionReady = false;
  bool _captureLoopRunning = false;
  bool _captureInProgress = false;
  bool _projectionRecoveryInProgress = false;
  int _projectionRetryCount = 0;
  static const int _maxProjectionRetries = 3;
  DateTime? _lastPolicyReadAt;
  Duration _captureInterval = const Duration(seconds: 15);
  String _logText = '';
  String _status = 'Grant permissions, then start monitoring.';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _refreshLogFromDisk();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _pollTimer?.cancel();
    _stopCaptureLoop(reason: 'dispose');
    _userIdController.dispose();
    _ageController.dispose();
    _baseUrlController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    unawaited(_traceToFile('lifecycle=$state MediaProjection.isGranted=${MediaProjectionScreenshot.isGranted}'));
    if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      _stopCaptureLoop(reason: 'app_background');
    }
    if (state == AppLifecycleState.resumed) {
      if (_projectionReady && _activeTargetPackage != null) {
        _startCaptureLoopIfNeeded();
      }
      unawaited(_refreshPermissionMessage());
    }
  }

  Future<void> _refreshLogFromDisk() async {
    try {
      final f = await _logFile();
      if (await f.exists()) {
        final t = await f.readAsString();
        if (mounted) {
          setState(() => _logText = t.isEmpty ? '(empty log)' : t);
        }
      } else if (mounted) {
        setState(() => _logText = '(no log file yet)');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _logText = 'Could not read log: $e');
      }
    }
  }

  Future<void> _refreshPermissionMessage() async {
    if (!Platform.isAndroid) {
      setState(() => _status = 'This demo targets Android only.');
      return;
    }
    final usage = await UsageStats.checkUsagePermission() == true;
    final notif = await Permission.notification.isGranted;
    var projection = false;
    try {
      projection = MediaProjectionScreenshot.isGranted;
    } catch (_) {
      projection = false;
    }
    _trace('refreshPermission: usage=$usage notif=$notif projection=$projection');

    final parts = <String>[
      if (usage) 'Usage stats OK' else 'Usage stats needed (Settings)',
      if (notif) 'Notifications OK' else 'Notifications: grant on Android 13+',
      if (projection) 'Screen capture OK' else 'Screen capture not granted yet',
    ];
    if (mounted) {
      setState(() => _status = parts.join(' · '));
    }
  }

  Duration _captureIntervalForRisk(double riskScore) {
    if (riskScore > 0.8) {
      return const Duration(seconds: 5);
    }
    if (riskScore > 0.5) {
      return const Duration(seconds: 10);
    }
    return const Duration(seconds: 20);
  }

  Future<void> _loadLatestRiskPolicy() async {
    try {
      final policyFile = await _capturePolicyFile();
      if (!await policyFile.exists()) {
        return;
      }
      final raw = await policyFile.readAsString();
      final dynamic decoded = jsonDecode(raw);
      if (decoded is! Map) {
        return;
      }

      final rawTs = decoded['updatedAt']?.toString();
      if (rawTs == null) {
        return;
      }
      final ts = DateTime.tryParse(rawTs);
      if (ts == null) {
        return;
      }
      if (_lastPolicyReadAt != null && !ts.isAfter(_lastPolicyReadAt!)) {
        return;
      }
      _lastPolicyReadAt = ts;

      final rawRisk = decoded['riskScore'];
      final riskScore = rawRisk is num
          ? rawRisk.toDouble()
          : double.tryParse(rawRisk?.toString() ?? '');
      if (riskScore == null) {
        return;
      }
      _updateCaptureIntervalFromRisk(riskScore.clamp(0.0, 1.0));
    } catch (e, st) {
      await _traceToFile(
        'risk policy read failed: $e',
        error: e,
        stackTrace: st,
      );
    }
  }

  void _updateCaptureIntervalFromRisk(double riskScore) {
    final newInterval = _captureIntervalForRisk(riskScore);
    if (newInterval == _captureInterval) {
      return;
    }
    _captureInterval = newInterval;
    unawaited(
      _traceToFile(
        'capture interval updated riskScore=$riskScore interval=${_captureInterval.inSeconds}s',
      ),
    );
    _restartCaptureLoop();
  }

  void _startCaptureLoopIfNeeded() {
    if (_captureLoopRunning || !_monitoring) {
      return;
    }
    if (_activeTargetPackage == null) {
      return;
    }
    if (!_projectionReady) {
      unawaited(_traceToFile('capture loop not started: projection not ready'));
      return;
    }

    _captureLoopRunning = true;
    unawaited(
      _traceToFile(
        'capture loop started interval=${_captureInterval.inSeconds}s pkg=$_activeTargetPackage',
      ),
    );
    _captureTimer = Timer.periodic(_captureInterval, (_) {
      unawaited(_safeCapture());
    });
    unawaited(_safeCapture());
  }

  void _stopCaptureLoop({String reason = 'manual'}) {
    if (_captureTimer == null && !_captureLoopRunning) {
      return;
    }
    _captureTimer?.cancel();
    _captureTimer = null;
    _captureLoopRunning = false;
    unawaited(_traceToFile('capture loop stopped reason=$reason'));
  }

  void _restartCaptureLoop() {
    _stopCaptureLoop(reason: 'interval_update');
    _startCaptureLoopIfNeeded();
  }

  Future<void> _safeCapture() async {
    if (!_monitoring) {
      return;
    }
    if (_activeTargetPackage == null) {
      await _traceToFile('capture skipped reason=no_target_foreground');
      return;
    }
    if (!_projectionReady) {
      await _traceToFile('capture skipped reason=projection_not_ready');
      return;
    }
    var granted = false;
    try {
      granted = MediaProjectionScreenshot.isGranted;
    } catch (_) {
      granted = false;
    }
    if (!granted) {
      _projectionReady = false;
      await _traceToFile('capture skipped reason=projection_not_granted');
      _stopCaptureLoop(reason: 'projection_lost');
      return;
    }
    if (_captureInProgress) {
      await _traceToFile('capture skipped reason=in_progress');
      return;
    }

    _captureInProgress = true;
    try {
      await _traceToFile('capture start pkg=$_activeTargetPackage');
      final ok = await _captureCompressSchedule();
      if (ok) {
        _projectionRetryCount = 0;
        await _traceToFile('capture success');
      }
      await _loadLatestRiskPolicy();
    } on PlatformException catch (e, st) {
      await _traceToFile('capture platform error: ${e.message ?? e.code}', error: e, stackTrace: st);
      if (_isProjectionInvalidError(e)) {
        await _handleProjectionFailure(e.message ?? e.code);
      }
    } catch (e, st) {
      await _traceToFile('capture error: $e', error: e, stackTrace: st);
    } finally {
      _captureInProgress = false;
    }
  }

  bool _isProjectionInvalidError(Object error) {
    final msg = error.toString().toLowerCase();
    return msg.contains('mediaprojection') ||
        msg.contains('virtualdisplay') ||
        msg.contains('non-current') ||
        msg.contains('token') ||
        msg.contains('must register a callback');
  }

  Future<bool> _requestMediaProjectionAgain() async {
    try {
      await _traceToFile('projection re-consent requested');
      await MediaProjectionCreator.destroyMediaProjection();
      await Future<void>.delayed(const Duration(milliseconds: 300));
      final code = await _screenshot.requestPermission();
      await _traceToFile('projection re-consent result code=$code');
      return code == MediaProjectionCreator.ERROR_CODE_SUCCEED;
    } catch (e, st) {
      await _traceToFile('projection re-consent exception: $e', error: e, stackTrace: st);
      return false;
    }
  }

  Future<void> _handleProjectionFailure(String reason) async {
    if (_projectionRecoveryInProgress) {
      await _traceToFile('projection recovery already in progress');
      return;
    }
    _projectionRecoveryInProgress = true;
    _projectionReady = false;
    _stopCaptureLoop(reason: 'projection_failure');
    await _traceToFile('projection failure detected: $reason');

    try {
      final backoff = <Duration>[
        const Duration(seconds: 1),
        const Duration(seconds: 2),
        const Duration(seconds: 4),
      ];

      for (var i = 0; i < backoff.length; i++) {
        if (!_monitoring || _activeTargetPackage == null) {
          await _traceToFile('projection recovery aborted: monitoring or target inactive');
          return;
        }
        _projectionRetryCount = i + 1;
        await _traceToFile(
          'projection recovery retry $_projectionRetryCount/$_maxProjectionRetries wait=${backoff[i].inSeconds}s',
        );
        await Future<void>.delayed(backoff[i]);
        try {
          final ok = await _captureCompressSchedule();
          if (ok) {
            _projectionReady = true;
            _projectionRetryCount = 0;
            await _traceToFile('projection recovered silently');
            _startCaptureLoopIfNeeded();
            return;
          }
        } on PlatformException catch (e, st) {
          await _traceToFile(
            'projection retry failed: ${e.message ?? e.code}',
            error: e,
            stackTrace: st,
          );
        }
      }

      await _traceToFile('projection silent retries exhausted; requesting re-consent');
      final consentOk = await _requestMediaProjectionAgain();
      if (consentOk) {
        _projectionReady = true;
        _projectionRetryCount = 0;
        await _traceToFile('projection recovered via re-consent');
        await _refreshPermissionMessage();
        _startCaptureLoopIfNeeded();
        return;
      }

      _projectionReady = false;
      if (mounted) {
        setState(() {
          _status = 'Screen capture permission expired. Tap Start monitoring to re-grant.';
        });
      }
      await _traceToFile('projection recovery failed after retries + re-consent');
    } finally {
      _projectionRecoveryInProgress = false;
    }
  }

  Future<bool> _ensurePermissionsForStart() async {
    if (!Platform.isAndroid) {
      _snack('Android only.');
      return false;
    }

    await _traceToFile('_ensurePermissionsForStart: begin baseUrl=${_baseUrlController.text.trim()}');

    final usageOk = await UsageStats.checkUsagePermission() == true;
    if (!usageOk) {
      await _traceToFile('usage not granted → opening Settings');
      await UsageStats.grantUsagePermission();
      await appendEventLog('Open Settings and allow usage access, then tap Start again.');
      _snack('Allow usage access in Settings, return, then Start again.');
      await _refreshPermissionMessage();
      return false;
    }

    final notifStatus = await Permission.notification.request();
    await _traceToFile('notification request → $notifStatus');
    if (!notifStatus.isGranted && !notifStatus.isProvisional) {
      _snack('Notification permission helps show capture status; you can continue if denied.');
    }

    await _traceToFile('calling MediaProjectionScreenshot.requestPermission() (watch logcat tag MediaProjectionPatch)');
    final code = await _screenshot.requestPermission();
    await _traceToFile('requestPermission() returned code=$code (0=OK 1=cancel 2=api low)');
    if (code != MediaProjectionCreator.ERROR_CODE_SUCCEED) {
      final msg = code == MediaProjectionCreator.ERROR_CODE_FAILED_USER_CANCELED
          ? 'Screen capture cancelled.'
          : 'Screen capture failed (code $code).';
      _snack(msg);
      await appendEventLog(msg);
      await _refreshPermissionMessage();
      return false;
    }

    await _traceToFile('projection OK isGranted=${MediaProjectionScreenshot.isGranted}');
    _projectionReady = true;
    _projectionRetryCount = 0;
    await _refreshPermissionMessage();
    return true;
  }

  void _snack(String message) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _startMonitoring() async {
    final ok = await _ensurePermissionsForStart();
    if (!ok) {
      return;
    }

    setState(() => _monitoring = true);
    await appendEventLog('Monitoring started.');
    await _refreshLogFromDisk();

    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 5), (_) => _pollUsage());
    await _pollUsage();
    _startCaptureLoopIfNeeded();
  }

  void _stopMonitoring() {
    _pollTimer?.cancel();
    _pollTimer = null;
    _stopCaptureLoop(reason: 'monitoring_stopped');
    _projectionReady = false;
    _projectionRetryCount = 0;
    _projectionRecoveryInProgress = false;
    setState(() {
      _monitoring = false;
      _lastForegroundPackage = null;
      _activeTargetPackage = null;
    });
    unawaited(appendEventLog('Monitoring stopped.'));
    unawaited(_refreshLogFromDisk());
    unawaited(MediaProjectionCreator.destroyMediaProjection());
  }

  Future<void> _pollUsage() async {
    if (!_monitoring || !mounted) {
      return;
    }

    final allowed = await UsageStats.checkUsagePermission();
    if (allowed != true) {
      return;
    }

    final end = DateTime.now();
    final start = end.subtract(const Duration(seconds: 10));

    List<EventUsageInfo> events;
    try {
      events = await UsageStats.queryEvents(start, end);
    } catch (e) {
      await appendEventLog('queryEvents error: $e');
      return;
    }

    EventUsageInfo? latest;
    var latestTs = -1;
    for (final e in events) {
      if (e.eventType != _kMoveToForeground) {
        continue;
      }
      final pkg = e.packageName;
      if (pkg == null || pkg.isEmpty) {
        continue;
      }
      final ts = int.tryParse(e.timeStamp ?? '') ?? 0;
      if (ts >= latestTs) {
        latestTs = ts;
        latest = e;
      }
    }

    if (latest == null) {
      return;
    }
    final pkg = latest.packageName!;
    final changed = pkg != _lastForegroundPackage;
    _lastForegroundPackage = pkg;
    final isTarget = kTargetApps.contains(pkg);

    if (changed) {
      await _traceToFile('foreground package=$pkg target=$isTarget');
      if (isTarget) {
        await appendEventLog('Target app foreground: $pkg');
      }
      await _refreshLogFromDisk();
    }

    if (!isTarget) {
      _activeTargetPackage = null;
      _stopCaptureLoop(reason: 'non_target_foreground');
      return;
    }

    _activeTargetPackage = pkg;
    _startCaptureLoopIfNeeded();
  }

  Future<bool> _captureCompressSchedule() async {
    if (!mounted) {
      return false;
    }

    await _traceToFile('takeCapture() start isGranted=${MediaProjectionScreenshot.isGranted}');
    CapturedImage? captured;
    try {
      captured = await _screenshot.takeCapture();
    } on PlatformException catch (e) {
      await _traceToFile('takeCapture threw: $e', error: e);
      await appendEventLog('takeCapture error: $e');
      await _refreshLogFromDisk();
      rethrow;
    } catch (e, st) {
      await _traceToFile('takeCapture exception: $e', error: e, stackTrace: st);
      await appendEventLog('takeCapture error: $e');
      await _refreshLogFromDisk();
      return false;
    }

    if (captured == null) {
      await _traceToFile('takeCapture returned null');
      await appendEventLog('takeCapture returned null (permission or capture failure).');
      await _refreshLogFromDisk();
      return false;
    }

    await appendEventLog('Screenshot captured (${captured.bytes.length} bytes PNG).');
    await _refreshLogFromDisk();

    final tmp = await getTemporaryDirectory();
    final stamp = DateTime.now().millisecondsSinceEpoch;
    final rawPath = '${tmp.path}/cap_$stamp.png';
    final rawFile = File(rawPath);
    await rawFile.writeAsBytes(captured.bytes, flush: true);

    final outPath = '${tmp.path}/cap_${stamp}_c.jpg';
    final compressed = await FlutterImageCompress.compressAndGetFile(
      rawFile.absolute.path,
      outPath,
      quality: 80,
      minWidth: 720,
    );

    try {
      await rawFile.delete();
    } catch (_) {}

    if (compressed == null) {
      await appendEventLog('Compression failed.');
      await _refreshLogFromDisk();
      return false;
    }

    final outLen = await compressed.length();
    await appendEventLog('Compressed: ${compressed.path} ($outLen bytes).');
    await _refreshLogFromDisk();

    final userId = int.tryParse(_userIdController.text.trim()) ?? 0;
    final age = int.tryParse(_ageController.text.trim()) ?? 0;
    if (userId <= 0) {
      await appendEventLog('Invalid userId; set a positive integer.');
      await _refreshLogFromDisk();
      return false;
    }
    if (age < 0) {
      await appendEventLog('Invalid age.');
      await _refreshLogFromDisk();
      return false;
    }

    final base = _baseUrlController.text.trim();
    final unique = 'upload_${DateTime.now().millisecondsSinceEpoch}';

    await Workmanager().registerOneOffTask(
      unique,
      kUploadTaskName,
      inputData: <String, dynamic>{
        'filePath': compressed.path,
        'userId': userId,
        'age': age,
        'baseUrl': base,
      },
    );

    await appendEventLog('Upload scheduled: $unique');
    await _refreshLogFromDisk();
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final logHeight = (MediaQuery.sizeOf(context).height * 0.28).clamp(160.0, 360.0);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Parental control demo'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _userIdController,
                decoration: const InputDecoration(labelText: 'User ID (positive int)'),
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _ageController,
                decoration: const InputDecoration(labelText: 'Age (non‑negative int)'),
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _baseUrlController,
                decoration: const InputDecoration(
                  labelText: 'Backend base URL',
                  hintText: 'http://10.0.2.2:3000',
                ),
                keyboardType: TextInputType.url,
              ),
              const SizedBox(height: 8),
              Text(_status, style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      onPressed: _monitoring ? null : () => _startMonitoring(),
                      child: const Text('Start monitoring'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _monitoring ? _stopMonitoring : null,
                      child: const Text('Stop monitoring'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: () async {
                  await _refreshPermissionMessage();
                  await _refreshLogFromDisk();
                },
                child: const Text('Refresh status & log'),
              ),
              const SizedBox(height: 16),
              Text('Event log ($kLogFileName)', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              SizedBox(
                height: logHeight,
                child: Container(
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  padding: const EdgeInsets.all(8),
                  child: SingleChildScrollView(
                    child: SelectableText(_logText, style: const TextStyle(fontFamily: 'monospace', fontSize: 12)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
