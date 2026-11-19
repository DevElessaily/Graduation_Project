import 'package:flutter/material.dart';
import '../theme.dart';

class CoachScreen extends StatefulWidget {
  const CoachScreen({super.key});
  @override
  State<CoachScreen> createState() => _CoachScreenState();
}

class _CoachScreenState extends State<CoachScreen> {
  final _ctrl = TextEditingController();
  final List<Map<String, String>> _msgs = [
    {'role': 'assistant', 'text': 'Hello! I\'m your Financial Coach. Ask me about your spending, budget, or savings goals.'},
  ];

  void _send() {
    final text = _ctrl.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _msgs.add({'role': 'user', 'text': text});
      _msgs.add({'role': 'assistant', 'text': 'Based on your recent spending, you have EGP 1,200 remaining this month. Consider reducing dining out to reach your savings goal.'});
    });
    _ctrl.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Financial Coach')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _msgs.length,
              itemBuilder: (ctx, i) {
                final m = _msgs[i];
                final isUser = m['role'] == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(14),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    decoration: BoxDecoration(
                      color: isUser ? FC.deepBurgundy : FC.warmWhite,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [BoxShadow(color: FC.cardShadow, blurRadius: 4)],
                    ),
                    child: Text(m['text']!, style: fcText(14, FontWeight.w400, isUser ? Colors.white : FC.darkCharcoal, height: 1.4)),
                  ),
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(color: FC.warmWhite, border: Border(top: BorderSide(color: FC.divider))),
            child: Row(
              children: [
                Expanded(child: TextField(
                  controller: _ctrl,
                  decoration: InputDecoration(hintText: 'Ask about your finances...', border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none), filled: true, fillColor: FC.lightGray),
                  onSubmitted: (_) => _send(),
                )),
                const SizedBox(width: 8),
                CircleAvatar(backgroundColor: FC.deepBurgundy, child: IconButton(onPressed: _send, icon: const Icon(Icons.send, color: Colors.white, size: 20))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
