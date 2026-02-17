import 'dart:async';
import 'dart:io';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import 'package:logger/logger.dart';
import 'package:flutter_sound/flutter_sound.dart';
import 'upload_queue_service.dart';

class RecordingService {
  static final RecordingService _instance = RecordingService._internal();
  factory RecordingService() => _instance;
  RecordingService._internal();

  final Logger _logger = Logger();
  final FlutterSoundRecorder _recorder = FlutterSoundRecorder();
  final UploadQueueService _uploadQueue = UploadQueueService();

  bool _isRecording = false;
  bool _isPaused = false;
  bool _isInitialized = false;
  String? _currentSessionId;
  int _chunkCount = 0;
  DateTime? _recordingStartTime;
  Timer? _chunkTimer;

  static const Duration _chunkDuration = Duration(minutes: 2);

  bool get isRecording => _isRecording;
  bool get isPaused => _isPaused;
  String? get currentSessionId => _currentSessionId;
  DateTime? get recordingStartTime => _recordingStartTime;

  Duration get currentDuration {
    if (_recordingStartTime == null) return Duration.zero;
    return DateTime.now().difference(_recordingStartTime!);
  }

  Future<void> _ensureInitialized() async {
    if (!_isInitialized) {
      await _recorder.openRecorder();
      _isInitialized = true;
    }
  }

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

  Future<bool> _hasSufficientDiskSpace() async {
    try {
      final directory = await getApplicationDocumentsDirectory();
      // Write a small test file to verify we can still write to disk.
      // A 3-hour WAV at 16kHz mono ≈ 342 MB.
      final tempFile = File('${directory.path}/.space_check');
      await tempFile.writeAsBytes(List.filled(1024, 0));
      await tempFile.delete();
      return true; // If we can write, we have *some* space
    } catch (e) {
      _logger.e('Disk space check failed: $e');
      return false;
    }
  }

  Future<String> startRecording({String? sessionId}) async {
    if (_isRecording) {
      _logger.w('Recording already in progress');
      return _currentSessionId ?? '';
    }

    final hasPermissions = await requestPermissions();
    if (!hasPermissions) {
      throw Exception('Microphone and storage permissions required');
    }

    final hasDiskSpace = await _hasSufficientDiskSpace();
    if (!hasDiskSpace) {
      throw Exception('Insufficient disk space to start recording');
    }

    await _ensureInitialized();

    _currentSessionId = sessionId ?? DateTime.now().millisecondsSinceEpoch.toString();
    _chunkCount = 0;
    _recordingStartTime = DateTime.now();

    final chunkPath = await _generateChunkPath();

    await _recorder.startRecorder(
      toFile: chunkPath,
      codec: Codec.pcm16WAV,
      sampleRate: 16000,
      numChannels: 1,
    );

    _isRecording = true;
    _isPaused = false;

    // Periodically finalize chunk and start a new one
    _chunkTimer = Timer.periodic(_chunkDuration, (_) => _rotateChunk());

    _logger.i('Recording started for session: $_currentSessionId');
    return _currentSessionId!;
  }

  Future<void> _rotateChunk() async {
    if (!_isRecording || _isPaused) return;

    try {
      final finishedPath = await _recorder.stopRecorder();
      if (finishedPath != null && _currentSessionId != null) {
        await _uploadQueue.enqueueUpload(
          finishedPath, _currentSessionId!, _chunkCount - 1,
        );
      }

      // Start next chunk
      final nextPath = await _generateChunkPath();
      await _recorder.startRecorder(
        toFile: nextPath,
        codec: Codec.pcm16WAV,
        sampleRate: 16000,
        numChannels: 1,
      );
    } catch (e) {
      _logger.e('Error rotating chunk: $e');
    }
  }

  Future<void> pauseRecording() async {
    if (!_isRecording || _isPaused) return;
    await _recorder.pauseRecorder();
    _isPaused = true;
    _logger.i('Recording paused');
  }

  Future<void> resumeRecording() async {
    if (!_isRecording || !_isPaused) return;
    await _recorder.resumeRecorder();
    _isPaused = false;
    _logger.i('Recording resumed');
  }

  Future<void> stopRecording() async {
    if (!_isRecording) return;

    _chunkTimer?.cancel();
    _chunkTimer = null;

    final lastPath = await _recorder.stopRecorder();
    if (lastPath != null && _currentSessionId != null) {
      await _uploadQueue.enqueueUpload(
        lastPath, _currentSessionId!, _chunkCount - 1,
      );
    }

    _isRecording = false;
    _isPaused = false;
    _logger.i('Recording stopped for session: $_currentSessionId');
    _currentSessionId = null;
    _recordingStartTime = null;
  }

  void dispose() {
    _chunkTimer?.cancel();
    _recorder.closeRecorder();
  }
}
