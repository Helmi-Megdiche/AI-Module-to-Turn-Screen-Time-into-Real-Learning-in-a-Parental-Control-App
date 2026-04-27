import 'dart:io';

import 'package:android_capture/services/usage_db.dart';
import 'package:android_capture/services/usage_tracker.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeUsageDb extends UsageDb {
  _FakeUsageDb()
      : super(
          documentsDirProvider: () async => Directory.systemTemp,
        );

  final List<UsageEventRecord> inserted = <UsageEventRecord>[];

  @override
  Future<int> insertEvent(UsageEventRecord event) async {
    inserted.add(event);
    return inserted.length;
  }

  @override
  Future<void> close() async {}
}

void main() {
  test('tracker writes app session, unlock, and screen_on events', () async {
    final fakeDb = _FakeUsageDb();

    final tracker = UsageTracker(
      db: fakeDb,
      permissionChecker: () async => true,
      pollInterval: const Duration(minutes: 5),
      nowProvider: () => DateTime.fromMillisecondsSinceEpoch(20 * 60 * 1000),
      queryRawEvents: (_, __) async => <UsageRawEvent>[
        UsageRawEvent(
          eventType: UsageTracker.moveToForeground,
          packageName: 'com.example.app',
          timestampMs: 1000,
        ),
        UsageRawEvent(
          eventType: UsageTracker.moveToBackground,
          packageName: 'com.example.app',
          timestampMs: 5000,
        ),
        UsageRawEvent(
          eventType: UsageTracker.keyguardHidden,
          timestampMs: 6000,
        ),
        UsageRawEvent(
          eventType: UsageTracker.screenInteractive,
          timestampMs: 7000,
        ),
      ],
    );

    await tracker.poll();

    expect(fakeDb.inserted, hasLength(3));
    expect(fakeDb.inserted[0].eventType, 'app_session');
    expect(fakeDb.inserted[0].durationSec, 4);
    expect(fakeDb.inserted[1].eventType, 'unlock');
    expect(fakeDb.inserted[2].eventType, 'screen_on');
  });

  test('tracker does nothing when permission denied', () async {
    final fakeDb = _FakeUsageDb();
    var queried = false;

    final tracker = UsageTracker(
      db: fakeDb,
      permissionChecker: () async => false,
      queryRawEvents: (_, __) async {
        queried = true;
        return <UsageRawEvent>[];
      },
    );

    await tracker.poll();

    expect(queried, isFalse);
    expect(fakeDb.inserted, isEmpty);
  });
}
