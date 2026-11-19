import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'theme.dart';
import 'api.dart';

class VoiceResult {
  final String transcript;
  const VoiceResult(this.transcript);
}

class VoiceRecorder {
  static const _method = MethodChannel('com.example.financial_coach/voice');
  static const _events = EventChannel('com.example.financial_coach/voice_events');

  static Stream<Map<String, dynamic>>? _stream;

  static Stream<Map<String, dynamic>> get events {
    return _stream ??= _events
        .receiveBroadcastStream()
        .where((event) => event is Map)
        .map((event) => Map<String, dynamic>.from(event as Map));
  }

  static Future<String> start() async {
    final result = await _method.invokeMethod<String>('startVoiceRecording');
    return result ?? '';
  }

  static Future<void> stop() async => await _method.invokeMethod<void>('stopVoiceRecording');
  static Future<void> cancel() async => await _method.invokeMethod<void>('cancelVoiceRecording');
}

class VoiceEntryButton extends StatefulWidget {
  final void Function(String transcript) onResult;
  const VoiceEntryButton({super.key, required this.onResult});

  @override
  State<VoiceEntryButton> createState() => _VoiceEntryButtonState();
}

class _VoiceEntryButtonState extends State<VoiceEntryButton> {
  bool _listening = false;
  String _partial = '';

  @override
  void initState() {
    super.initState();
    VoiceRecorder.events.listen((event) {
      final type = event['type'];
      if (type == 'partial') {
        if (mounted) setState(() => _partial = event['transcript'] ?? '');
      } else if (type == 'completed') {
        if (mounted) setState(() { _listening = false; _partial = ''; });
        widget.onResult(event['transcript'] ?? '');
      } else if (type == 'error') {
        if (mounted) setState(() { _listening = false; _partial = ''; });
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(event['message'] ?? 'Error')));
      } else if (type == 'cancelled') {
        if (mounted) setState(() { _listening = false; _partial = ''; });
      }
    });
  }

  Future<void> _toggle() async {
    if (_listening) {
      await VoiceRecorder.stop();
      if (mounted) setState(() => _listening = false);
    } else {
      if (mounted) setState(() { _listening = true; _partial = ''; });
      await VoiceRecorder.start();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        if (_partial.isNotEmpty)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(_partial, style: const TextStyle(fontStyle: FontStyle.italic, color: FC.neutralGray)),
          ),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: OutlinedButton.icon(
            onPressed: _toggle,
            icon: Icon(_listening ? Icons.stop : Icons.mic, color: _listening ? Colors.red : FC.deepBurgundy),
            label: Text(_listening ? 'Listening...' : 'Voice Entry', style: fcText(16, FontWeight.w600, _listening ? Colors.red : FC.deepBurgundy)),
            style: OutlinedButton.styleFrom(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              side: BorderSide(color: _listening ? Colors.red : FC.deepBurgundy),
            ),
          ),
        ),
      ],
    );
  }
}
