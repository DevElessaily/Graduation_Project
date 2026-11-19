import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../theme.dart';
import '../api.dart';

class IncomeScreen extends StatefulWidget {
  const IncomeScreen({super.key});
  @override
  State<IncomeScreen> createState() => _IncomeScreenState();
}

class _IncomeScreenState extends State<IncomeScreen> {
  final _titleCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  final _sourceCtrl = TextEditingController();
  List<Map<String, dynamic>> _incomes = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await http.get(Uri.parse('${Api.baseUrl}/api/income'));
      setState(() { _incomes = List<Map<String, dynamic>>.from(jsonDecode(r.body)); _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _add() async {
    if (_titleCtrl.text.isEmpty || _amountCtrl.text.isEmpty) return;
    await http.post(
      Uri.parse('${Api.baseUrl}/api/income'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'title': _titleCtrl.text, 'amount': _amountCtrl.text, 'source': _sourceCtrl.text}),
    );
    _titleCtrl.clear(); _amountCtrl.clear(); _sourceCtrl.clear();
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Income')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
              child: Column(
                children: [
                  TextField(controller: _titleCtrl, decoration: const InputDecoration(labelText: 'Title (e.g. Salary)')),
                  const SizedBox(height: 12),
                  TextField(controller: _amountCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Amount (EGP)')),
                  const SizedBox(height: 12),
                  TextField(controller: _sourceCtrl, decoration: const InputDecoration(labelText: 'Source (optional)')),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _add,
                      style: ElevatedButton.styleFrom(backgroundColor: FC.deepBurgundy, foregroundColor: Colors.white),
                      child: const Text('Add Income'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Text('Income History', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
            const SizedBox(height: 12),
            if (_loading) const Center(child: CircularProgressIndicator())
            else if (_incomes.isEmpty) Center(child: Text('No income recorded', style: fcText(13, FontWeight.w400, FC.neutralGray)))
            else ..._incomes.map((i) => Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(14)),
              child: Row(
                children: [
                  Container(width: 44, height: 44, decoration: BoxDecoration(color: FC.softGreen.withOpacity(0.15), borderRadius: BorderRadius.circular(12)), child: const Icon(Icons.arrow_downward, color: FC.softGreen)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${i['title']}', style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
                    if (i['source'] != null) Text('${i['source']}', style: fcText(12, FontWeight.w400, FC.neutralGray)),
                  ])),
                  Text('EGP ${i['amount']}', style: fcText(14, FontWeight.w600, FC.softGreen)),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}
