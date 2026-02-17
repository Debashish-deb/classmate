from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from .deps import get_current_user
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import secrets
import logging
import json
import uuid
from ..services.transcription_service import TranscriptionService
from ..services.notes_service import NotesService
from ..services.cloud_storage_service import cloud_storage_service
from ..services.calendar_service import calendar_service
from ..services.encryption_service import encryption_service
from ..database import get_db
from ..database.models import Session, TranscriptChunk, APIKey

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
router = APIRouter(prefix="/api/v1/public", tags=["public-api"])

class APIKeyManager:
    """Manages API keys for third-party integrations"""
    
    def __init__(self):
        self.rate_limits = {}  # Simple in-memory rate limiting
    
    def generate_api_key(self, user_id: str, app_name: str, permissions: List[str]) -> Dict[str, str]:
        """Generate a new API key"""
        try:
            api_key = f"cm_{secrets.token_urlsafe(32)}"
            key_id = str(uuid.uuid4())
            hashed_key, salt = encryption_service.hash_password(api_key)
            stored_hash = f"{salt}${hashed_key}"
            
            # Store in database
            with get_db() as db:
                api_key_record = APIKey(
                    id=key_id,
                    user_id=user_id,
                    app_name=app_name,
                    api_key_hash=stored_hash,
                    permissions=json.dumps(permissions),
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=365),
                    is_active=True
                )
                db.add(api_key_record)
                db.commit()
            
            return {
                "api_key": api_key,
                "key_id": key_id,
                "permissions": permissions,
                "expires_at": api_key_record.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate API key: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate API key")
    
    def validate_api_key(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
        """Validate API key and return user info"""
        try:
            if not credentials or not credentials.credentials:
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            api_key = credentials.credentials
            
            # Check rate limiting
            client_ip = "unknown"  # In production, get from request
            self._check_rate_limit(client_ip)
            
            # Validate API key in database
            with get_db() as db:
                now = datetime.utcnow()
                query = db.query(APIKey).filter(APIKey.is_active == True)
                query = query.filter((APIKey.expires_at == None) | (APIKey.expires_at > now))
                api_key_records = query.all()

                if not api_key_records:
                    raise HTTPException(status_code=401, detail="Invalid or expired API key")
                
                matched_record = None
                for record in api_key_records:
                    stored = record.api_key_hash or ""
                    salt = ""
                    hashed = stored
                    if "$" in stored:
                        parts = stored.split("$", 1)
                        salt = parts[0]
                        hashed = parts[1]
                    if encryption_service.verify_password(api_key, hashed, salt):
                        matched_record = record
                        break

                if not matched_record:
                    raise HTTPException(status_code=401, detail="Invalid API key")

                matched_record.last_used = datetime.utcnow()
                db.commit()
                
                return {
                    "user_id": matched_record.user_id,
                    "app_name": matched_record.app_name,
                    "permissions": json.loads(matched_record.permissions),
                    "key_id": matched_record.id
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    def _check_rate_limit(self, client_ip: str, limit: int = 1000, window: int = 3600):
        """Simple rate limiting"""
        now = datetime.utcnow()
        
        if client_ip not in self.rate_limits:
            self.rate_limits[client_ip] = []
        
        # Clean old requests
        self.rate_limits[client_ip] = [
            req_time for req_time in self.rate_limits[client_ip]
            if now - req_time < timedelta(seconds=window)
        ]
        
        # Check limit
        if len(self.rate_limits[client_ip]) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(window)}
            )
        
        # Add current request
        self.rate_limits[client_ip].append(now)

api_key_manager = APIKeyManager()

# API Endpoints
@router.post("/transcribe")
async def public_transcribe(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Public API for audio transcription"""
    try:
        # User is already verified via Firebase
        user_id = current_user.get("uid")
        
        # Validate request
        if "audio_url" not in request and "audio_data" not in request:
            raise HTTPException(status_code=400, detail="Audio URL or data required")
        
        # Offload to Celery worker check
        from ..tasks import process_transcription_task
        
        # Mocking session ID and path for the example
        session_id = str(uuid.uuid4())
        audio_path = request.get("audio_url", "mock_path")
        
        task = process_transcription_task.delay(session_id, audio_path)
        
        return JSONResponse(content={
            "message": "Transcription queued",
            "task_id": task.id,
            "session_id": session_id,
            "status": "processing"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public transcription failed: {e}")
        raise HTTPException(status_code=500, detail="Transcription failed")

@router.post("/generate-notes")
async def public_generate_notes(
    request: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Public API for AI note generation"""
    try:
        user_id = current_user.get("uid")
        
        if "transcript" not in request:
            raise HTTPException(status_code=400, detail="Transcript required")
        
        notes_service = NotesService()
        
        # Generate notes (mock implementation)
        result = {
            "summary": "This is a mock summary of the transcript",
            "key_points": [
                "Important point 1",
                "Important point 2",
                "Action item: Follow up on discussed topics"
            ],
            "action_items": [
                "Schedule follow-up meeting",
                "Review documentation"
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Public note generation failed: {e}")
        raise HTTPException(status_code=500, detail="Note generation failed")

@router.get("/sessions")
async def public_list_sessions(
    user_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Public API to list sessions"""
    try:
        # Check if user matches token
        token_uid = current_user.get("uid")
        if user_id and user_id != token_uid:
             raise HTTPException(status_code=403, detail="Access denied")
        
        target_user_id = user_id or token_uid
        
        with get_db() as db:
            query = db.query(Session).filter(Session.user_id == target_user_id)
            
            # Apply pagination
            sessions = query.offset(offset).limit(limit).all()
            
            # Convert to response format
            session_list = []
            for session in sessions:
                session_data = {
                    "id": session.id,
                    "title": session.title,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat() if session.end_time else None,
                    "duration": session.duration,
                    "status": session.status,
                    "created_at": session.created_at.isoformat()
                }
                session_list.append(session_data)
            
            return JSONResponse(content={
                "sessions": session_list,
                "total": len(session_list),
                "limit": limit,
                "offset": offset
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list sessions")

@router.get("/sessions/{session_id}/transcript")
async def public_get_transcript(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Public API to get session transcript"""
    try:
        token_uid = current_user.get("uid")

        with get_db() as db:
            # Get session
            session = db.query(Session).filter(Session.id == session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Check access
            if session.user_id != token_uid:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Get transcript chunks
            chunks = db.query(TranscriptChunk).filter(
                TranscriptChunk.session_id == session_id
            ).order_by(TranscriptChunk.chunk_index).all()
            
            # Build transcript
            transcript = {
                "session_id": session_id,
                "title": session.title,
                "full_transcript": session.transcript or "",
                "chunks": [
                    {
                        "chunk_index": chunk.chunk_index,
                        "text": chunk.text,
                        "timestamp": chunk.timestamp.isoformat(),
                        "confidence": chunk.confidence,
                        "speaker": chunk.speaker
                    }
                    for chunk in chunks
                ],
                "summary": session.summary,
                "key_points": json.loads(session.key_points) if session.key_points else [],
                "action_items": json.loads(session.action_items) if session.action_items else []
            }
            
            return JSONResponse(content=transcript)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}")
        raise HTTPException(status_code=500, detail="Failed to get transcript")

@router.post("/webhooks/transcription-complete")
async def transcription_webhook(
    webhook_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Webhook endpoint for transcription completion notifications"""
    try:
        # User is verified
        user_id = current_user.get("uid")
        
        # Process webhook data
        session_id = webhook_data.get("session_id")
        status = webhook_data.get("status")
        transcript = webhook_data.get("transcript")
        
        if not session_id or not status:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Log webhook
        logger.info(f"Transcription webhook received: session={session_id}, status={status}")
        
        # In a real implementation, this would:
        # 1. Update the session status
        # 2. Send notifications
        # 3. Trigger additional processing
        
        return JSONResponse(content={
            "status": "received",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

@router.get("/usage")
async def get_api_usage(
    current_user: dict = Depends(get_current_user)
):
    """Get API usage statistics"""
    try:
        user_id = current_user.get("uid")
        
        # Mock usage data
        usage_data = {
            "period": "current_month",
            "requests": {
                "transcribe": 150,
                "generate_notes": 75,
                "read_sessions": 300,
                "read_transcripts": 200
            },
            "limits": {
                "requests_per_month": 10000,
                "storage_gb": 100,
                "transcription_minutes": 500
            },
            "storage_used": "2.5 GB",
            "transcription_minutes_used": 45
        }
        
        return JSONResponse(content=usage_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get usage")

@router.get("/health")
async def public_api_health():
    """Health check for public API"""
    return JSONResponse(content={
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "transcribe": "/api/v1/public/transcribe",
            "generate_notes": "/api/v1/public/generate-notes",
            "sessions": "/api/v1/public/sessions",
            "webhooks": "/api/v1/public/webhooks/transcription-complete"
        }
    })
