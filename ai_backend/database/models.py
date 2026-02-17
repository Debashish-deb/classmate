from sqlalchemy import Column, String, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum

class SessionStatus(Enum):
    recording = "recording"
    processing = "processing"
    completed = "completed"
    failed = "failed"

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=False)  # in milliseconds
    status = Column(String, nullable=False, default=SessionStatus.recording)
    total_chunks = Column(Integer, default=0)
    uploaded_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)  # JSON string
    action_items = Column(Text, nullable=True)  # JSON string

class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    confidence = Column(Float, nullable=True)
    speaker = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
