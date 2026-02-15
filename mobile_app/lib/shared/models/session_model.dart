import 'package:json_annotation/json_annotation.dart';

part 'session_model.g.dart';

@JsonSerializable()
class SessionModel {
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

  SessionModel({
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

  factory SessionModel.fromJson(Map<String, dynamic> json) =>
      _$SessionModelFromJson(json);

  Map<String, dynamic> toJson() => _$SessionModelToJson(this);

  SessionModel copyWith({
    String? id,
    String? title,
    DateTime? startTime,
    DateTime? endTime,
    Duration? duration,
    SessionStatus? status,
    int? totalChunks,
    int? uploadedChunks,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? transcript,
    String? summary,
    List<String>? keyPoints,
    List<String>? actionItems,
  }) {
    return SessionModel(
      id: id ?? this.id,
      title: title ?? this.title,
      startTime: startTime ?? this.startTime,
      endTime: endTime ?? this.endTime,
      duration: duration ?? this.duration,
      status: status ?? this.status,
      totalChunks: totalChunks ?? this.totalChunks,
      uploadedChunks: uploadedChunks ?? this.uploadedChunks,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? DateTime.now(),
      transcript: transcript ?? this.transcript,
      summary: summary ?? this.summary,
      keyPoints: keyPoints ?? this.keyPoints,
      actionItems: actionItems ?? this.actionItems,
    );
  }

  double get uploadProgress => totalChunks > 0 ? uploadedChunks / totalChunks : 0.0;
  
  bool get isCompleted => status == SessionStatus.completed;
  bool get isProcessing => status == SessionStatus.processing;
  bool get isRecording => status == SessionStatus.recording;
  bool get hasNotes => summary != null || keyPoints?.isNotEmpty == true;
}

enum SessionStatus {
  @JsonValue('recording')
  recording,
  @JsonValue('processing')
  processing,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
  @JsonValue('uploaded')
  uploaded,
}

@JsonSerializable()
class TranscriptChunk {
  final String id;
  final String sessionId;
  final int chunkIndex;
  final String text;
  final DateTime timestamp;
  final double? confidence;
  final String? speaker;

  TranscriptChunk({
    required this.id,
    required this.sessionId,
    required this.chunkIndex,
    required this.text,
    required this.timestamp,
    this.confidence,
    this.speaker,
  });

  factory TranscriptChunk.fromJson(Map<String, dynamic> json) =>
      _$TranscriptChunkFromJson(json);

  Map<String, dynamic> toJson() => _$TranscriptChunkToJson(this);
}
