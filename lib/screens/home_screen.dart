import 'package:flutter/material.dart';
import '../theme.dart';
import '../models.dart';
import '../api.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _balanceVisible = true;
  double _balance = 134370.20;
  double _income = 45000.0;
  double _expenses = 3972.0;

  final List<Transaction> _recent = [
    Transaction(id: '1', merchant: 'Carrefour', category: 'Groceries', amount: 1437.02, isIncome: false, date: DateTime(2025, 5, 23, 20, 55)),
    Transaction(id: '2', merchant: 'Uber', category: 'Transportation', amount: 85.50, isIncome: false, date: DateTime(2025, 5, 22, 14, 30)),
    Transaction(id: '3', merchant: 'Salary', category: 'Income', amount: 45000.0, isIncome: true, date: DateTime(2025, 5, 1, 9, 0)),
    Transaction(id: '4', merchant: 'Netflix', category: 'Subscription', amount: 165.0, isIncome: false, date: DateTime(2025, 5, 20, 12, 0)),
    Transaction(id: '5', merchant: 'Seif Pharmacy', category: 'Healthcare', amount: 320.0, isIncome: false, date: DateTime(2025, 5, 19, 16, 45)),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top App Bar
              Row(
                children: [
                  CircleAvatar(
                    radius: 22,
                    backgroundColor: FC.lightBurgundy,
                    child: Text('MA', style: fcText(14, FontWeight.w600, FC.deepBurgundy)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Good evening', style: fcText(13, FontWeight.w400, FC.neutralGray)),
                      Text('Moaz', style: fcText(18, FontWeight.w700, FC.darkCharcoal)),
                    ],
                  )),
                  IconButton(
                    onPressed: () {},
                    icon: const Icon(Icons.notifications_outlined, color: FC.deepBurgundy),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Balance Card
              _balanceCard(),
              const SizedBox(height: 20),

              // Financial Summary
              _financialSummary(),
              const SizedBox(height: 20),

              // Spending Overview
              _spendingOverview(),
              const SizedBox(height: 20),

              // Recent Transactions
              _recentTransactions(),
              const SizedBox(height: 20),

              // Financial Coach Insights
              _coachInsights(),
              const SizedBox(height: 20),

              // Quick Actions
              _quickActions(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _balanceCard() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [FC.deepBurgundy, FC.darkBurgundy],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [BoxShadow(color: FC.deepBurgundy.withOpacity(0.3), blurRadius: 16, offset: const Offset(0, 8))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Total Balance', style: fcText(14, FontWeight.w500, Colors.white70)),
              IconButton(
                onPressed: () => setState(() => _balanceVisible = !_balanceVisible),
                icon: Icon(_balanceVisible ? Icons.visibility : Icons.visibility_off, color: Colors.white70, size: 20),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            _balanceVisible ? 'EGP ${_fmt(_balance)}' : 'EGP ••••••',
            style: fcText(32, FontWeight.w700, Colors.white, spacing: -1),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Income', style: fcText(12, FontWeight.w400, Colors.white60)),
                  const SizedBox(height: 4),
                  Text('EGP ${_fmt(_income)}', style: fcText(16, FontWeight.w600, FC.softGreen)),
                ],
              )),
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Expenses', style: fcText(12, FontWeight.w400, Colors.white60)),
                  const SizedBox(height: 4),
                  Text('EGP ${_fmt(_expenses)}', style: fcText(16, FontWeight.w600, FC.softRed)),
                ],
              )),
            ],
          ),
        ],
      ),
    );
  }

  Widget _financialSummary() {
    final spentPct = _expenses / _income;
    final remaining = _income - _expenses;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Financial Summary', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
          const SizedBox(height: 16),
          Row(
            children: [
              _summaryTile('Income', 'EGP ${_fmt(_income)}', FC.softGreen, Icons.arrow_downward_rounded),
              const SizedBox(width: 12),
              _summaryTile('Expenses', 'EGP ${_fmt(_expenses)}', FC.softRed, Icons.arrow_upward_rounded),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _summaryTile('Remaining', 'EGP ${_fmt(remaining)}', FC.mutedGold, Icons.savings_rounded),
              const SizedBox(width: 12),
              _summaryTile('Spent', '${(spentPct * 100).toStringAsFixed(1)}%', FC.deepBurgundy, Icons.pie_chart_rounded),
            ],
          ),
          const SizedBox(height: 16),
          ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: LinearProgressIndicator(
              value: spentPct.clamp(0.0, 1.0),
              minHeight: 8,
              backgroundColor: FC.lightGray,
              valueColor: AlwaysStoppedAnimation(FC.deepBurgundy),
            ),
          ),
        ],
      ),
    );
  }

  Widget _summaryTile(String label, String value, Color color, IconData icon) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: FC.lightGray, borderRadius: BorderRadius.circular(12)),
        child: Row(
          children: [
            Container(
              width: 36, height: 36,
              decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
              child: Icon(icon, color: color, size: 18),
            ),
            const SizedBox(width: 8),
            Expanded(child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: fcText(11, FontWeight.w400, FC.neutralGray)),
                Text(value, style: fcText(13, FontWeight.w600, FC.darkCharcoal), overflow: TextOverflow.ellipsis),
              ],
            )),
          ],
        ),
      ),
    );
  }

  Widget _spendingOverview() {
    // Category breakdown
    final cats = <String, double>{
      'Groceries': 1437.02,
      'Transportation': 85.50,
      'Subscription': 165.0,
      'Healthcare': 320.0,
      'Other': 1965.48,
    };
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Spending Overview', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
          const SizedBox(height: 4),
          Text('This month vs last month', style: fcText(12, FontWeight.w400, FC.neutralGray)),
          const SizedBox(height: 16),
          // Donut chart placeholder
          Center(
            child: SizedBox(
              width: 160, height: 160,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: 0.65,
                    strokeWidth: 16,
                    backgroundColor: FC.lightGray,
                    valueColor: AlwaysStoppedAnimation(FC.deepBurgundy),
                  ),
                  Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('EGP', style: fcText(12, FontWeight.w400, FC.neutralGray)),
                      Text(_fmt(_expenses), style: fcText(18, FontWeight.w700, FC.darkCharcoal)),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          ...cats.entries.map((e) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                Container(width: 12, height: 12, decoration: BoxDecoration(color: categoryColor(e.key), borderRadius: BorderRadius.circular(3))),
                const SizedBox(width: 8),
                Expanded(child: Text(e.key, style: fcText(13, FontWeight.w400, FC.darkCharcoal))),
                Text('EGP ${_fmt(e.value)}', style: fcText(13, FontWeight.w600, FC.darkCharcoal)),
              ],
            ),
          )),
        ],
      ),
    );
  }

  Widget _recentTransactions() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Recent Transactions', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
              TextButton(onPressed: () {}, child: Text('View All', style: fcText(13, FontWeight.w600, FC.deepBurgundy))),
            ],
          ),
          const SizedBox(height: 8),
          ..._recent.map((t) => _transactionTile(t)),
        ],
      ),
    );
  }

  Widget _transactionTile(Transaction t) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
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
              Text('${t.category} • ${_formatDate(t.date)}', style: fcText(12, FontWeight.w400, FC.neutralGray)),
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

  Widget _coachInsights() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [FC.lightBurgundy, FC.warmWhite], begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: FC.deepBurgundy.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome, color: FC.deepBurgundy, size: 20),
              const SizedBox(width: 8),
              Text('Financial Coach', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
            ],
          ),
          const SizedBox(height: 12),
          _insightTile(Icons.savings_rounded, 'Savings Tip', 'You spent 15% less on dining this month. Consider adding EGP 200 to your savings goal.', FC.softGreen),
          const SizedBox(height: 8),
          _insightTile(Icons.warning_rounded, 'Spending Alert', 'Your entertainment spending is 40% higher than last month.', FC.softRed),
          const SizedBox(height: 8),
          _insightTile(Icons.lightbulb_rounded, 'Smart Tip', 'Switching to annual billing for subscriptions could save you EGP 120/year.', FC.mutedGold),
        ],
      ),
    );
  }

  Widget _insightTile(IconData icon, String title, String message, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 36, height: 36,
          decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
          child: Icon(icon, color: color, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: fcText(13, FontWeight.w600, FC.darkCharcoal)),
            Text(message, style: fcText(12, FontWeight.w400, FC.neutralGray, height: 1.4)),
          ],
        )),
      ],
    );
  }

  Widget _quickActions() {
    final actions = [
      (Icons.add_rounded, 'Add Transaction', FC.deepBurgundy),
      (Icons.account_balance_wallet_rounded, 'Add Income', FC.softGreen),
      (Icons.mic_rounded, 'Voice Entry', FC.mutedGold),
      (Icons.receipt_long_rounded, 'Pay Bill', FC.neutralGray),
      (Icons.calculate_rounded, 'Installments', FC.deepBurgundy),
      (Icons.add_chart_rounded, 'Add Widget', FC.softRed),
    ];
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Quick Actions', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12, runSpacing: 12,
            children: actions.map((a) => SizedBox(
              width: (MediaQuery.of(context).size.width - 88) / 3,
              child: Column(
                children: [
                  Container(
                    width: 56, height: 56,
                    decoration: BoxDecoration(color: a.$3.withOpacity(0.1), borderRadius: BorderRadius.circular(16)),
                    child: Icon(a.$1, color: a.$3, size: 26),
                  ),
                  const SizedBox(height: 6),
                  Text(a.$2, style: fcText(11, FontWeight.w500, FC.darkCharcoal), textAlign: TextAlign.center, maxLines: 2),
                ],
              ),
            )).toList(),
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

  String _formatDate(DateTime d) {
    final now = DateTime.now();
    if (d.day == now.day && d.month == now.month && d.year == now.year) return 'Today';
    return '${d.day}/${d.month}/${d.year}';
  }
}
EOF