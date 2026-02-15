from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from .models import SessionStatus

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./classmate.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

class Session(declarative_base):
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

class TranscriptChunk(declarative_base):
    __tablename__ = "transcript_chunks"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    confidence = Column(Float, nullable=True)
    speaker = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Session.metadata.create_all(engine)
    print("Database tables created successfully")
