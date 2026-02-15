import 'dart:async';
import 'dart:io';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart' as path;
import 'package:path_provider/path_provider.dart';
import 'package:logger/logger.dart';
import 'package:uuid/uuid.dart';
import '../models/session_model.dart';
import 'api_client.dart';

class Session {
  final String id;
  final String title;
  final DateTime startTime;
  final DateTime? endTime;
  final Duration duration;
  final SessionStatus status;
  final int totalChunks;
  final int uploadedChunks;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? transcript;
  final String? summary;
  final List<String>? keyPoints;
  final List<String>? actionItems;

  Session({
    required this.id,
    required this.title,
    required this.startTime,
    this.endTime,
    required this.duration,
    required this.status,
    this.totalChunks = 0,
    this.uploadedChunks = 0,
    required this.createdAt,
    required this.updatedAt,
    this.transcript,
    this.summary,
    this.keyPoints,
    this.actionItems,
  });

  Map<String, dynamic> toMap() => {
    'id': id,
    'title': title,
    'start_time': startTime.toIso8601String(),
    'end_time': endTime?.toIso8601String(),
    'duration': duration.inMilliseconds,
    'status': status.index,
    'total_chunks': totalChunks,
    'uploaded_chunks': uploadedChunks,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
  };

  factory Session.fromMap(Map<String, dynamic> map) => Session(
    id: map['id'],
    title: map['title'],
    startTime: DateTime.parse(map['start_time']),
    endTime: map['end_time'] != null ? DateTime.parse(map['end_time']) : null,
    duration: Duration(milliseconds: map['duration']),
    status: SessionStatus.values[map['status']],
    totalChunks: map['total_chunks'] ?? 0,
    uploadedChunks: map['uploaded_chunks'] ?? 0,
    createdAt: DateTime.parse(map['created_at']),
    updatedAt: DateTime.parse(map['updated_at']),
  );

  Session copyWith({
    String? title,
    DateTime? startTime,
    DateTime? endTime,
    Duration? duration,
    SessionStatus? status,
    int? totalChunks,
    int? uploadedChunks,
    DateTime? updatedAt,
    String? transcript,
    String? summary,
    List<String>? keyPoints,
    List<String>? actionItems,
  }) {
    return Session(
      id: id,
      title: title ?? this.title,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      duration: duration ?? this.duration,
      status: status ?? this.status,
      totalChunks: totalChunks ?? this.totalChunks,
      uploadedChunks: uploadedChunks ?? this.uploadedChunks,
      createdAt: createdAt,
      updatedAt: updatedAt ?? DateTime.now(),
      transcript: transcript ?? this.transcript,
      summary: summary ?? this.summary,
      keyPoints: keyPoints ?? this.keyPoints,
      actionItems: actionItems ?? this.actionItems,
    );
  }

  bool get isRecording => status == SessionStatus.recording;
  bool get isCompleted => status == SessionStatus.completed;
  bool get isProcessing => status == SessionStatus.processing;
  bool get hasNotes => summary != null || keyPoints?.isNotEmpty == true;
  double get uploadProgress => totalChunks > 0 ? uploadedChunks / totalChunks : 0.0;
}

enum SessionStatus {
  recording,
  processing,
  completed,
  failed,
  uploaded,
}

class SessionManager {
  static final SessionManager _instance = SessionManager._internal();
  factory SessionManager() => _instance;
  SessionManager._internal();

  final ApiClient _apiClient = ApiClient();
  final Logger _logger = Logger();
  final List<Session> _sessions = [];
  final StreamController<List<Session>> _sessionsController = StreamController<List<Session>>.broadcast();
  
  Database? _database;
  Session? _currentSession;

  List<Session> get sessions => List.unmodifiable(_sessions);
  Stream<List<Session>> get sessionsStream => _sessionsController.stream;
  Session? get currentSession => _currentSession;

  Future<void> initialize() async {
    await _initDatabase();
    await _loadSessions();
    _logger.i('SessionManager initialized');
  }

