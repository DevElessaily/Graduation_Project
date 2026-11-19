import 'package:flutter/material.dart';
import '../theme.dart';

class BudgetScreen extends StatelessWidget {
  const BudgetScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final budgets = <(String, double, double, Color)>[];

    return Scaffold(
      appBar: AppBar(title: const Text('Budget Management')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [FC.deepBurgundy, FC.darkBurgundy], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Monthly Budget', style: fcText(14, FontWeight.w500, Colors.white70)),
                  const SizedBox(height: 8),
                  Text('EGP 0', style: fcText(28, FontWeight.w700, Colors.white)),
                  const SizedBox(height: 4),
                  Text('of EGP 0', style: fcText(13, FontWeight.w400, Colors.white60)),
                  const SizedBox(height: 12),
                  ClipRRect(borderRadius: BorderRadius.circular(8), child: LinearProgressIndicator(value: 0, minHeight: 8, backgroundColor: Colors.white24, valueColor: const AlwaysStoppedAnimation(FC.mutedGold))),
                ],
              ),
            ),
            const SizedBox(height: 20),
            Text('Category Budgets', style: fcText(16, FontWeight.w700, FC.darkCharcoal)),
            const SizedBox(height: 12),
            ...budgets.map((b) => Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(14)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(b.$1, style: fcText(14, FontWeight.w600, FC.darkCharcoal)),
                      Text('EGP ${b.$3.toStringAsFixed(0)} / ${b.$2.toStringAsFixed(0)}', style: fcText(13, FontWeight.w500, FC.neutralGray)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(borderRadius: BorderRadius.circular(6), child: LinearProgressIndicator(value: (b.$3 / b.$2).clamp(0.0, 1.0), minHeight: 6, backgroundColor: FC.lightGray, valueColor: AlwaysStoppedAnimation(b.$4))),
                ],
              ),
            )),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: FC.deepBurgundy,
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }
}
