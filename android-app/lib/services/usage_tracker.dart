import 'dart:async';

import 'package:usage_stats/usage_stats.dart';

import 'usage_db.dart';

typedef UsagePermissionChecker = Future<bool> Function();
typedef QueryRawEventsFn = Future<List<UsageRawEvent>> Function(
  DateTime start,
  DateTime end,
);
typedef NowProvider = DateTime Function();

class UsageRawEvent {
  UsageRawEvent({
    required this.eventType,
    required this.timestampMs,
    this.packageName,
  });

  final String eventType;
  final int timestampMs;
  final String? packageName;
}

class UsageTracker {
  UsageTracker({
    UsageDb? db,
    UsagePermissionChecker? permissionChecker,
    QueryRawEventsFn? queryRawEvents,
    NowProvider? nowProvider,
    Duration? pollInterval,
  })  : _db = db ?? UsageDb(),
        _permissionChecker = permissionChecker ?? _defaultPermissionChecker,
        _queryRawEvents = queryRawEvents ?? _defaultQueryRawEvents,
        _nowProvider = nowProvider ?? DateTime.now,
        _pollInterval = pollInterval ?? const Duration(minutes: 5);

  static const String moveToForeground = '1';
  static const String moveToBackground = '2';
  static const String keyguardHidden = '18';
  static const String screenInteractive = '15';

  static UsageTracker? _instance;

  final UsageDb _db;
  final UsagePermissionChecker _permissionChecker;
  final QueryRawEventsFn _queryRawEvents;
  final NowProvider _nowProvider;
  final Duration _pollInterval;

  Timer? _pollTimer;
  DateTime? _lastPollAt;
  final Map<String, int> _openSessionsByPackage = <String, int>{};

  static Future<bool> _defaultPermissionChecker() async {
    return await UsageStats.checkUsagePermission() == true;
  }

  static Future<List<UsageRawEvent>> _defaultQueryRawEvents(
    DateTime start,
    DateTime end,
  ) async {
    final raw = await UsageStats.queryEvents(start, end);
    return raw
        .map(
          (e) => UsageRawEvent(
            eventType: e.eventType ?? '',
            timestampMs: int.tryParse(e.timeStamp ?? '') ?? 0,
            packageName: e.packageName,
          ),
        )
        .where((e) => e.timestampMs > 0)
        .toList();
  }

  static void start() {
    _instance ??= UsageTracker();
    _instance!._startTimer();
  }

  void _startTimer() {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(_pollInterval, (_) {
      unawaited(poll());
    });
    unawaited(poll());
  }

  Future<void> stop() async {
    _pollTimer?.cancel();
    _pollTimer = null;
    await _db.close();
  }

  Future<void> poll() async {
    final allowed = await _permissionChecker();
    if (!allowed) {
      return;
    }

    final end = _nowProvider();
    final start = _lastPollAt ?? end.subtract(_pollInterval);
    _lastPollAt = end;

    final events = await _queryRawEvents(start, end);
    events.sort((a, b) => a.timestampMs.compareTo(b.timestampMs));

    for (final event in events) {
      await _handleEvent(event);
    }
  }

  Future<void> _handleEvent(UsageRawEvent event) async {
    if (event.eventType == moveToForeground) {
      final pkg = event.packageName;
      if (pkg == null || pkg.isEmpty) {
        return;
      }
      _openSessionsByPackage[pkg] = event.timestampMs;
      return;
    }

    if (event.eventType == moveToBackground) {
      final pkg = event.packageName;
      if (pkg == null || pkg.isEmpty) {
        return;
      }
      final startedAt = _openSessionsByPackage.remove(pkg);
      if (startedAt == null) {
        return;
      }
      final durationSec = ((event.timestampMs - startedAt) / 1000).round();
      await _db.insertEvent(
        UsageEventRecord(
          eventType: 'app_session',
          appPackage: pkg,
          startedAtMs: startedAt,
          endedAtMs: event.timestampMs,
          durationSec: durationSec < 0 ? 0 : durationSec,
        ),
      );
      return;
    }

    if (event.eventType == keyguardHidden) {
      await _db.insertEvent(
        UsageEventRecord(
          eventType: 'unlock',
          appPackage: null,
          startedAtMs: event.timestampMs,
          endedAtMs: null,
          durationSec: null,
        ),
      );
      return;
    }

    if (event.eventType == screenInteractive) {
      await _db.insertEvent(
        UsageEventRecord(
          eventType: 'screen_on',
          appPackage: null,
          startedAtMs: event.timestampMs,
          endedAtMs: null,
          durationSec: null,
        ),
      );
    }
  }
}
