import json
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException
from ..database.models import Session
from ..database import get_db
from ..shared_contracts.models import NotesGenerationRequest, NotesResponse

class NotesService:
    def __init__(self):
        # Could initialize AI model here for note generation
        pass

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

            # Generate notes (simplified for now - in production, use actual AI model)
            summary = self._generate_summary(transcript) if request.include_summary else None
            key_points = self._extract_key_points(transcript) if request.include_key_points else []
            action_items = self._extract_action_items(transcript) if request.include_action_items else []

            # Update session with generated notes
            session.summary = summary
            session.key_points = json.dumps(key_points) if key_points else None
            session.action_items = json.dumps(action_items) if action_items else None
            session.status = "completed"
            session.updated_at = datetime.utcnow()
            db.commit()

            return NotesResponse(
                session_id=request.session_id,
                summary=summary,
                key_points=key_points,
                action_items=action_items
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Notes generation failed: {str(e)}")

    def _generate_summary(self, transcript: str) -> str:
        """Generate a summary of the transcript"""
        # Simplified summary generation - in production, use actual AI model
        sentences = transcript.split('. ')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 2:
            return transcript
        
        # Take first few sentences as summary
        summary_sentences = sentences[:3]
        return '. '.join(summary_sentences)

    def _extract_key_points(self, transcript: str) -> List[str]:
        """Extract key points from transcript"""
        # Simplified key point extraction - look for important keywords
        key_points = []
        sentences = transcript.split('. ')
        
        important_keywords = [
            "important", "key", "main", "primary", "essential", "critical",
            "remember", "note", "pay attention", "focus on", "highlight"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if any(keyword in sentence for keyword in important_keywords):
                # Clean up the sentence
                key_point = sentence.capitalize()
                if len(key_point) > 10:  # Only include meaningful points
                    key_points.append(key_point)
        
        return key_points[:5]  # Limit to top 5 key points

    def _extract_action_items(self, transcript: str) -> List[str]:
        """Extract action items from transcript"""
        # Simplified action item extraction - look for action verbs
        action_items = []
        sentences = transcript.split('. ')
        
        action_verbs = [
            "should", "must", "need to", "have to", "will", "can",
            "do", "make", "create", "implement", "complete", "finish"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip().lower()
            if any(verb in sentence for verb in action_verbs):
                # Clean up the sentence
                action_item = sentence.capitalize()
                if len(action_item) > 10:  # Only include meaningful items
                    action_items.append(action_item)
        
        return action_items[:5]  # Limit to top 5 action items
