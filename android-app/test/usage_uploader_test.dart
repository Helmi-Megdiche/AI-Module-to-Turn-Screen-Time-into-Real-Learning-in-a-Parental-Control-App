import 'dart:io';

import 'package:android_capture/services/usage_db.dart';
import 'package:android_capture/services/usage_uploader.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeUsageDb extends UsageDb {
  _FakeUsageDb(this.pending)
      : super(
          documentsDirProvider: () async => Directory.systemTemp,
        );

  final List<UsageEventRecord> pending;
  int? deletedOlderThanMs;
  List<int> markedIds = <int>[];

  @override
  Future<int> deleteOlderThan(int thresholdEpochMs) async {
    deletedOlderThanMs = thresholdEpochMs;
    return 0;
  }

  @override
  Future<List<UsageEventRecord>> fetchUnsyncedEvents({int limit = 500}) async {
    return pending.take(limit).toList();
  }

  @override
  Future<int> markSynced(List<int> ids) async {
    markedIds = ids;
    return ids.length;
  }

  @override
  Future<void> close() async {}
}

void main() {
  test('uploader posts batch and marks rows synced', () async {
    final db = _FakeUsageDb(
      <UsageEventRecord>[
        UsageEventRecord(
          id: 1,
          eventType: 'unlock',
          startedAtMs: 1000,
        ),
      ],
    );

    Map<String, Object?>? sentPayload;
    String? sentUrl;
    final ok = await UsageUploader.runUploadTask(
      db: db,
      configReader: () async => UsageUploadConfig(
        baseUrl: 'http://127.0.0.1:3000',
        userId: 10,
      ),
      postUsageBatch: (dio, url, payload) async {
        sentUrl = url;
        sentPayload = payload;
        return Response<dynamic>(
          requestOptions: RequestOptions(path: url),
          statusCode: 200,
          data: <String, Object?>{'success': true},
        );
      },
    );

    expect(ok, isTrue);
    expect(sentUrl, 'http://127.0.0.1:3000/api/usage/events');
    expect(sentPayload?['userId'], 10);
    final events = sentPayload?['events'] as List<dynamic>;
    expect(events, hasLength(1));
    expect((events.first as Map<String, Object?>)['event_type'], 'unlock');
    expect(db.markedIds, <int>[1]);
    expect(db.deletedOlderThanMs, isNotNull);
  });

  test('uploader handles 404 gracefully and keeps queue', () async {
    final db = _FakeUsageDb(
      <UsageEventRecord>[
        UsageEventRecord(
          id: 9,
          eventType: 'screen_on',
          startedAtMs: 2000,
        ),
      ],
    );

    final ok = await UsageUploader.runUploadTask(
      db: db,
      configReader: () async => UsageUploadConfig(
        baseUrl: 'http://127.0.0.1:3000',
        userId: 11,
      ),
      postUsageBatch: (dio, url, payload) async {
        throw DioException(
          requestOptions: RequestOptions(path: url),
          response: Response<dynamic>(
            requestOptions: RequestOptions(path: url),
            statusCode: 404,
          ),
        );
      },
    );

    expect(ok, isTrue);
    expect(db.markedIds, isEmpty);
  });
}
