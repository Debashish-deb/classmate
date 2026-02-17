import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:logger/logger.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

class UploadTask {
  final String id;
  final String filePath;
  final String sessionId;
  final int chunkIndex;
  final DateTime createdAt;
  int retryCount;
  DateTime? nextRetryAt;

  UploadTask({
    required this.filePath,
    required this.sessionId,
    required this.chunkIndex,
    this.retryCount = 0,
  }) : id = const Uuid().v4(),
       createdAt = DateTime.now(),
       nextRetryAt = null;

  Map<String, dynamic> toJson() => {
    'id': id,
    'filePath': filePath,
    'sessionId': sessionId,
    'chunkIndex': chunkIndex,
    'createdAt': createdAt.toIso8601String(),
    'retryCount': retryCount,
    'nextRetryAt': nextRetryAt?.toIso8601String(),
  };

  factory UploadTask.fromJson(Map<String, dynamic> json) {
    return UploadTask(
      filePath: json['filePath'],
      sessionId: json['sessionId'],
      chunkIndex: json['chunkIndex'],
      retryCount: json['retryCount'] ?? 0,
    );
  }
}

class UploadQueueService {
  static final UploadQueueService _instance = UploadQueueService._internal();
  factory UploadQueueService() => _instance;
  UploadQueueService._internal();

  final Dio _dio = Dio();
  final Logger _logger = Logger();
  final List<UploadTask> _queue = [];
  final StreamController<UploadTask> _uploadStatusController = 
      StreamController<UploadTask>.broadcast();
  
  Timer? _processTimer;
  bool _isProcessing = false;
  
  static const int _maxRetries = 5;
  static const Duration _baseRetryDelay = Duration(seconds: 5);
  static const Duration _processInterval = Duration(seconds: 10);

  Stream<UploadTask> get uploadStatusStream => _uploadStatusController.stream;
  List<UploadTask> get pendingUploads => _queue.where((task) => 
      task.retryCount < _maxRetries).toList();

  Future<void> initialize() async {
    await _loadQueue();
    _startProcessing();
    _logger.i('Upload queue service initialized');
  }

  Future<void> enqueueUpload(String filePath, String sessionId, int chunkIndex) async {
    // Deduplication: skip if same session+chunk is already queued
    final alreadyQueued = _queue.any(
      (t) => t.sessionId == sessionId && t.chunkIndex == chunkIndex,
    );
    if (alreadyQueued) {
      _logger.d('Duplicate upload skipped: session=$sessionId chunk=$chunkIndex');
      return;
    }

    final task = UploadTask(
      filePath: filePath,
      sessionId: sessionId,
      chunkIndex: chunkIndex,
    );

    _queue.add(task);
    await _saveQueue();
    
    _logger.d('Upload enqueued: ${task.id}');
    _uploadStatusController.add(task);
  }

  void _startProcessing() {
    _processTimer?.cancel();
    _processTimer = Timer.periodic(_processInterval, (_) => _processQueue());
  }

  Future<void> _processQueue() async {
    if (_isProcessing || _queue.isEmpty) return;

    _isProcessing = true;
    
    try {
      final readyTasks = _queue.where((task) => 
          task.retryCount < _maxRetries &&
          (task.nextRetryAt == null || task.nextRetryAt!.isBefore(DateTime.now()))
      ).toList();

      for (final task in readyTasks.take(3)) { // Process up to 3 concurrently
        unawaited(_processUpload(task));
      }
    } finally {
      _isProcessing = false;
    }
  }

  Future<void> _processUpload(UploadTask task) async {
    try {
      final file = File(task.filePath);
      if (!await file.exists()) {
        _logger.w('File not found, removing task: ${task.id}');
        _queue.remove(task);
        await _saveQueue();
        return;
      }

      final formData = FormData.fromMap({
        'audio': await MultipartFile.fromFile(
          task.filePath,
          filename: 'chunk_${task.chunkIndex}.wav',
        ),
        'session_id': task.sessionId,
        'chunk_index': task.chunkIndex,
      });

      final response = await _dio.post(
        'http://localhost:8000/api/v1/upload',
        data: formData,
        options: Options(
          headers: {'Content-Type': 'multipart/form-data'},
          sendTimeout: const Duration(minutes: 5),
          receiveTimeout: const Duration(minutes: 5),
        ),
      );

      if (response.statusCode == 200) {
        _logger.i('Upload successful: ${task.id}');
        _queue.remove(task);
        await _saveQueue();
        _uploadStatusController.add(task);
      } else {
        throw Exception('Upload failed with status: ${response.statusCode}');
      }
    } catch (e) {
      _logger.e('Upload error for ${task.id}: $e');
      await _handleUploadFailure(task);
    }
  }

  Future<void> _handleUploadFailure(UploadTask task) async {
    task.retryCount++;
    
    if (task.retryCount >= _maxRetries) {
      _logger.e('Max retries exceeded for task: ${task.id}');
      _queue.remove(task);
    } else {
      // Exponential backoff
      final delay = _baseRetryDelay * (1 << (task.retryCount - 1));
      task.nextRetryAt = DateTime.now().add(delay);
      _logger.d('Scheduling retry for ${task.id} in $delay');
    }
    
    await _saveQueue();
    _uploadStatusController.add(task);
  }

  Future<void> _loadQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final queueJson = prefs.getString('upload_queue');
      
      if (queueJson != null && queueJson.isNotEmpty) {
        final List<dynamic> decoded = jsonDecode(queueJson);
        _queue.clear();
        for (final item in decoded) {
          try {
            _queue.add(UploadTask.fromJson(item as Map<String, dynamic>));
          } catch (e) {
            _logger.w('Skipping corrupt queue entry: $e');
          }
        }
        _logger.d('Loaded ${_queue.length} tasks from storage');
      }
    } catch (e) {
      _logger.e('Error loading upload queue: $e');
    }
  }

  Future<void> _saveQueue() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonList = _queue.map((t) => t.toJson()).toList();
      await prefs.setString('upload_queue', jsonEncode(jsonList));
      _logger.d('Saved ${_queue.length} tasks to storage');
    } catch (e) {
      _logger.e('Error saving upload queue: $e');
    }
  }

  Future<void> retryFailedUploads() async {
    for (final task in _queue) {
      if (task.retryCount < _maxRetries) {
        task.retryCount = 0;
        task.nextRetryAt = null;
      }
    }
    await _saveQueue();
    await _processQueue();
  }

  void dispose() {
    _processTimer?.cancel();
    _uploadStatusController.close();
  }
}

// Helper function for fire-and-forget async calls
void unawaited(Future<void> future) {
  // Intentionally unimplemented - just prevents warning
}
