import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

class UsageEventRecord {
  UsageEventRecord({
    this.id,
    required this.eventType,
    this.appPackage,
    required this.startedAtMs,
    this.endedAtMs,
    this.durationSec,
    this.synced = 0,
  });

  final int? id;
  final String eventType;
  final String? appPackage;
  final int startedAtMs;
  final int? endedAtMs;
  final int? durationSec;
  final int synced;

  Map<String, Object?> toDbMap() {
    return <String, Object?>{
      'id': id,
      'event_type': eventType,
      'app_package': appPackage,
      'started_at': startedAtMs,
      'ended_at': endedAtMs,
      'duration_sec': durationSec,
      'synced': synced,
    };
  }

  static UsageEventRecord fromDbMap(Map<String, Object?> map) {
    return UsageEventRecord(
      id: map['id'] as int?,
      eventType: map['event_type'] as String,
      appPackage: map['app_package'] as String?,
      startedAtMs: map['started_at'] as int,
      endedAtMs: map['ended_at'] as int?,
      durationSec: map['duration_sec'] as int?,
      synced: (map['synced'] as int?) ?? 0,
    );
  }

  Map<String, Object?> toUploadMap() {
    return <String, Object?>{
      'event_type': eventType,
      'app_package': appPackage,
      'started_at': startedAtMs,
      'ended_at': endedAtMs,
      'duration_sec': durationSec,
    };
  }
}

typedef OpenUsageDatabaseFn = Future<Database> Function(String dbPath);
typedef DocumentsDirProvider = Future<Directory> Function();

class UsageDb {
  UsageDb({
    OpenUsageDatabaseFn? openDatabaseFn,
    DocumentsDirProvider? documentsDirProvider,
  })  : _openDatabaseFn = openDatabaseFn ?? _defaultOpenDatabase,
        _documentsDirProvider =
            documentsDirProvider ?? getApplicationDocumentsDirectory;

  static const String dbFileName = 'usage_events.db';
  static const String tableName = 'usage_events';
  final OpenUsageDatabaseFn _openDatabaseFn;
  final DocumentsDirProvider _documentsDirProvider;
  Database? _db;

  static Future<Database> _defaultOpenDatabase(String dbPath) {
    return openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
CREATE TABLE usage_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  app_package TEXT,
  started_at INTEGER NOT NULL,
  ended_at INTEGER,
  duration_sec INTEGER,
  synced INTEGER NOT NULL DEFAULT 0
)
''');
      },
    );
  }

  Future<Database> _database() async {
    if (_db != null) {
      return _db!;
    }
    final docs = await _documentsDirProvider();
    final dbPath = p.join(docs.path, dbFileName);
    _db = await _openDatabaseFn(dbPath);
    return _db!;
  }

  Future<int> insertEvent(UsageEventRecord event) async {
    final db = await _database();
    return db.insert(tableName, event.toDbMap());
  }

  Future<List<UsageEventRecord>> fetchUnsyncedEvents({int limit = 500}) async {
    final db = await _database();
    final rows = await db.query(
      tableName,
      where: 'synced = 0',
      orderBy: 'started_at ASC',
      limit: limit,
    );
    return rows.map(UsageEventRecord.fromDbMap).toList();
  }

  Future<int> markSynced(List<int> ids) async {
    if (ids.isEmpty) {
      return 0;
    }
    final db = await _database();
    final placeholders = List.filled(ids.length, '?').join(', ');
    return db.rawUpdate(
      'UPDATE $tableName SET synced = 1 WHERE id IN ($placeholders)',
      ids,
    );
  }

  Future<int> deleteOlderThan(int thresholdEpochMs) async {
    final db = await _database();
    return db.delete(
      tableName,
      where: 'started_at < ?',
      whereArgs: <Object>[thresholdEpochMs],
    );
  }

  Future<void> close() async {
    if (_db != null) {
      await _db!.close();
      _db = null;
    }
  }
}
