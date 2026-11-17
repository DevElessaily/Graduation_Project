import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart';

class DeviceSms {
  const DeviceSms({required this.id, required this.sender, required this.message, required this.date});
  final int id;
  final String sender;
  final String message;
  final DateTime date;

  factory DeviceSms.fromMap(Map<dynamic, dynamic> map) {
    final millis = (map['date'] as num?)?.toInt() ?? 0;
    return DeviceSms(
      id: (map['id'] as num?)?.toInt() ?? 0,
      sender: '${map['sender'] ?? 'Unknown'}',
      message: '${map['message'] ?? ''}',
      date: DateTime.fromMillisecondsSinceEpoch(millis),
    );
  }
}

class SmsPermissionStatus {
  const SmsPermissionStatus({required this.canRead, required this.canReceive});
  final bool canRead;
  final bool canReceive;
  static const none = SmsPermissionStatus(canRead: false, canReceive: false);
  factory SmsPermissionStatus.fromMap(Map<dynamic, dynamic>? map) {
    if (map == null) return none;
    return SmsPermissionStatus(canRead: map['read'] == true, canReceive: map['receive'] == true);
  }
}

class SmsFlushResult {
  const SmsFlushResult({this.stored = 0, this.skipped = 0, this.failed = 0,
    this.pending = 0, this.transactionsCreated = 0, this.error});
  final int stored, skipped, failed, pending, transactionsCreated;
  final String? error;
  factory SmsFlushResult.fromMap(Map<dynamic, dynamic>? map) {
    if (map == null) return const SmsFlushResult();
    return SmsFlushResult(
      stored: (map['stored'] as num?)?.toInt() ?? 0,
      skipped: (map['skipped'] as num?)?.toInt() ?? 0,
      failed: (map['failed'] as num?)?.toInt() ?? 0,
      pending: (map['pending'] as num?)?.toInt() ?? 0,
      transactionsCreated: (map['transactions_created'] as num?)?.toInt() ?? 0,
      error: map['error'] as String?,
    );
  }
}

class SmsLiveEvent {
  const SmsLiveEvent({required this.type, this.sender, this.message, this.date,
    this.stored = 0, this.skipped = 0, this.pending = 0, this.transactionsCreated = 0, this.error});
  final String type;
  final String? sender, message, error;
  final int? date;
  final int stored, skipped, pending, transactionsCreated;
  factory SmsLiveEvent.fromMap(Map<dynamic, dynamic> map) => SmsLiveEvent(
    type: '${map['type'] ?? ''}',
    sender: map['sender'] as String?,
    message: map['message'] as String?,
    date: (map['date'] as num?)?.toInt(),
    stored: (map['stored'] as num?)?.toInt() ?? 0,
    skipped: (map['skipped'] as num?)?.toInt() ?? 0,
    pending: (map['pending'] as num?)?.toInt() ?? 0,
    transactionsCreated: (map['transactions_created'] as num?)?.toInt() ?? 0,
    error: map['error'] as String?,
  );
}

class SmsReader {
  static const _channel = MethodChannel('com.example.financial_coach/sms');

  static Future<bool> hasPermission() async =>
      (await _channel.invokeMethod<bool>('hasPermission')) ?? false;

  static Future<SmsPermissionStatus> permissionStatus() async {
    final r = await _channel.invokeMethod<Map>('permissionStatus');
    return SmsPermissionStatus.fromMap(r);
  }

  static Future<bool> requestPermission() async =>
      (await _channel.invokeMethod<bool>('requestPermission')) ?? false;

  static Future<void> openSettings() async =>
      await _channel.invokeMethod<void>('openSettings');

  static Future<List<DeviceSms>> readInbox({int limit = 200}) async {
    final result = await _channel.invokeMethod<List<dynamic>>('getInbox', {'limit': limit});
    return (result ?? []).whereType<Map>().map(DeviceSms.fromMap).toList();
  }

  static Future<SmsFlushResult> flushPending() async {
    final result = await _channel.invokeMethod<Map>('flushPending');
    return SmsFlushResult.fromMap(result);
  }
}

class SmsLive {
  static const _channel = EventChannel('com.example.financial_coach/sms_events');
  static Stream<SmsLiveEvent>? _stream;

  static Stream<SmsLiveEvent> get stream {
    return _stream ??= _channel
        .receiveBroadcastStream()
        .where((event) => event is Map)
        .map((event) => SmsLiveEvent.fromMap(event as Map));
  }
}
EOF