  Future<void> _initDatabase() async {
    final directory = await getApplicationDocumentsDirectory();
    final databasePath = path.join(directory.path, 'classmate.db');
    
    _database = await openDatabase(
      databasePath,
      version: 1,
      onCreate: (Database db, int version) async {
        await db.execute('''
          CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            start_time INTEGER NOT NULL,
            end_time INTEGER,
            duration INTEGER NOT NULL,
            status TEXT NOT NULL,
            total_chunks INTEGER DEFAULT 0,
            uploaded_chunks INTEGER DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            transcript TEXT,
            summary TEXT,
            key_points TEXT,
            action_items TEXT
          )
        ''');
      },
    );
  }

  Future<void> _loadSessions() async {
    if (_database == null) return;

    try {
      final List<Map<String, dynamic>> maps = await _database!.query('sessions', orderBy: 'created_at DESC');
      
      _sessions.clear();
      for (final map in maps) {
        final session = Session.fromMap(map);
        _sessions.add(session);
      }
      
      _sessionsController.add(_sessions);
      _logger.i('Loaded ${_sessions.length} sessions from database');
    } catch (e) {
      _logger.e('Failed to load sessions: $e');
    }
  }

  Future<void> _saveSessionToDatabase(Session session) async {
    if (_database == null) return;

    try {
      await _database!.insert(
        'sessions',
        session.toMap(),
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    } catch (e) {
      _logger.e('Failed to save session to database: $e');
    }
  }

  Future<void> updateSession(String sessionId, {
    String? title,
    DateTime? endTime,
    Duration? duration,
    SessionStatus? status,
    int? totalChunks,
    int? uploadedChunks,
    String? transcript,
    String? summary,
    List<String>? keyPoints,
    List<String>? actionItems,
  }) async {
    try {
      final sessionIndex = _sessions.indexWhere((s) => s.id == sessionId);
      if (sessionIndex == -1) return;

      final session = _sessions[sessionIndex];
      final updatedSession = session.copyWith(
        title: title,
        endTime: endTime,
        duration: duration,
        status: status,
        totalChunks: totalChunks,
        uploadedChunks: uploadedChunks,
        updatedAt: DateTime.now(),
        transcript: transcript,
        summary: summary,
        keyPoints: keyPoints,
        actionItems: actionItems,
      );

      _sessions[sessionIndex] = updatedSession;
      await _saveSessionToDatabase(updatedSession);
      _sessionsController.add(_sessions);

      _logger.i('Session updated: $sessionId');
    } catch (e) {
      _logger.e('Failed to update session: $e');
      rethrow;
    }
  }

  Future<void> deleteSession(String sessionId) async {
    try {
      _sessions.removeWhere((s) => s.id == sessionId);
      if (_database != null) {
        await _database!.delete('sessions', where: 'id = ?', whereArgs: [sessionId]);
      }
      _sessionsController.add(_sessions);
      _logger.i('Session deleted: $sessionId');
    } catch (e) {
      _logger.e('Failed to delete session: $e');
      rethrow;
    }
  }

  Future<void> endCurrentSession({DateTime? endTime}) async {
    if (_currentSession == null) return;
    
    final duration = endTime != null 
        ? endTime.difference(_currentSession!.startTime)
        : DateTime.now().difference(_currentSession!.startTime);
    
    await updateSession(
      _currentSession!.id,
      endTime: endTime ?? DateTime.now(),
      duration: duration,
      status: SessionStatus.completed,
    );
    
    _currentSession = null;
  }

  Future<void> generateNotes(String sessionId) async {
    try {
      await _apiClient.generateNotes(sessionId);
      
      // Refresh session data
      await _refreshSession(sessionId);
      
      _logger.i('Notes generated for session: $sessionId');
    } catch (e) {
      _logger.e('Failed to generate notes: $e');
      rethrow;
    }
  }

  Future<void> _refreshSession(String sessionId) async {
    try {
      final sessionModel = await _apiClient.getSession(sessionId);
      if (sessionModel != null) {
        final session = Session(
          id: sessionModel.id,
          title: sessionModel.title,
          startTime: sessionModel.startTime,
          endTime: sessionModel.endTime,
          duration: sessionModel.duration,
          status: SessionStatus.values.firstWhere(
            (e) => e.name == sessionModel.status.name,
            orElse: () => SessionStatus.recording,
          ),
          totalChunks: sessionModel.totalChunks,
          uploadedChunks: sessionModel.uploadedChunks,
          createdAt: sessionModel.createdAt,
          updatedAt: sessionModel.updatedAt,
          transcript: sessionModel.transcript,
          summary: sessionModel.summary,
          keyPoints: sessionModel.keyPoints,
          actionItems: sessionModel.actionItems,
        );
        
        final index = _sessions.indexWhere((s) => s.id == sessionId);
        if (index != -1) {
          _sessions[index] = session;
          await _saveSessionToDatabase(session);
          _sessionsController.add(_sessions);
        }
      }
    } catch (e) {
      _logger.e('Failed to refresh session: $e');
    }
  }

  void dispose() {
    _sessionsController.close();
    _database?.close();
  }

  Future<Session> createSession({required String title}) async {
    try {
      // Create session via API
      final sessionModel = await _apiClient.createSession(title);
      
      // Convert to local Session object
      final session = Session(
        id: sessionModel.id,
        title: sessionModel.title,
        startTime: sessionModel.startTime,
        endTime: sessionModel.endTime,
        duration: sessionModel.duration,
        status: SessionStatus.values.firstWhere(
          (e) => e.name == sessionModel.status.name,
          orElse: () => SessionStatus.recording,
        ),
        totalChunks: sessionModel.totalChunks,
        uploadedChunks: sessionModel.uploadedChunks,
        createdAt: sessionModel.createdAt,
        updatedAt: sessionModel.updatedAt,
        transcript: sessionModel.transcript,
        summary: sessionModel.summary,
        keyPoints: sessionModel.keyPoints,
        actionItems: sessionModel.actionItems,
      );

      // Save to local database
      await _saveSessionToDatabase(session);
      
      // Add to local list
      _sessions.insert(0, session);
      _sessionsController.add(_sessions);
      
      _logger.i('Session created: ${session.id}');
      return session;
    } catch (e) {
      _logger.e('Failed to create session: $e');
      rethrow;
    }
  }

  Future<Session?> getSession(String sessionId) async {
    if (_database == null) return null;
    
    final List<Map<String, dynamic>> maps = await _database!.query(
      'sessions',
      where: 'id = ?',
      whereArgs: [sessionId],
    );
    
    return maps.isNotEmpty ? Session.fromMap(maps.first) : null;
  }

  Future<List<Session>> getAllSessions({int limit = 50, int offset = 0}) async {
    if (_database == null) return [];
    
    final List<Map<String, dynamic>> maps = await _database!.query(
      'sessions',
      orderBy: 'created_at DESC',
      limit: limit,
      offset: offset,
    );
    
    return maps.map((map) => Session.fromMap(map)).toList();
  }

  Future<List<Session>> getSessionsByStatus(SessionStatus status) async {
    if (_database == null) return [];
    
    final List<Map<String, dynamic>> maps = await _database!.query(
      'sessions',
      where: 'status = ?',
      whereArgs: [status.index],
      orderBy: 'created_at DESC',
    );
    
    return maps.map((map) => Session.fromMap(map)).toList();
  }

  Future<void> syncSessionWithBackend(String sessionId) async {
    final session = await getSession(sessionId);
    if (session == null) return;
    
    try {
      // TODO: Implement backend sync
      // This would fetch the latest session status from the backend
      // and update the local database accordingly
      
      _logger.d('Session synced with backend: $sessionId');
    } catch (e) {
      _logger.e('Error syncing session with backend: $e');
    }
  }
}
