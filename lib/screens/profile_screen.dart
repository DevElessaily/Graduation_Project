import 'package:flutter/material.dart';
import '../theme.dart';
import 'income_screen.dart';
import 'installment_screen.dart';
import 'budget_screen.dart';
import 'settings_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile & Settings')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // Profile header
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
              child: Row(
                children: [
                  CircleAvatar(radius: 36, backgroundColor: FC.lightBurgundy, child: Text('MA', style: fcText(20, FontWeight.w700, FC.deepBurgundy))),
                  const SizedBox(width: 16),
                  Expanded(child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Moaz Ahmed', style: fcText(18, FontWeight.w700, FC.darkCharcoal)),
                      Text('moaz@financialcoach.app', style: fcText(13, FontWeight.w400, FC.neutralGray)),
                    ],
                  )),
                  IconButton(onPressed: () {}, icon: const Icon(Icons.edit, color: FC.deepBurgundy)),
                ],
              ),
            ),
            const SizedBox(height: 16),
            // Settings sections
            _section('Account', [
              _tile(Icons.person_outline, 'Personal Information'),
              _tile(Icons.account_balance, 'Linked Accounts'),
              _tile(Icons.security, 'Security & Privacy'),
            ]),
            const SizedBox(height: 16),
            _section('Preferences', [
              _tile(Icons.language, 'Language (Arabic/English)'),
              _tile(Icons.notifications_outlined, 'Notifications'),
              _tile(Icons.dark_mode_outlined, 'Dark Mode'),
              _tile(Icons.link, 'Backend URL', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen()))),
            ]),
            const SizedBox(height: 16),
            _section('Financial', [
              _tile(Icons.account_balance_wallet, 'Income', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const IncomeScreen()))),
              _tile(Icons.calendar_month, 'Installments', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const InstallmentScreen()))),
              _tile(Icons.account_balance, 'Budget', onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const BudgetScreen()))),
            ]),
            const SizedBox(height: 16),
            _section('Data', [
              _tile(Icons.sync, 'SMS Sync Settings'),
              _tile(Icons.cloud_upload, 'Backup & Restore'),
              _tile(Icons.delete_outline, 'Clear Data'),
            ]),
            const SizedBox(height: 16),
            _section('About', [
              _tile(Icons.info_outline, 'About Financial Coach'),
              _tile(Icons.help_outline, 'Help & Support'),
              _tile(Icons.description_outlined, 'Terms & Privacy Policy'),
            ]),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: OutlinedButton(
                onPressed: () {},
                style: OutlinedButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)), side: const BorderSide(color: FC.softRed)),
                child: Text('Log Out', style: fcText(16, FontWeight.w600, FC.softRed)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _section(String title, List<Widget> tiles) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(padding: const EdgeInsets.only(left: 4, bottom: 8), child: Text(title, style: fcText(14, FontWeight.w600, FC.neutralGray))),
      Container(
        decoration: BoxDecoration(color: FC.warmWhite, borderRadius: BorderRadius.circular(16)),
        child: Column(children: tiles),
      ),
    ],
  );

  Widget _tile(IconData icon, String label, {VoidCallback? onTap}) => ListTile(
    leading: Icon(icon, color: FC.deepBurgundy),
    title: Text(label, style: fcText(14, FontWeight.w500, FC.darkCharcoal)),
    trailing: const Icon(Icons.chevron_right, color: FC.neutralGray),
    onTap: onTap ?? () {},
  );
}
