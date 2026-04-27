import 'dart:io';

import 'package:android_capture/services/usage_db.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  late Directory tempDir;
  late UsageDb db;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('usage_db_test_');
    db = UsageDb(documentsDirProvider: () async => tempDir);
  });

  tearDown(() async {
    await db.close();
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('insert + query unsynced events', () async {
    await db.insertEvent(
      UsageEventRecord(
        eventType: 'app_session',
        appPackage: 'com.example.app',
        startedAtMs: 1000,
        endedAtMs: 2000,
        durationSec: 1,
      ),
    );
    await db.insertEvent(
      UsageEventRecord(
        eventType: 'unlock',
        appPackage: null,
        startedAtMs: 3000,
      ),
    );

    final unsynced = await db.fetchUnsyncedEvents();
    expect(unsynced, hasLength(2));
    expect(unsynced.first.eventType, 'app_session');
    expect(unsynced.last.eventType, 'unlock');
  });

  test('mark synced removes rows from unsynced query', () async {
    final id = await db.insertEvent(
      UsageEventRecord(
        eventType: 'screen_on',
        appPackage: null,
        startedAtMs: 1000,
      ),
    );

    final updated = await db.markSynced(<int>[id]);
    expect(updated, 1);

    final unsynced = await db.fetchUnsyncedEvents();
    expect(unsynced, isEmpty);
  });

  test('delete old rows keeps recent rows', () async {
    await db.insertEvent(
      UsageEventRecord(
        eventType: 'unlock',
        appPackage: null,
        startedAtMs: 1000,
      ),
    );
    await db.insertEvent(
      UsageEventRecord(
        eventType: 'unlock',
        appPackage: null,
        startedAtMs: 10 * 60 * 1000,
      ),
    );

    final deleted = await db.deleteOlderThan(5 * 60 * 1000);
    expect(deleted, 1);

    final unsynced = await db.fetchUnsyncedEvents();
    expect(unsynced, hasLength(1));
    expect(unsynced.single.startedAtMs, 10 * 60 * 1000);
  });
}
