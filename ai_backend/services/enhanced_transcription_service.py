import os
import asyncio
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import numpy as np
import librosa
from pydub import AudioSegment
from fastapi import HTTPException
from ..database.models import Session, TranscriptChunk
from ..database import get_db
from ..shared_contracts.models import TranscriptionRequest, TranscriptionResponse

logger = logging.getLogger(__name__)

class EnhancedTranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if self._check_cuda() else "cpu"
        self.sample_rate = 16000
        self.channels = 1
        self.load_model()

    def _check_cuda(self) -> bool:
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def load_model(self):
        """Load the enhanced Whisper model with speaker diarization"""
        try:
            import whisper
            # Use large model for better accuracy
            model_name = "openai/whisper-large-v3"
            self.model = whisper.load_model(model_name, device=self.device)
            
            # Load speaker diarization model
            try:
                from pyannote.audio import Pipeline
                self.diarization_pipeline = Pipeline(
                    "speaker_diarization",
                    device=self.device
                )
                logger.info("Speaker diarization pipeline loaded")
            except ImportError:
                logger.warning("Speaker diarization not available")
                self.diarization_pipeline = None
            
            logger.info(f"Enhanced Whisper model loaded on {self.device}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    async def transcribe_audio_enhanced(self, request: TranscriptionRequest) -> TranscriptionResponse:
        """Enhanced transcription with speaker identification and noise reduction"""
        try:
            # Check if file exists
            if not os.path.exists(request.audio_file_path):
                raise HTTPException(status_code=404, detail="Audio file not found")

            # Load and preprocess audio
            audio = self._load_and_preprocess_audio(request.audio_file_path)
            
            # Enhanced transcription with speaker diarization
            result = self.model.transcribe(
                audio,
                language="english",  # Auto-detect language
                task="transcribe",
                word_timestamps=True,
                fp16=torch.float16 if self.device == "cuda" else torch.float32,
                verbose=False
            )

            # Extract text and timestamps
            text = result["text"].strip()
            segments = result.get("segments", [])
            
            # Calculate confidence
            confidence = self._calculate_confidence(segments)
            
            # Speaker identification
            speakers = await self._identify_speakers(request.audio_file_path, segments)
            
            # Combine with speaker information
            enhanced_text = self._combine_speakers_with_text(text, speakers, segments)
            
            # Save to database
            chunk_id = str(uuid.uuid4())
            with get_db() as db:
                # Create transcript chunk with speaker info
                transcript_chunk = TranscriptChunk(
                    id=chunk_id,
                    session_id=request.session_id,
                    chunk_index=request.chunk_index,
                    text=enhanced_text,
                    timestamp=datetime.utcnow(),
                    confidence=confidence,
                    speaker=self._get_primary_speaker(speakers)
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
                text=enhanced_text,
                timestamp=datetime.utcnow(),
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Enhanced transcription failed: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    def _load_and_preprocess_audio(self, audio_file_path: str) -> np.ndarray:
        """Load and preprocess audio with noise reduction"""
        try:
            # Load audio file
            audio = AudioSegment.from_file(audio_file_path)
            
            # Convert to mono if needed
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample to 16kHz if needed
            if audio.frame_rate != self.sample_rate:
                audio = audio.set_frame_rate(self.sample_rate)
            
            # Apply noise reduction
            audio = self._reduce_noise(audio)
            
            # Normalize audio
            audio = self._normalize_audio(audio)
            
            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())
            
            if samples.dtype != np.float32:
                samples = samples.astype(np.float32)
            
            return samples
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Audio preprocessing failed: {str(e)}")

    def _reduce_noise(self, audio: AudioSegment) -> AudioSegment:
        """Apply noise reduction to audio"""
        try:
            # Simple noise reduction using spectral subtraction
            samples = np.array(audio.get_array_of_samples())
            
            # Apply high-pass filter to reduce low-frequency noise
            from scipy import signal
            sos = signal.butter(4, 100, [0.01, 0.04, 0.59, 0.98], [0.98, 0.59, 0.04, 0.01], 'high')
            filtered_samples = signal.lfilter(sos, samples)
            
            # Convert back to AudioSegment
            filtered_audio = AudioSegment(
                filtered_samples.tobytes(),
                frame_rate=audio.frame_rate,
                channels=audio.channels
            )
            
            return filtered_audio
            
        except ImportError:
            logger.warning("scipy not available, skipping noise reduction")
            return audio
        except Exception as e:
            logger.error(f"Noise reduction failed: {e}")
            return audio

    def _normalize_audio(self, audio: AudioSegment) -> AudioSegment:
        """Normalize audio to consistent volume level"""
        try:
            # Normalize to -20 dBFS
            target_dBFS = -20
            change_in_dBFS = target_dBFS - audio.dBFS
            return audio + change_in_dBFS
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return audio

    def _calculate_confidence(self, segments: List[Dict]) -> Optional[float]:
        """Calculate transcription confidence from segments"""
        try:
            confidences = [seg.get("avg_logprob", 0.0) for seg in segments if "avg_logprob" in seg]
            if confidences:
                # Convert log probabilities to confidence scores (0-1)
                confidence_scores = [np.exp(conf) for conf in confidences]
                return min(max(confidence_scores), 1.0)
            return None
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return None

    async def _identify_speakers(self, audio_file_path: str, segments: List[Dict]) -> List[Dict]:
        """Identify speakers using diarization"""
        if not self.diarization_pipeline:
            return []
        
        try:
            # Load audio for diarization
            diarization = self.diarization_pipeline(audio_file_path)
            
            speakers = []
            for segment in segments:
                start_time = segment.get("start", 0)
                end_time = segment.get("end", 0)
                
                # Find speaker for this segment
                speaker_label = self._get_speaker_at_time(diarization, start_time)
                
                speakers.append({
                    "start": start_time,
                    "end": end_time,
                    "speaker": speaker_label,
                    "text": segment.get("text", "")
                })
            
            return speakers
            
        except Exception as e:
            logger.error(f"Speaker identification failed: {e}")
            return []

    def _get_speaker_at_time(self, diarization, timestamp: float) -> str:
        """Get speaker label at specific timestamp"""
        try:
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if turn.start <= timestamp <= turn.end:
                    return speaker
            return "Unknown"
        except Exception:
            return "Unknown"

    def _get_primary_speaker(self, speakers: List[Dict]) -> str:
        """Determine the primary speaker"""
        if not speakers:
            return "Unknown"
        
        # Count speaker occurrences
        speaker_counts = {}
        for speaker in speakers:
            label = speaker.get("speaker", "Unknown")
            speaker_counts[label] = speaker_counts.get(label, 0) + 1
        
        # Return speaker with most occurrences
        return max(speaker_counts, key=speaker_counts.get) if speaker_counts else "Unknown"

    def _combine_speakers_with_text(self, text: str, speakers: List[Dict], segments: List[Dict]) -> str:
        """Combine speaker information with transcribed text"""
        if not speakers:
            return text
        
        enhanced_text = []
        current_speaker = None
        
        for speaker in speakers:
            if speaker["speaker"] != current_speaker:
                enhanced_text.append(f"\n\n[{speaker['speaker'].upper()}]:")
                current_speaker = speaker["speaker"]
            
            enhanced_text.append(speaker["text"])
        
        return "\n".join(enhanced_text).strip()

    async def get_session_transcript(self, session_id: str) -> str:
        """Get full transcript with speaker information"""
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
            logger.error(f"Failed to get transcript: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")

    async def get_session_speakers(self, session_id: str) -> List[str]:
        """Get list of speakers for a session"""
        try:
            with get_db() as db:
                chunks = db.query(TranscriptChunk).filter(
                    TranscriptChunk.session_id == session_id
                ).all()
                
                speakers = set()
                for chunk in chunks:
                    if chunk.speaker:
                        speakers.add(chunk.speaker)
                
                return list(speakers)

        except Exception as e:
            logger.error(f"Failed to get speakers: {e}")
            return []

    async def get_speaker_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get speaking time statistics for each speaker"""
        try:
            with get_db() as db:
                chunks = db.query(TranscriptChunk).filter(
                    TranscriptChunk.session_id == session_id
                ).all()
                
                speaker_stats = {}
                for chunk in chunks:
                    speaker = chunk.speaker or "Unknown"
                    if speaker not in speaker_stats:
                        speaker_stats[speaker] = {
                            "word_count": 0,
                            "duration": 0.0,
                            "segments": 0
                        }
                    
                    # Count words in segment
                    word_count = len(chunk.text.split())
                    speaker_stats[speaker]["word_count"] += word_count
                    speaker_stats[speaker]["segments"] += 1
                    
                    # Estimate duration (rough calculation)
                    speaker_stats[speaker]["duration"] += 30.0  # 30 seconds per chunk
                
                return speaker_stats

        except Exception as e:
            logger.error(f"Failed to get speaker statistics: {e}")
            return {}
