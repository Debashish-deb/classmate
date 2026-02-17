import os
import asyncio
from datetime import datetime
from typing import Dict, Any
import logging
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import pathlib

# Add ai_backend to path
sys.path.append(str(pathlib.Path(__file__).parent.parent / "ai_backend"))

from services.enhanced_transcription_service import EnhancedTranscriptionService
from shared_contracts.models import TranscriptionRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    'transcription_worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['transcription_worker']
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./classmate.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

class TranscriptionWorker:
    def __init__(self):
        self.service = EnhancedTranscriptionService()
        
    
    async def transcribe_audio(self, audio_file_path: str, session_id: str, chunk_index: int) -> Dict[str, Any]:
        """Transcribe audio chunk - simplified mock implementation"""
        try:
            request = TranscriptionRequest(
                session_id=session_id,
                chunk_index=chunk_index,
                audio_file_path=audio_file_path
            )
            response = await self.service.transcribe_audio_enhanced(request)
            result = {
                "id": response.id,
                "session_id": response.session_id,
                "chunk_index": response.chunk_index,
                "text": response.text,
                "timestamp": response.timestamp.isoformat(),
                "confidence": response.confidence,
                "speaker": response.speaker,
                "language": response.language,
                "processing_time": response.processing_time,
                "segments": [s.model_dump() for s in (response.segments or [])],
                "corrections": response.corrections,
                "session_context": response.session_context,
            }
            
            # Save to database
            await self.save_transcription_to_db(result)
            
            logger.info(f"Transcription completed for session {session_id}, chunk {chunk_index}")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    async def save_transcription_to_db(self, transcription_data: Dict[str, Any]):
        """Save transcription to database"""
        try:
            with SessionLocal() as db:
                # Create transcript chunk record
                db.execute("""
                    INSERT INTO transcript_chunks 
                    (id, session_id, chunk_index, text, timestamp, confidence, speaker, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transcription_data["id"],
                    transcription_data["session_id"],
                    transcription_data["chunk_index"],
                    transcription_data["text"],
                    transcription_data["timestamp"],
                    transcription_data["confidence"],
                    transcription_data["speaker"],
                    datetime.utcnow()
                ))
                db.commit()
                
                # Update session uploaded_chunks count
                db.execute("""
                    UPDATE sessions 
                    SET uploaded_chunks = uploaded_chunks + 1,
                        updated_at = ?
                    WHERE id = ?
                """, (datetime.utcnow(), transcription_data["session_id"]))
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save transcription to DB: {e}")
            raise

@celery_app.task(bind=True)
def transcribe_audio_task(self, session_id: str, chunk_index: int, audio_file_path: str):
    """Celery task for audio transcription"""
    worker = TranscriptionWorker()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            worker.transcribe_audio(audio_file_path, session_id, chunk_index)
        )
        
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Transcription task failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        loop.close()

if __name__ == "__main__":
    # Test the worker
    worker = TranscriptionWorker()
    worker.load_model()
    
    # Test transcription
    result = asyncio.run(
        worker.transcribe_audio("test.wav", "test_session", 0)
    )
    print("Test transcription result:", result)
