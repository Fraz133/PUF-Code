import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class ApiService {
  // Cloud URL for production authentication
  static const String baseUrl = 'http://212.28.191.52:8001';

  /// Health check - is the server running and how many tags are registered?
  static Future<Map<String, dynamic>> getHealthStatus() async {
    try {
      final response = await http.get(
        Uri.parse(baseUrl),
      ).timeout(const Duration(seconds: 5));
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
      return {'status': 'offline', 'registered_tags_count': 0};
    } catch (e) {
      return {'status': 'offline', 'registered_tags_count': 0};
    }
  }

  /// Get list of registered tags
  static Future<List<String>> getRegisteredTags() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/tags'),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final tags = data['registered_tags'] as List? ?? [];
        return tags.map((t) => t['tag_id'] as String).toList();
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  /// Main authentication call
  /// Sends: image file + tag_id + time_node
  /// Returns: JSON response with PASS/FAIL and all 3 key scores
  static Future<Map<String, dynamic>> authenticate({
    required File imageFile,
    String? tagId,
    required double timeNode,
  }) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/authenticate'),
      );

      // Add form fields
      if (tagId != null && tagId.isNotEmpty) {
        request.fields['tag_id'] = tagId;
      }
      request.fields['time_node'] = timeNode.toString();

      // Add the image file
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      // Send the request
      final streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
      );
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final errorBody = json.decode(response.body);
        throw Exception(errorBody['detail'] ?? 'Authentication failed');
      }
    } catch (e) {
      throw Exception('Connection error: $e');
    }
  }
}
