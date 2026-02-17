from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SessionCreateRequest(BaseModel):
    title: str
    user_id: str

class SessionResponse(BaseModel):
    id: str
    title: str
    user_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    total_chunks: Optional[int] = None
    uploaded_chunks: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[str] = None
    action_items: Optional[str] = None

class TranscriptionRequest(BaseModel):
    session_id: str
    chunk_index: int = 0
    audio_file_path: str
    language: Optional[str] = None


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    probability: Optional[float] = None


class SegmentTimestamp(BaseModel):
    id: Optional[int] = None
    start: float
    end: float
    text: str
    avg_logprob: Optional[float] = None
    no_speech_prob: Optional[float] = None
    words: Optional[List[WordTimestamp]] = None

class TranscriptionResponse(BaseModel):
    # Backward-compatible core fields
    id: str
    session_id: str
    chunk_index: int
    text: str
    timestamp: datetime
    confidence: Optional[float] = None
    speaker: Optional[str] = None

    # Rich structured output (optional)
    language: Optional[str] = None
    processing_time: Optional[float] = None
    segments: Optional[List[SegmentTimestamp]] = None

    # Session-aware improvements (optional)
    corrections: Optional[List[Dict[str, Any]]] = None
    session_context: Optional[Dict[str, Any]] = None

class NotesGenerationRequest(BaseModel):
    session_id: str
    transcript: str
    user_preferences: Optional[dict] = None
    include_summary: bool = True
    include_key_points: bool = True
    include_action_items: bool = True

class NotesResponse(BaseModel):
    session_id: str
    summary: str
    key_points: List[str]
    action_items: List[str]
    generated_at: datetime
    evaluation: Optional[Dict[str, Any]] = None
    agent_meta: Optional[Dict[str, Any]] = None
    memory: Optional[Dict[str, Any]] = None

class UploadResponse(BaseModel):
    success: bool
    message: str
    chunk_id: Optional[str] = None
