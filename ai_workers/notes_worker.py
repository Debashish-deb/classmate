import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import logging
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    'notes_worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['notes_worker']
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./classmate.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False)

class NotesWorker:
    def __init__(self):
        pass
        
    async def generate_notes(self, session_id: str, transcript: str, 
                           include_summary: bool = True,
                           include_key_points: bool = True,
                           include_action_items: bool = True) -> Dict[str, Any]:
        """Generate AI-powered notes from transcript - simplified mock implementation"""
        try:
            # Mock notes generation - in production, use actual AI model
            notes = {
                "session_id": session_id,
                "summary": None,
                "key_points": [],
                "action_items": []
            }
            
            if include_summary:
                notes["summary"] = self._generate_mock_summary(transcript)
            
            if include_key_points:
                notes["key_points"] = self._extract_mock_key_points(transcript)
            
            if include_action_items:
                notes["action_items"] = self._extract_mock_action_items(transcript)
            
            # Save to database
            await self.save_notes_to_db(notes)
            
            logger.info(f"Notes generated for session {session_id}")
            return notes
            
        except Exception as e:
            logger.error(f"Notes generation failed: {e}")
            raise
    
    def _generate_mock_summary(self, transcript: str) -> str:
        """Generate a mock summary"""
        sentences = transcript.split('. ')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 2:
            return transcript
        
        # Take first few sentences as summary
        summary_sentences = sentences[:3]
        return '. '.join(summary_sentences)
    
    def _extract_mock_key_points(self, transcript: str) -> List[str]:
        """Extract mock key points"""
        key_points = []
        sentences = transcript.split('. ')
        
        important_keywords = [
            "important", "key", "main", "primary", "essential", "critical",
            "remember", "note", "pay attention", "focus on", "highlight"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if any(keyword in sentence for keyword in important_keywords):
                key_point = sentence.capitalize()
                if len(key_point) > 10:
                    key_points.append(key_point)
        
        return key_points[:5]  # Limit to top 5 key points
    
    def _extract_mock_action_items(self, transcript: str) -> List[str]:
        """Extract mock action items"""
        action_items = []
        sentences = transcript.split('. ')
        
        action_verbs = [
            "should", "must", "need to", "have to", "will", "can",
            "do", "make", "create", "implement", "complete", "finish"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if any(verb in sentence for verb in action_verbs):
                action_item = sentence.capitalize()
                if len(action_item) > 10:
                    action_items.append(action_item)
        
        return action_items[:5]  # Limit to top 5 action items
    
    async def save_notes_to_db(self, notes_data: Dict[str, Any]):
        """Save notes to database"""
        try:
            with SessionLocal() as db:
                # Update session with generated notes
                db.execute("""
                    UPDATE sessions 
                    SET summary = ?,
                        key_points = ?,
                        action_items = ?,
                        status = 'completed',
                        updated_at = ?
                    WHERE id = ?
                """, (
                    notes_data.get("summary"),
                    json.dumps(notes_data.get("key_points", [])),
                    json.dumps(notes_data.get("action_items", [])),
                    datetime.utcnow(),
                    notes_data["session_id"]
                ))
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to save notes to DB: {e}")
            raise

@celery_app.task(bind=True)
def generate_notes_task(self, session_id: str, transcript: str, 
                       include_summary: bool = True,
                       include_key_points: bool = True,
                       include_action_items: bool = True):
    """Celery task for notes generation"""
    worker = NotesWorker()
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            worker.generate_notes(
                session_id, transcript, include_summary, include_key_points, include_action_items
            )
        )
        
        return {
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Notes generation task failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        loop.close()

if __name__ == "__main__":
    # Test the worker
    worker = NotesWorker()
    
    # Test notes generation
    test_transcript = """
    This is an important meeting about the project timeline. We need to focus on the key deliverables.
    The main point is that we must complete the implementation by next month. Remember to document everything.
    We should create a comprehensive testing plan and implement proper error handling.
    """
    
    result = asyncio.run(
        worker.generate_notes("test_session", test_transcript)
    )
    print("Test notes generation result:", result)
