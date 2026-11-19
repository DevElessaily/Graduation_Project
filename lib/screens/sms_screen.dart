import 'package:flutter/material.dart';
import '../theme.dart';
import '../models.dart';
import '../sms.dart';
import '../api.dart';

class SmsScreen extends StatefulWidget {
  const SmsScreen({super.key});
  @override
  State<SmsScreen> createState() => _SmsScreenState();
}

class _SmsScreenState extends State<SmsScreen> {
  bool _hasPermission = false;
  List<DeviceSms> _inbox = [];
  List<Map<String, dynamic>> _synced = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _checkPermission();
    SmsLive.stream.listen((event) {
      if (mounted) setState(() {});
    });
  }

  Future<void> _checkPermission() async {
    final granted = await SmsReader.hasPermission();
    setState(() => _hasPermission = granted);
    if (granted) _loadInbox();
  }

  Future<void> _requestPermission() async {
    final granted = await SmsReader.requestPermission();
    setState(() => _hasPermission = granted);
    if (granted) _loadInbox();
  }

  Future<void> _loadInbox() async {
    setState(() => _loading = true);
    final msgs = await SmsReader.readInbox(limit: 50);
    setState(() { _inbox = msgs; _loading = false; });
  }

  Future<void> _syncToServer() async {
    final items = _inbox.map((s) => {'sender': s.sender, 'message': s.message, 'date': s.date.millisecondsSinceEpoch ~/ 1000}).toList();
    final result = await Api.syncSms(items);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Synced: ${result['stored']} new, ${result['skipped']} skipped')));
      _loadSynced();
    }
  }

  Future<void> _loadSynced() async {
    final h = await Api.fetchSmsHistory(limit: 50);
    setState(() => _synced = h);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SMS Transactions')),
      body: !_hasPermission
          ? Center(child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.sms, size: 64, color: FC.neutralGray),
                const SizedBox(height: 16),
                Text('SMS access required', style: fcText(18, FontWeight.w700, FC.darkCharcoal)),
                const SizedBox(height: 8),
                Text('Grant SMS permission to detect transactions', style: fcText(14, FontWeight.w400, FC.neutralGray)),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: _requestPermission,
                  style: ElevatedButton.styleFrom(backgroundColor: FC.deepBurgundy, foregroundColor: Colors.white),
                  child: const Text('Grant Permission'),
                ),
              ],
            ))
          : DefaultTabController(
              length: 2,
              child: Column(
                children: [
                  const TabBar(tabs: [Tab(text: 'On this phone'), Tab(text: 'Synced')]),
                  Expanded(child: TabBarView(children: [
                    // On this phone
                    _loading
                        ? const Center(child: CircularProgressIndicator())
                        : ListView.builder(
                            itemCount: _inbox.length,
                            itemBuilder: (ctx, i) {
                              final s = _inbox[i];
                              return ListTile(
                                leading: CircleAvatar(backgroundColor: FC.lightBurgundy, child: Icon(Icons.sms, color: FC.deepBurgundy, size: 20)),
                                title: Text(s.sender, style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
                                subtitle: Text(s.message, maxLines: 2, overflow: TextOverflow.ellipsis, style: fcText(12, FontWeight.w400, FC.neutralGray)),
                                trailing: Text('${s.date.day}/${s.date.month}', style: fcText(11, FontWeight.w400, FC.neutralGray)),
                              );
                            },
                          ),
                    // Synced
                    ListView.builder(
                      itemCount: _synced.length,
                      itemBuilder: (ctx, i) {
                        final s = _synced[i];
                        return ListTile(
                          leading: CircleAvatar(backgroundColor: FC.lightBurgundy, child: Icon(Icons.check, color: FC.softGreen, size: 20)),
                          title: Text('${s['sender']}', style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
                          subtitle: Text('${s['message']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: fcText(12, FontWeight.w400, FC.neutralGray)),
                          trailing: s['transaction_category'] != null
                              ? Chip(label: Text('${s['transaction_category']}', style: fcText(10, FontWeight.w600, FC.deepBurgundy)), backgroundColor: FC.lightBurgundy)
                              : null,
                        );
                      },
                    ),
                  ])),
                ],
              ),
            ),
      floatingActionButton: _hasPermission
          ? FloatingActionButton(
              onPressed: _syncToServer,
              backgroundColor: FC.deepBurgundy,
              child: const Icon(Icons.sync, color: Colors.white),
            )
          : null,
    );
  }
}
