import 'dart:async';
import 'dart:io';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import 'package:logger/logger.dart';

class RecordingService {
  static final RecordingService _instance = RecordingService._internal();
  factory RecordingService() => _instance;
  RecordingService._internal();

  final Logger _logger = Logger();
  
  bool _isRecording = false;
  String? _currentSessionId;
  int _chunkCount = 0;

  bool get isRecording => _isRecording;
  String? get currentSessionId => _currentSessionId;

  Future<bool> requestPermissions() async {
    final microphonePermission = await Permission.microphone.request();
    final storagePermission = await Permission.storage.request();
    
    return microphonePermission == PermissionStatus.granted &&
           storagePermission == PermissionStatus.granted;
  }

  Future<String> _getSessionDirectory() async {
    final directory = await getApplicationDocumentsDirectory();
    final sessionDir = Directory('${directory.path}/sessions/$_currentSessionId');
    await sessionDir.create(recursive: true);
    return sessionDir.path;
  }

  Future<String> _generateChunkPath() async {
    final sessionDir = await _getSessionDirectory();
    final chunkNumber = (_chunkCount++).toString().padLeft(4, '0');
    return '$sessionDir/chunk_$chunkNumber.wav';
  }

  Future<void> startRecording({String? sessionId}) async {
    if (_isRecording) {
      _logger.w('Recording already in progress');
      return;
    }

    final hasPermissions = await requestPermissions();
    if (!hasPermissions) {
      throw Exception('Microphone and storage permissions required');
    }

    _currentSessionId = sessionId ?? DateTime.now().millisecondsSinceEpoch.toString();
    _chunkCount = 0;
    _isRecording = true;

    _logger.i('Recording started for session: $_currentSessionId');
  }

  Future<void> stopRecording() async {
    if (!_isRecording) return;

    _isRecording = false;
    _logger.i('Recording stopped for session: $_currentSessionId');
    _currentSessionId = null;
  }

  void dispose() {
    // Cleanup if needed
  }
}
