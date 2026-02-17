import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List
import logging
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import pathlib

# Add ai_backend to path
sys.path.append(str(pathlib.Path(__file__).parent.parent / "ai_backend"))

from agents import NotesOrchestrator

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
        self.orchestrator = NotesOrchestrator()
        
    async def generate_notes(self, session_id: str, transcript: str, 
                           include_summary: bool = True,
                           include_key_points: bool = True,
                           include_action_items: bool = True) -> Dict[str, Any]:
        """Generate AI-powered notes using multi-agent orchestrator"""
        try:
            result = await self.orchestrator.run(
                session_id=session_id,
                transcript=transcript,
                include_summary=include_summary,
                include_key_points=include_key_points,
                include_action_items=include_action_items,
            )
            notes = {
                "session_id": session_id,
                "summary": result.get("summary"),
                "key_points": result.get("key_points", []),
                "action_items": result.get("action_items", []),
                "evaluation": result.get("evaluation"),
                "agent_meta": result.get("agent_meta"),
                "memory": result.get("memory"),
            }
            
            # Save to database
            await self.save_notes_to_db(notes)
            
            logger.info(f"Notes generated for session {session_id}")
            return notes
            
        except Exception as e:
            logger.error(f"Notes generation failed: {e}")
            raise
    
    
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
