import os
import tempfile
import uuid
from datetime import datetime
from typing import Optional
import whisper
import torch
import torchaudio
from fastapi import HTTPException
from ..database.models import Session, TranscriptChunk
from ..database import get_db
from ..shared_contracts.models import TranscriptionRequest, TranscriptionResponse

class TranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.load_model()

    def load_model(self):
        """Load the Whisper model"""
        try:
            # Use medium model for good balance of speed and accuracy
            model_name = "openai/whisper-medium"
            self.model = whisper.load_model(model_name, device=self.device)
            print(f"Whisper model loaded on {self.device}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load Whisper model: {str(e)}")

    async def transcribe_audio(self, request: TranscriptionRequest) -> TranscriptionResponse:
        """Transcribe audio chunk using Whisper"""
        try:
            # Check if file exists
            if not os.path.exists(request.audio_file_path):
                raise HTTPException(status_code=404, detail="Audio file not found")

            # Load and process audio
            audio = torchaudio.load(request.audio_file_path)
            
            # Resample to 16kHz if needed
            if audio.sample_rate != 16000:
                audio = torchaudio.transforms.Resample(orig_freq=audio.sample_rate, new_freq=16000)(audio)

            # Transcribe
            result = self.model.transcribe(
                audio.numpy(),
                language="english",  # Auto-detect language
                task="transcribe",
                word_timestamps=True,
                fp16=torch.float16 if self.device == "cuda" else torch.float32
            )

            # Extract text and timestamps
            text = result["text"].strip()
            segments = result.get("segments", [])
            
            # Calculate confidence (average of segment confidences)
            confidence = None
            if segments:
                confidences = [seg.get("avg_logprob", 0.0) for seg in segments if "avg_logprob" in seg]
                confidence = sum(confidences) / len(confidences) if confidences else None

            # Save to database
            chunk_id = str(uuid.uuid4())
            with get_db() as db:
                # Create transcript chunk
                transcript_chunk = TranscriptChunk(
                    id=chunk_id,
                    session_id=request.session_id,
                    chunk_index=request.chunk_index,
                    text=text,
                    timestamp=datetime.utcnow(),
                    confidence=confidence
                )
                db.add(transcript_chunk)
                db.commit()

                # Update session
                session = db.query(Session).filter(Session.id == request.session_id).first()
                if session:
                    session.uploaded_chunks += 1
                    session.updated_at = datetime.utcnow()
                    if session.uploaded_chunks >= session.total_chunks:
                        session.status = "completed"
                    db.commit()

            return TranscriptionResponse(
                id=chunk_id,
                session_id=request.session_id,
                chunk_index=request.chunk_index,
                text=text,
                timestamp=datetime.utcnow(),
                confidence=confidence
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    async def get_session_transcript(self, session_id: str) -> str:
        """Get full transcript for a session"""
        try:
            with get_db() as db:
                chunks = db.query(TranscriptChunk).filter(
                    TranscriptChunk.session_id == session_id
                ).order_by(TranscriptChunk.chunk_index).all()
                
                if not chunks:
                    return ""
                
                # Combine all chunks
                transcript = "\n\n".join([chunk.text for chunk in chunks])
                return transcript

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")
