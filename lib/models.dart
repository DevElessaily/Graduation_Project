import 'package:flutter/material.dart';

class Transaction {
  final String id;
  final String merchant;
  final String category;
  final double amount;
  final String currency;
  final bool isIncome;
  final DateTime date;
  final String? description;

  const Transaction({
    required this.id,
    required this.merchant,
    required this.category,
    required this.amount,
    this.currency = 'EGP',
    required this.isIncome,
    required this.date,
    this.description,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) => Transaction(
    id: '${json['id'] ?? ''}',
    merchant: '${json['merchant'] ?? 'Unknown'}',
    category: '${json['category'] ?? 'Other'}',
    amount: double.tryParse('${json['amount'] ?? '0'}') ?? 0,
    currency: '${json['currency'] ?? 'EGP'}',
    isIncome: json['type'] == 'deposit',
    date: DateTime.tryParse('${json['transaction_date'] ?? ''}') ?? DateTime.now(),
    description: json['description'] as String?,
  );
}

class Budget {
  final String category;
  final double limit;
  final double spent;
  const Budget({required this.category, required this.limit, required this.spent});
  double get remaining => limit - spent;
  double get percent => limit > 0 ? (spent / limit).clamp(0.0, 1.0) : 0;
}

class Insight {
  final String title;
  final String message;
  final IconData icon;
  final Color color;
  const Insight({required this.title, required this.message, required this.icon, required this.color});
}

// Category icon mapping
IconData categoryIcon(String category) {
  switch (category.toLowerCase()) {
    case 'groceries': return Icons.shopping_cart_rounded;
    case 'restaurants': return Icons.restaurant_rounded;
    case 'transportation': return Icons.directions_car_rounded;
    case 'shopping': return Icons.shopping_bag_rounded;
    case 'utilities': return Icons.bolt_rounded;
    case 'healthcare': return Icons.local_hospital_rounded;
    case 'entertainment': return Icons.movie_rounded;
    case 'subscription': return Icons.subscriptions_rounded;
    case 'education': return Icons.school_rounded;
    case 'travel': return Icons.flight_rounded;
    case 'personal care': return Icons.spa_rounded;
    case 'transfer': return Icons.swap_horiz_rounded;
    case 'income': return Icons.account_balance_wallet_rounded;
    case 'cash withdrawal': return Icons.atm_rounded;
    case 'fees': return Icons.receipt_rounded;
    case 'refund': return Icons.replay_rounded;
    case 'bills': return Icons.receipt_long_rounded;
    case 'food': return Icons.fastfood_rounded;
    case 'transport': return Icons.directions_bus_rounded;
    case 'health': return Icons.medical_services_rounded;
    case 'salary': return Icons.payments_rounded;
    default: return Icons.category_rounded;
  }
}

Color categoryColor(String category) {
  switch (category.toLowerCase()) {
    case 'groceries': return const Color(0xFF279B70);
    case 'restaurants': return const Color(0xFFD9534F);
    case 'transportation': return const Color(0xFF5B8DEF);
    case 'shopping': return const Color(0xFFC6A15B);
    case 'utilities': return const Color(0xFF8B1538);
    case 'healthcare': return const Color(0xFFE8735A);
    case 'entertainment': return const Color(0xFF9B59B6);
    case 'subscription': return const Color(0xFF3498DB);
    case 'education': return const Color(0xFF1ABC9C);
    case 'travel': return const Color(0xFFF39C12);
    case 'personal care': return const Color(0xFFE91E63);
    case 'transfer': return const Color(0xFF641027);
    case 'income': return const Color(0xFF279B70);
    default: return const Color(0xFF858585);
  }
}
