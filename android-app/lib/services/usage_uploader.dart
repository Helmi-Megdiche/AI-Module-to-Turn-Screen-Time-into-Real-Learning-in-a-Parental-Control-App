import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:workmanager/workmanager.dart';

import 'usage_db.dart';

typedef UsageLogFn = Future<void> Function(String message);
typedef ConfigReaderFn = Future<UsageUploadConfig?> Function();
typedef DioFactory = Dio Function();
typedef DateTimeNowFn = DateTime Function();
typedef PostUsageBatchFn = Future<Response<dynamic>> Function(
  Dio dio,
  String url,
  Map<String, Object?> payload,
);

class UsageUploadConfig {
  UsageUploadConfig({
    required this.baseUrl,
    required this.userId,
  });

  final String baseUrl;
  final int userId;
}

class UsageUploader {
  static const String periodicTaskName = 'usageEventsUpload';
  static const String periodicTaskUniqueName = 'usageEventsUploadUnique';
  static const String configFileName = 'usage_upload_config.json';

  static Future<void> registerPeriodicTask() async {
    await Workmanager().registerPeriodicTask(
      periodicTaskUniqueName,
      periodicTaskName,
      frequency: const Duration(hours: 1),
      initialDelay: const Duration(hours: 1),
      existingWorkPolicy: ExistingWorkPolicy.keep,
    );
  }

  static Future<void> persistConfig({
    required String baseUrl,
    required int userId,
  }) async {
    final docs = await getApplicationDocumentsDirectory();
    final file = File(p.join(docs.path, configFileName));
    await file.writeAsString(
      jsonEncode(
        <String, Object?>{
          'baseUrl': baseUrl.replaceAll(RegExp(r'/+$'), ''),
          'userId': userId,
        },
      ),
      flush: true,
    );
  }

  static Future<UsageUploadConfig?> _readConfig() async {
    final docs = await getApplicationDocumentsDirectory();
    final file = File(p.join(docs.path, configFileName));
    if (!await file.exists()) {
      return null;
    }
    final raw = await file.readAsString();
    final decoded = jsonDecode(raw);
    if (decoded is! Map) {
      return null;
    }
    final baseUrl = decoded['baseUrl']?.toString();
    final userIdRaw = decoded['userId'];
    final userId = userIdRaw is int ? userIdRaw : int.tryParse('$userIdRaw');
    if (baseUrl == null || baseUrl.isEmpty || userId == null || userId <= 0) {
      return null;
    }
    return UsageUploadConfig(baseUrl: baseUrl, userId: userId);
  }

  static Dio _defaultDioFactory() {
    return Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 60),
        receiveTimeout: const Duration(seconds: 120),
        sendTimeout: const Duration(seconds: 120),
        contentType: Headers.jsonContentType,
      ),
    );
  }

  static Future<bool> runUploadTask({
    Map<String, dynamic>? inputData,
    UsageDb? db,
    UsageLogFn? onLog,
    ConfigReaderFn? configReader,
    DioFactory? dioFactory,
    DateTimeNowFn? nowFn,
    PostUsageBatchFn? postUsageBatch,
  }) async {
    final log = onLog ?? (_) async {};
    final usageDb = db ?? UsageDb();
    final reader = configReader ?? _readConfig;
    final dio = (dioFactory ?? _defaultDioFactory)();
    final post = postUsageBatch ?? _defaultPostUsageBatch;
    final now = (nowFn ?? DateTime.now)();
    final retentionCutoffMs =
        now.subtract(const Duration(days: 30)).millisecondsSinceEpoch;

    await usageDb.deleteOlderThan(retentionCutoffMs);

    final pending = await usageDb.fetchUnsyncedEvents(limit: 500);
    if (pending.isEmpty) {
      await log('usage_uploader: no pending events');
      return true;
    }

    final configFromInput = _configFromInputData(inputData);
    final config = configFromInput ?? await reader();
    if (config == null) {
      await log('usage_uploader: config missing, keeping ${pending.length} events queued');
      return true;
    }

    final payload = <String, Object?>{
      'userId': config.userId,
      'events': pending.map((e) => e.toUploadMap()).toList(),
    };

    try {
      final response = await post(dio, '${config.baseUrl}/api/usage/events', payload);
      if (response.statusCode == 404) {
        await log('usage_uploader: endpoint missing (404), keeping events queued');
        return true;
      }
      final ids = pending.map((e) => e.id).whereType<int>().toList();
      await usageDb.markSynced(ids);
      await log('usage_uploader: uploaded and marked ${ids.length} events synced');
      return true;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        await log('usage_uploader: endpoint missing (404), keeping events queued');
        return true;
      }
      await log('usage_uploader: request failed, keeping events queued');
      return false;
    } catch (_) {
      await log('usage_uploader: unexpected failure, keeping events queued');
      return false;
    }
  }

  static Future<Response<dynamic>> _defaultPostUsageBatch(
    Dio dio,
    String url,
    Map<String, Object?> payload,
  ) {
    return dio.post<dynamic>(url, data: payload);
  }

  static UsageUploadConfig? _configFromInputData(Map<String, dynamic>? inputData) {
    if (inputData == null) {
      return null;
    }
    final baseUrl = inputData['baseUrl']?.toString();
    final userRaw = inputData['userId'];
    final userId = userRaw is int ? userRaw : int.tryParse('$userRaw');
    if (baseUrl == null || baseUrl.isEmpty || userId == null || userId <= 0) {
      return null;
    }
    return UsageUploadConfig(
      baseUrl: baseUrl.replaceAll(RegExp(r'/+$'), ''),
      userId: userId,
    );
  }
}
