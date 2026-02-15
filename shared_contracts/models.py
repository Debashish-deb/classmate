from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SessionStatus(str, Enum):
    recording = "recording"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    uploaded = "uploaded"

class SessionCreateRequest(BaseModel):
    title: str
    user_id: str

class SessionResponse(BaseModel):
    id: str
    title: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: int
    status: SessionStatus
    total_chunks: int = 0
    uploaded_chunks: int = 0
    created_at: datetime
    updated_at: datetime
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = []
    action_items: Optional[List[str]] = []

class TranscriptChunk(BaseModel):
    id: str
    session_id: str
    chunk_index: int
    text: str
    timestamp: datetime
    confidence: Optional[float] = None
    speaker: Optional[str] = None

class TranscriptionRequest(BaseModel):
    session_id: str
    chunk_index: int
    audio_file_path: str

class TranscriptionResponse(BaseModel):
    id: str
    session_id: str
    chunk_index: int
    text: str
    timestamp: datetime
    confidence: Optional[float] = None
    speaker: Optional[str] = None

class NotesGenerationRequest(BaseModel):
    session_id: str
    transcript: str
    include_summary: bool = True
    include_key_points: bool = True
    include_action_items: bool = True

class NotesResponse(BaseModel):
    session_id: str
    summary: Optional[str] = None
    key_points: Optional[List[str]] = []
    action_items: Optional[List[str]] = []

class UploadResponse(BaseModel):
    success: bool
    message: str
    chunk_id: Optional[str] = None
