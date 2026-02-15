import 'dart:io';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import '../models/session_model.dart';

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal() {
    _initializeDio();
  }

  final Dio _dio = Dio();
  final Logger _logger = Logger();
  
  static const String _baseUrl = 'http://localhost:8000/api/v1';

  void _initializeDio() {
    _dio.options.baseUrl = _baseUrl;
    _dio.options.connectTimeout = const Duration(seconds: 30);
    _dio.options.receiveTimeout = const Duration(seconds: 30);
    _dio.options.headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Add logging for debugging
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (object) => _logger.d(object.toString()),
    ));
  }

  // Session Management
  Future<SessionModel> createSession(String title, {String? userId}) async {
    try {
      final response = await _dio.post('/sessions', data: {
        'title': title,
        'user_id': userId ?? 'default_user',
      });

      if (response.statusCode == 201) {
        return SessionModel.fromJson(response.data);
      } else {
        throw Exception('Failed to create session: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('Error creating session: $e');
      throw Exception('Failed to create session: ${e.message}');
    }
  }

  Future<SessionModel?> getSession(String sessionId) async {
    try {
      final response = await _dio.get('/sessions/$sessionId');

      if (response.statusCode == 200) {
        return SessionModel.fromJson(response.data);
      } else {
        return null;
      }
    } on DioException catch (e) {
      _logger.e('Error getting session: $e');
      return null;
    }
  }

  Future<List<SessionModel>> listSessions({String? userId}) async {
    try {
      final response = await _dio.get('/sessions', queryParameters: {
        if (userId != null) 'user_id': userId,
      });

      if (response.statusCode == 200) {
        final List<dynamic> data = response.data;
        return data.map((json) => SessionModel.fromJson(json)).toList();
      } else {
        throw Exception('Failed to list sessions: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('Error listing sessions: $e');
      throw Exception('Failed to list sessions: ${e.message}');
    }
  }

  // Audio Upload and Transcription
  Future<bool> uploadAudioChunk(String sessionId, int chunkIndex, String audioFilePath) async {
    try {
      final file = File(audioFilePath);
      if (!file.existsSync()) {
        throw Exception('Audio file not found: $audioFilePath');
      }

      final formData = FormData.fromMap({
        'session_id': sessionId,
        'chunk_index': chunkIndex,
        'audio_file': await MultipartFile.fromFile(
          audioFilePath,
          filename: 'chunk_$chunkIndex.wav',
        ),
      });

      final response = await _dio.post('/upload', data: formData);

      if (response.statusCode == 200) {
        _logger.i('Audio chunk uploaded successfully');
        return true;
      } else {
        throw Exception('Failed to upload audio: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('Error uploading audio: $e');
      throw Exception('Failed to upload audio: ${e.message}');
    }
  }

  Future<String?> getTranscript(String sessionId) async {
    try {
      final response = await _dio.get('/transcript/$sessionId');

      if (response.statusCode == 200) {
        return response.data['transcript'];
      } else {
        return null;
      }
    } on DioException catch (e) {
      _logger.e('Error getting transcript: $e');
      return null;
    }
  }

  // Notes Generation
  Future<bool> generateNotes(String sessionId) async {
    try {
      // First get the transcript
      final transcript = await getTranscript(sessionId);
      if (transcript == null || transcript.isEmpty) {
        throw Exception('No transcript available for notes generation');
      }

      final response = await _dio.post('/generate-notes', data: {
        'session_id': sessionId,
        'transcript': transcript,
        'include_summary': true,
        'include_key_points': true,
        'include_action_items': true,
      });

      if (response.statusCode == 200) {
        _logger.i('Notes generated successfully');
        return true;
      } else {
        throw Exception('Failed to generate notes: ${response.statusCode}');
      }
    } on DioException catch (e) {
      _logger.e('Error generating notes: $e');
      throw Exception('Failed to generate notes: ${e.message}');
    }
  }

  // Health Check
  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get('/health');
      return response.statusCode == 200;
    } catch (e) {
      _logger.e('Health check failed: $e');
      return false;
    }
  }
}
