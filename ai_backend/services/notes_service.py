import json
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException
from ..database.models import Session
from ..database import get_db
from ..shared_contracts.models import NotesGenerationRequest, NotesResponse
from ..agents import NotesOrchestrator

class NotesService:
    def __init__(self):
        # Could initialize AI model here for note generation
        self.orchestrator = NotesOrchestrator()

    async def generate_notes(self, request: NotesGenerationRequest) -> NotesResponse:
        """Generate AI-powered notes from transcript"""
        try:
            # Get the full transcript
            with get_db() as db:
                session = db.query(Session).filter(Session.id == request.session_id).first()
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                transcript = session.transcript or ""
                
                if not transcript:
                    raise HTTPException(status_code=400, detail="No transcript available for this session")

                agent_result = await self.orchestrator.run(
                    session_id=request.session_id,
                    transcript=transcript,
                    include_summary=request.include_summary,
                    include_key_points=request.include_key_points,
                    include_action_items=request.include_action_items,
                )

                summary = agent_result.get("summary")
                key_points = agent_result.get("key_points") or []
                action_items = agent_result.get("action_items") or []

                # Update session with generated notes
                session.summary = summary
                session.key_points = json.dumps(key_points) if key_points else None
                session.action_items = json.dumps(action_items) if action_items else None
                session.status = "completed"
                session.updated_at = datetime.utcnow()
                db.commit()

                return NotesResponse(
                    session_id=request.session_id,
                    summary=summary or "",
                    key_points=key_points,
                    action_items=action_items,
                    generated_at=datetime.utcnow(),
                    evaluation=agent_result.get("evaluation"),
                    agent_meta=agent_result.get("agent_meta"),
                    memory=agent_result.get("memory"),
                )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Notes generation failed: {str(e)}")
