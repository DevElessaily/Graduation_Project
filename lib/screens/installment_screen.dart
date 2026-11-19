import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../theme.dart';
import '../api.dart';

class InstallmentScreen extends StatefulWidget {
  const InstallmentScreen({super.key});
  @override
  State<InstallmentScreen> createState() => _InstallmentScreenState();
}

class _InstallmentScreenState extends State<InstallmentScreen> {
  final _titleCtrl = TextEditingController();
  final _totalCtrl = TextEditingController();
  final _monthlyCtrl = TextEditingController();
  DateTime? _startDate;
  DateTime? _endDate;
  List<Map<String, dynamic>> _installments = [];
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await http.get(Uri.parse('${Api.baseUrl}/api/installments'));
      setState(() { _installments = List<Map<String, dynamic>>.from(jsonDecode(r.body)); _loading = false; });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _add() async {
    if (_titleCtrl.text.isEmpty || _totalCtrl.text.isEmpty || _monthlyCtrl.text.isEmpty || _startDate == null) return;
    await http.post(
      Uri.parse('${Api.baseUrl}/api/installments'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'title': _titleCtrl.text,
        'total_amount': _totalCtrl.text,
        'monthly_amount': _monthlyCtrl.text,
        'start_date': _startDate!.toIso8601String().split('T')[0],
        'end_date': _endDate?.toIso8601String().split('T')[0],
      }),
    );
    _titleCtrl.clear(); _totalCtrl.clear(); _monthlyCtrl.clear();
    _startDate = null; _endDate = null;
    _load();
  }

  Future<void> _pickDate(bool isStart) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2035),
    );
    if (picked != null) {
      setState(() {
        if (isStart) _startDate = picked; else _endDate = picked;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Installments')),
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
                  TextField(controller: _titleCtrl, decoration: const InputDecoration(labelText: 'Title (e.g. Car Loan)')),
                  const SizedBox(height: 12),
                  TextField(controller: _totalCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Total Amount (EGP)')),
                  const SizedBox(height: 12),
                  TextField(controller: _monthlyCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Monthly Payment (EGP)')),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(child: OutlinedButton(
                        onPressed: () => _pickDate(true),
                        child: Text(_startDate == null ? 'Start Date' : '${_startDate!.day}/${_startDate!.month}/${_startDate!.year}'),
                      )),
                      const SizedBox(width: 12),
                      Expanded(child: OutlinedButton(
                        onPressed: () => _pickDate(false),
                        child: Text(_endDate == null ? 'End Date (optional)' : '${_endDate!.day}/${_endDate!.month}/${_endDate!.year}'),
                      )),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _add,
                      style: ElevatedButton.styleFrom(backgroundColor: FC.deepBurgundy, foregroundColor: Colors.white),
                      child: const Text('Add Installment'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Text('Your Installments', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
            const SizedBox(height: 12),
            if (_loading) const Center(child: CircularProgressIndicator())
            else if (_installments.isEmpty) Center(child: Text('No installments', style: fcText(13, FontWeight.w400, FC.neutralGray)))
            else ..._installments.map((inst) {
              final total = double.tryParse('${inst['total_amount']}') ?? 0;
              final monthly = double.tryParse('${inst['monthly_amount']}') ?? 0;
              final remaining = double.tryParse('${inst['remaining_amount']}') ?? 0;
              final paid = total - remaining;
              final progress = total > 0 ? (paid / total).clamp(0.0, 1.0) : 0.0;
              return Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(14)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text('${inst['title']}', style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
                        Text('EGP ${monthly.toStringAsFixed(0)}/mo', style: fcText(13, FontWeight.w600, FC.deepBurgundy)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text('Remaining: EGP ${remaining.toStringAsFixed(0)} of ${total.toStringAsFixed(0)}', style: fcText(12, FontWeight.w400, FC.neutralGray)),
                    const SizedBox(height: 8),
                    ClipRRect(borderRadius: BorderRadius.circular(6), child: LinearProgressIndicator(value: progress, minHeight: 6, backgroundColor: FC.lightGray, valueColor: const AlwaysStoppedAnimation(FC.softGreen))),
                    const SizedBox(height: 4),
                    Text('Next payment: ${inst['start_date']}', style: fcText(11, FontWeight.w400, FC.neutralGray)),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
EOF