from fastapi import APIRouter, UploadFile, File, HTTPException, Form, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import uuid
import tempfile
from typing import List, Optional
from pydantic import BaseModel
from ..services.transcription_service import TranscriptionService
from ..services.notes_service import NotesService
from ..services.websocket_service import WebSocketService
from ..shared_contracts.models import (
    SessionCreateRequest, SessionResponse, TranscriptionRequest, 
    TranscriptionResponse, NotesGenerationRequest, NotesResponse,
    UploadResponse
)
from ..database.models import Session, TranscriptChunk
from ..database import get_db

router = APIRouter(prefix="/api/v1")

# Initialize services
transcription_service = TranscriptionService()
notes_service = NotesService()
websocket_service = WebSocketService()

class TranscriptionResponseWithMeta(BaseModel):
    response: TranscriptionResponse
    meta: Optional[Dict[str, Any]] = None

class NotesResponseWithMeta(BaseModel):
    response: NotesResponse
    meta: Optional[Dict[str, Any]] = None

@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new recording session"""
    try:
        with get_db() as db:
            session = Session(
                id=str(uuid.uuid4()),
                user_id=request.user_id,
                title=request.title,
                start_time=datetime.utcnow(),
                duration=0,
                status="recording",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(session)
            db.commit()
            
            return SessionResponse(
                id=session.id,
                title=session.title,
                user_id=session.user_id,
                start_time=session.start_time,
                end_time=session.end_time,
                duration=session.duration,
                status=session.status,
                total_chunks=session.total_chunks,
                uploaded_chunks=session.uploaded_chunks,
                created_at=session.created_at,
                updated_at=session.updated_at,
                transcript=session.transcript,
                summary=session.summary,
                key_points=session.key_points,
                action_items=session.action_items
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get a specific session"""
    try:
        with get_db() as db:
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            return SessionResponse(
                id=session.id,
                title=session.title,
                user_id=session.user_id,
                start_time=session.start_time,
                end_time=session.end_time,
                duration=session.duration,
                status=session.status,
                total_chunks=session.total_chunks,
                uploaded_chunks=session.uploaded_chunks,
                created_at=session.created_at,
                updated_at=session.updated_at,
                transcript=session.transcript,
                summary=session.summary,
                key_points=session.key_points,
                action_items=session.action_items
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(user_id: str = None):
    """List all sessions for a user"""
    try:
        with get_db() as db:
            query = db.query(Session)
            if user_id:
                query = query.filter(Session.user_id == user_id)
            sessions = query.order_by(Session.created_at.desc()).all()
            
            return [
                SessionResponse(
                    id=session.id,
                    title=session.title,
                    user_id=session.user_id,
                    start_time=session.start_time,
                    end_time=session.end_time,
                    duration=session.duration,
                    status=session.status,
                    total_chunks=session.total_chunks,
                    uploaded_chunks=session.uploaded_chunks,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    transcript=session.transcript,
                    summary=session.summary,
                    key_points=session.key_points,
                    action_items=session.action_items
                )
                for session in sessions
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.post("/transcribe")
async def transcribe_audio(request: TranscriptionRequest, include_meta: Optional[bool] = False):
    """Transcribe an audio chunk"""
    try:
        response = await transcription_service.transcribe_audio(request)
        if include_meta:
            return TranscriptionResponseWithMeta(
                response=response,
                meta={
                    "segments": getattr(response, "segments", None),
                    "corrections": getattr(response, "corrections", None),
                    "session_context": getattr(response, "session_context", None),
                    "language": getattr(response, "language", None),
                    "processing_time": getattr(response, "processing_time", None),
                }
            )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/generate-notes")
async def generate_notes(request: NotesGenerationRequest, include_meta: Optional[bool] = False):
    """Generate AI-powered notes from transcript"""
    try:
        response = await notes_service.generate_notes(request)
        if include_meta:
            return NotesResponseWithMeta(
                response=response,
                meta={
                    "evaluation": getattr(response, "evaluation", None),
                    "agent_meta": getattr(response, "agent_meta", None),
                    "memory": getattr(response, "memory", None),
                }
            )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes generation failed: {str(e)}")

@router.post("/upload")
async def upload_audio(
    session_id: str,
    chunk_index: int,
    audio_file: UploadFile = File(...),
):
    """Upload audio chunk for transcription"""
    try:
        # Validate file
        if not audio_file.filename:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        if not audio_file.filename.endswith(('.wav')):
            raise HTTPException(status_code=400, detail="Only WAV files are supported")
        
        # Create upload directory if it doesn't exist
        upload_dir = f"uploads/{session_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file temporarily
        file_path = f"{upload_dir}/chunk_{chunk_index:04d}.wav"
        with open(file_path, "wb") as buffer:
            content = await audio_file.read()
            buffer.write(content)
        
        # Update session chunk count
        with get_db() as db:
            session = db.query(Session).filter(Session.id == session_id).first()
            if session:
                session.total_chunks = max(session.total_chunks, chunk_index + 1)
                session.updated_at = datetime.utcnow()
                db.commit()
        
        # Trigger transcription
        transcription_request = TranscriptionRequest(
            session_id=session_id,
            chunk_index=chunk_index,
            audio_file_path=file_path
        )
        
        transcription_result = await transcription_service.transcribe_audio(transcription_request)
        
        # Clean up temporary file
        os.remove(file_path)
        
        return UploadResponse(
            success=True,
            message="Audio uploaded and transcription started",
            chunk_id=transcription_result.id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/transcript/{session_id}")
async def get_transcript(session_id: str):
    """Get full transcript for a session"""
    try:
        transcript = await transcription_service.get_session_transcript(session_id)
        return JSONResponse({"transcript": transcript})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")

@router.websocket("/ws/transcribe/{session_id}/{user_id}")
async def websocket_transcribe(websocket: WebSocket, session_id: str, user_id: str):
    """WebSocket endpoint for real-time transcription"""
    await websocket_service.handle_websocket_connection(websocket, session_id, user_id)
