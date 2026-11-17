import 'package:flutter/material.dart';
import '../theme.dart';
import '../models.dart';

class TransactionsScreen extends StatefulWidget {
  const TransactionsScreen({super.key});
  @override
  State<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TransactionsScreenState extends State<TransactionsScreen> {
  String _filter = 'All';
  final _filters = ['All', 'Income', 'Expense', 'Transfer'];

  final List<Transaction> _txns = [
    Transaction(id: '1', merchant: 'Carrefour', category: 'Groceries', amount: 1437.02, isIncome: false, date: DateTime(2025, 5, 23, 20, 55)),
    Transaction(id: '2', merchant: 'Uber', category: 'Transportation', amount: 85.50, isIncome: false, date: DateTime(2025, 5, 22, 14, 30)),
    Transaction(id: '3', merchant: 'Salary', category: 'Income', amount: 45000.0, isIncome: true, date: DateTime(2025, 5, 1, 9, 0)),
    Transaction(id: '4', merchant: 'Netflix', category: 'Subscription', amount: 165.0, isIncome: false, date: DateTime(2025, 5, 20, 12, 0)),
    Transaction(id: '5', merchant: 'Seif Pharmacy', category: 'Healthcare', amount: 320.0, isIncome: false, date: DateTime(2025, 5, 19, 16, 45)),
    Transaction(id: '6', merchant: 'KFC', category: 'Restaurants', amount: 210.0, isIncome: false, date: DateTime(2025, 5, 18, 13, 0)),
    Transaction(id: '7', merchant: 'Amazon.eg', category: 'Shopping', amount: 899.0, isIncome: false, date: DateTime(2025, 5, 17, 10, 0)),
    Transaction(id: '8', merchant: 'Uber', category: 'Transportation', amount: 120.0, isIncome: false, date: DateTime(2025, 5, 16, 8, 30)),
  ];

  List<Transaction> get _filtered {
    if (_filter == 'All') return _txns;
    if (_filter == 'Income') return _txns.where((t) => t.isIncome).toList();
    if (_filter == 'Expense') return _txns.where((t) => !t.isIncome).toList();
    return _txns.where((t) => t.category == _filter).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Transactions')),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              decoration: InputDecoration(
                hintText: 'Search transactions...',
                prefixIcon: const Icon(Icons.search, color: FC.neutralGray),
                filled: true,
                fillColor: FC.warmWhite,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
          ),
          // Filter chips
          SizedBox(
            height: 40,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              children: _filters.map((f) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(f),
                  selected: _filter == f,
                  onSelected: (_) => setState(() => _filter = f),
                  selectedColor: FC.deepBurgundy.withOpacity(0.15),
                  checkmarkColor: FC.deepBurgundy,
                  labelStyle: fcText(13, FontWeight.w500, _filter == f ? FC.deepBurgundy : FC.neutralGray),
                ),
              )).toList(),
            ),
          ),
          const SizedBox(height: 8),
          // Transaction list
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _filtered.length,
              itemBuilder: (ctx, i) {
                final t = _filtered[i];
                return _tile(t);
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: FC.deepBurgundy,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  Widget _tile(Transaction t) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(14)),
      child: Row(
        children: [
          Container(
            width: 44, height: 44,
            decoration: BoxDecoration(color: categoryColor(t.category).withOpacity(0.15), borderRadius: BorderRadius.circular(12)),
            child: Icon(categoryIcon(t.category), color: categoryColor(t.category), size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(t.merchant, style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
              Text('${t.category} • ${_fmtDate(t.date)}', style: fcText(12, FontWeight.w400, FC.neutralGray)),
            ],
          )),
          Text(
            '${t.isIncome ? '+' : '-'} EGP ${_fmt(t.amount)}',
            style: fcText(14, FontWeight.w600, t.isIncome ? FC.softGreen : FC.softRed),
          ),
        ],
      ),
    );
  }

  String _fmt(double v) {
    final fixed = v.toStringAsFixed(2).split('.');
    final whole = fixed[0].replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
    return '$whole.${fixed[1]}';
  }

  String _fmtDate(DateTime d) {
    final now = DateTime.now();
    if (d.day == now.day && d.month == now.month) return 'Today';
    return '${d.day}/${d.month}';
  }
}
EOF