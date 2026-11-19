import 'package:flutter/material.dart';
import '../theme.dart';
import '../voice.dart';
import '../api.dart';

class AddTransactionScreen extends StatefulWidget {
  const AddTransactionScreen({super.key});
  @override
  State<AddTransactionScreen> createState() => _AddTransactionScreenState();
}

class _AddTransactionScreenState extends State<AddTransactionScreen> {
  bool _isExpense = true;
  final _amountCtrl = TextEditingController();
  final _merchantCtrl = TextEditingController();
  final _descCtrl = TextEditingController();
  String _category = 'Groceries';
  final _categories = ['Groceries', 'Restaurants', 'Transportation', 'Shopping', 'Utilities', 'Healthcare', 'Entertainment', 'Subscription', 'Education', 'Travel', 'Personal Care', 'Transfer', 'Income', 'Cash Withdrawal', 'Fees', 'Refund'];

  void _onVoiceResult(String transcript) async {
    if (transcript.trim().isEmpty) return;
    final result = await Api.parseSms('voice', transcript);
    if (result['is_transaction'] == true) {
      final tx = result['transaction'];
      setState(() {
        _amountCtrl.text = tx['amount'] ?? '';
        _merchantCtrl.text = tx['merchant'] ?? '';
        _category = tx['category'] ?? 'Other';
        _descCtrl.text = tx['description'] ?? '';
        _isExpense = tx['type'] != 'income';
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Parsed: ${tx['amount']} EGP at ${tx['merchant']}')),
        );
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not detect a transaction from speech')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Transaction')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Type toggle
            Row(
              children: [
                Expanded(child: _typeBtn('Expense', _isExpense, () => setState(() => _isExpense = true))),
                const SizedBox(width: 12),
                Expanded(child: _typeBtn('Income', !_isExpense, () => setState(() => _isExpense = false))),
              ],
            ),
            const SizedBox(height: 20),
            // Amount
            TextField(controller: _amountCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Amount (EGP)', prefixIcon: Icon(Icons.attach_money))),
            const SizedBox(height: 16),
            // Merchant
            TextField(controller: _merchantCtrl, decoration: const InputDecoration(labelText: 'Merchant', prefixIcon: Icon(Icons.store))),
            const SizedBox(height: 16),
            // Category
            DropdownButtonFormField<String>(
              value: _categories.contains(_category) ? _category : 'Groceries',
              decoration: const InputDecoration(labelText: 'Category', prefixIcon: Icon(Icons.category)),
              items: _categories.map((c) => DropdownMenuItem(value: c, child: Text(c))).toList(),
              onChanged: (v) => setState(() => _category = v!),
            ),
            const SizedBox(height: 16),
            // Description
            TextField(controller: _descCtrl, maxLines: 3, decoration: const InputDecoration(labelText: 'Description (optional)', prefixIcon: Icon(Icons.notes))),
            const SizedBox(height: 24),
            // Submit
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Transaction added')));
                  Navigator.pop(context);
                },
                style: ElevatedButton.styleFrom(backgroundColor: FC.deepBurgundy, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                child: const Text('Save Transaction', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
              ),
            ),
            const SizedBox(height: 12),
            // Voice entry
            VoiceEntryButton(onResult: _onVoiceResult),
          ],
        ),
      ),
    );
  }

  Widget _typeBtn(String label, bool selected, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: selected ? FC.deepBurgundy : FC.warmWhite,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? FC.deepBurgundy : FC.divider),
        ),
        child: Center(child: Text(label, style: fcText(14, FontWeight.w600, selected ? Colors.white : FC.neutralGray))),
      ),
    );
  }
}
