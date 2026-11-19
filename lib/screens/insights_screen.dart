import 'package:flutter/material.dart';
import '../theme.dart';
import '../models.dart';

class InsightsScreen extends StatelessWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Insights & Analytics')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Monthly spending card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Monthly Spending', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _statCol('This Month', 'EGP 3,972', FC.deepBurgundy),
                      _statCol('Last Month', 'EGP 4,210', FC.neutralGray),
                      _statCol('Change', '-5.7%', FC.softGreen),
                    ],
                  ),
                  const SizedBox(height: 16),
                  // Bar chart placeholder
                  SizedBox(
                    height: 120,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [0.4, 0.6, 0.5, 0.8, 0.7, 0.9, 0.65].map((v) => Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Container(
                            height: 120 * v,
                            decoration: BoxDecoration(
                              color: FC.deepBurgundy.withOpacity(0.7),
                              borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
                            ),
                          ),
                        ),
                      )).toList(),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Category breakdown
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Category Breakdown', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
                  const SizedBox(height: 16),
                  Center(child: Text('No spending data yet', style: fcText(13, FontWeight.w400, FC.neutralGray))),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Top spending
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Top Spending Categories', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
                  const SizedBox(height: 12),
                  Center(child: Text('No spending data yet', style: fcText(13, FontWeight.w400, FC.neutralGray))),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statCol(String label, String value, Color color) => Column(
    children: [
      Text(label, style: fcText(12, FontWeight.w400, FC.neutralGray)),
      const SizedBox(height: 4),
      Text(value, style: fcText(16, FontWeight.w700, color)),
    ],
  );

  Widget _catRow(String name, double amount, double pct, Color color) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      children: [
        Container(width: 12, height: 12, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 8),
        Expanded(child: Text(name, style: fcText(13, FontWeight.w400, FC.darkCharcoal))),
        Text('EGP ${amount.toStringAsFixed(0)}', style: fcText(13, FontWeight.w600, FC.darkCharcoal)),
        const SizedBox(width: 8),
        SizedBox(width: 60, child: LinearProgressIndicator(value: pct, backgroundColor: FC.lightGray, valueColor: AlwaysStoppedAnimation(color), minHeight: 6)),
      ],
    ),
  );

  Widget _topCat(String name, String amount, IconData icon, Color color) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(
      children: [
        Container(width: 40, height: 40, decoration: BoxDecoration(color: color.withOpacity(0.15), borderRadius: BorderRadius.circular(10)), child: Icon(icon, color: color, size: 20)),
        const SizedBox(width: 12),
        Expanded(child: Text(name, style: fcText(14, FontWeight.w600, FC.darkCharcoal))),
        Text(amount, style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
      ],
    ),
  );
}
EOF