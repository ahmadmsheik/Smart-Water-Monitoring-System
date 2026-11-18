import 'dart:convert';
import 'package:http/http.dart' as http;
import '../api_config.dart';

class ApiService {
  static Future<Map<String, dynamic>> fetch(String endpoint) async {
    final response = await http.get(apiUri(endpoint));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to load $endpoint');
    }
  }
}
