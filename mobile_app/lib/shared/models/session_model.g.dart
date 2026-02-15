// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'session_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SessionModel _$SessionModelFromJson(Map<String, dynamic> json) => SessionModel(
      id: json['id'] as String,
      title: json['title'] as String,
      startTime: DateTime.parse(json['startTime'] as String),
      endTime: json['endTime'] == null
          ? null
          : DateTime.parse(json['endTime'] as String),
      duration: Duration(microseconds: (json['duration'] as num).toInt()),
      status: $enumDecode(_$SessionStatusEnumMap, json['status']),
      totalChunks: (json['totalChunks'] as num?)?.toInt() ?? 0,
      uploadedChunks: (json['uploadedChunks'] as num?)?.toInt() ?? 0,
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: DateTime.parse(json['updatedAt'] as String),
      transcript: json['transcript'] as String?,
      summary: json['summary'] as String?,
      keyPoints: (json['keyPoints'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      actionItems: (json['actionItems'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$SessionModelToJson(SessionModel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'startTime': instance.startTime.toIso8601String(),
      'endTime': instance.endTime?.toIso8601String(),
      'duration': instance.duration.inMicroseconds,
      'status': _$SessionStatusEnumMap[instance.status]!,
      'totalChunks': instance.totalChunks,
      'uploadedChunks': instance.uploadedChunks,
      'createdAt': instance.createdAt.toIso8601String(),
      'updatedAt': instance.updatedAt.toIso8601String(),
      'transcript': instance.transcript,
      'summary': instance.summary,
      'keyPoints': instance.keyPoints,
      'actionItems': instance.actionItems,
    };

const _$SessionStatusEnumMap = {
  SessionStatus.recording: 'recording',
  SessionStatus.processing: 'processing',
  SessionStatus.completed: 'completed',
  SessionStatus.failed: 'failed',
  SessionStatus.uploaded: 'uploaded',
};

TranscriptChunk _$TranscriptChunkFromJson(Map<String, dynamic> json) =>
    TranscriptChunk(
      id: json['id'] as String,
      sessionId: json['sessionId'] as String,
      chunkIndex: (json['chunkIndex'] as num).toInt(),
      text: json['text'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      confidence: (json['confidence'] as num?)?.toDouble(),
      speaker: json['speaker'] as String?,
    );

Map<String, dynamic> _$TranscriptChunkToJson(TranscriptChunk instance) =>
    <String, dynamic>{
      'id': instance.id,
      'sessionId': instance.sessionId,
      'chunkIndex': instance.chunkIndex,
      'text': instance.text,
      'timestamp': instance.timestamp.toIso8601String(),
      'confidence': instance.confidence,
      'speaker': instance.speaker,
    };
