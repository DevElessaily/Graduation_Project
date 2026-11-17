import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class Api {
  static String _baseUrl = 'http://10.0.2.2:8000';

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString('backend_base_url') ?? _baseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    _baseUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('backend_base_url', _baseUrl);
  }

  static String get baseUrl => _baseUrl;

  static Uri _uri(String path) => Uri.parse('$_baseUrl$path');

  static Future<bool> health() async {
    try {
      final r = await http.get(_uri('/health')).timeout(const Duration(seconds: 5));
      return r.statusCode == 200;
    } catch (_) { return false; }
  }

  static Future<Map<String, dynamic>> parseSms(String sender, String message) async {
    final r = await http.post(_uri('/api/sms/parse'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'sender': sender, 'message': message}),
    ).timeout(const Duration(seconds: 15));
    return jsonDecode(r.body) as Map<String, dynamic>;
  }

  static Future<List<Map<String, dynamic>>> fetchSmsHistory({int limit = 100}) async {
    final r = await http.get(_uri('/api/sms/history?limit=$limit')).timeout(const Duration(seconds: 15));
    final data = jsonDecode(r.body);
    return (data as List).cast<Map<String, dynamic>>();
  }

  static Future<Map<String, dynamic>> syncSms(List<Map<String, dynamic>> items) async {
    final r = await http.post(_uri('/api/sms/bulk'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'items': items}),
    ).timeout(const Duration(seconds: 60));
    return jsonDecode(r.body) as Map<String, dynamic>;
  }
}
EOF