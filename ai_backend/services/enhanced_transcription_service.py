import os
import asyncio
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import re
import time
import numpy as np
import librosa
from pydub import AudioSegment
from fastapi import HTTPException
from ..database.models import Session, TranscriptChunk
from ..database import get_db
from ..shared_contracts.models import (
    TranscriptionRequest,
    TranscriptionResponse,
    SegmentTimestamp,
    WordTimestamp,
)
from ..agents.memory_store import SQLiteMemoryStore
from ..agents.transcription_post_agents import PostTranscriptionChain

logger = logging.getLogger(__name__)

class EnhancedTranscriptionService:
    def __init__(self):
        self.model = None
        self.device = "cuda" if self._check_cuda() else "cpu"
        self.sample_rate = 16000
        self.channels = 1
        self._session_memory: Dict[str, Dict[str, Any]] = {}
        self._memory_store = SQLiteMemoryStore()
        self._post_chain = PostTranscriptionChain()
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
            import torch
            
            # Use large model for better accuracy
            model_name = "large-v3"
            self.model = whisper.load_model(model_name, device=self.device)
            
            # Load speaker diarization model
            try:
                from pyannote.audio import Pipeline
                from pyannote.audio.pipelines.speaker_diarization import SpeakerDiarization
                hf_token = os.getenv("HF_TOKEN")
                try:
                    # Newer versions support `use_auth_token` (str | bool)
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=hf_token or None,
                    )
                except TypeError:
                    # Older versions don't accept `use_auth_token`
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                    )
                if torch.cuda.is_available():
                    self.diarization_pipeline.to(torch.device("cuda"))
                logger.info("Speaker diarization pipeline loaded")
            except Exception as e:
                logger.warning(f"Speaker diarization not available: {e}")
                self.diarization_pipeline = None
            
            logger.info(f"Enhanced Whisper model loaded on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    async def transcribe_audio_enhanced(self, request: TranscriptionRequest, language: str = None) -> TranscriptionResponse:
        """Enhanced transcription with speaker identification and noise reduction"""
        try:
            import torch

            started_at = time.time()

            # Check if file exists
            if not os.path.exists(request.audio_file_path):
                raise HTTPException(status_code=404, detail="Audio file not found")

            # Load and preprocess audio
            audio = self._load_and_preprocess_audio(request.audio_file_path)
            
            # Auto-detect language if not specified
            if language is None:
                # Use Whisper to detect language
                result_detect = self.model.transcribe(
                    audio,
                    task="language_detection",
                    fp16=torch.float16 if self.device == "cuda" else torch.float32
                )
                detected_language = result_detect.get("language", "en")
            else:
                detected_language = language
            
            # Enhanced transcription with speaker diarization
            result = self.model.transcribe(
                audio,
                language=detected_language,
                task="transcribe",
                word_timestamps=True,
                fp16=torch.float16 if self.device == "cuda" else torch.float32,
                verbose=False
            )

            # Extract text and timestamps
            raw_text = (result.get("text") or "").strip()
            segments = result.get("segments", [])
            
            # Calculate confidence
            confidence = self._calculate_confidence(segments)
            
            # Speaker identification
            speakers = await self._identify_speakers(request.audio_file_path, segments)

            # Combine with speaker information
            enhanced_text = self._combine_speakers_with_text(raw_text, speakers, segments)

            # Session-aware self-correction / normalization
            memory = self._get_session_memory(request.session_id)
            corrected_text, corrections = self._self_correct_text(
                text=enhanced_text,
                session_memory=memory,
            )

            # Update session pattern learning
            self._learn_session_patterns(
                session_memory=memory,
                segments=segments,
                corrected_text=corrected_text,
            )

            # Persist learned session memory (best-effort)
            try:
                self._memory_store.put_kv(request.session_id, "transcription_memory", memory)
            except Exception:
                pass

            # Build rich structured segments
            structured_segments = self._build_structured_segments(segments)

            # Multi-agent post-processing chain (cleanup, term consistency, confidence, speaker turn)
            primary_speaker = self._get_primary_speaker(speakers)
            chain_result = self._post_chain.run(
                text=corrected_text,
                confidence=confidence,
                primary_speaker=primary_speaker,
                learned_replacements=memory.get("replacements", {}),
            )
            if chain_result.corrections:
                corrections.extend(chain_result.corrections)
            corrected_text = chain_result.text
            
            # Save to database
            chunk_id = str(uuid.uuid4())
            with get_db() as db:
                # Create transcript chunk with speaker info
                transcript_chunk = TranscriptChunk(
                    id=chunk_id,
                    session_id=request.session_id,
                    chunk_index=request.chunk_index,
                    text=corrected_text,
                    timestamp=datetime.utcnow(),
                    confidence=confidence,
                    speaker=primary_speaker
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

            processing_time = time.time() - started_at

            return TranscriptionResponse(
                id=chunk_id,
                session_id=request.session_id,
                chunk_index=request.chunk_index,
                text=corrected_text,
                timestamp=datetime.utcnow(),
                confidence=confidence,
                speaker=primary_speaker,
                language=detected_language,
                processing_time=processing_time,
                segments=structured_segments,
                corrections=corrections,
                session_context={
                    "session_id": request.session_id,
                    "learned_replacements": memory.get("replacements", {}),
                    "top_terms": memory.get("top_terms", [])[:25],
                },
            )

        except Exception as e:
            logger.error(f"Enhanced transcription failed: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    def _get_session_memory(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._session_memory:
            loaded = None
            try:
                loaded = self._memory_store.get_kv(session_id, "transcription_memory")
            except Exception:
                loaded = None

            if isinstance(loaded, dict):
                self._session_memory[session_id] = loaded
            else:
                self._session_memory[session_id] = {
                    "replacements": {},
                    "term_counts": {},
                    "top_terms": [],
                }
        return self._session_memory[session_id]

    def _self_correct_text(self, text: str, session_memory: Dict[str, Any]) -> (str, List[Dict[str, Any]]):
        corrections: List[Dict[str, Any]] = []

        original = text

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", text).strip()
        if normalized != text:
            corrections.append({"type": "whitespace_normalization"})
            text = normalized

        # Remove trivial repeated adjacent words (e.g., "the the")
        dedup = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)
        if dedup != text:
            corrections.append({"type": "adjacent_word_dedup"})
            text = dedup

        # Apply session-learned replacements (pattern learning)
        replacements: Dict[str, str] = session_memory.get("replacements", {})
        for src, dst in replacements.items():
            if src and src in text and dst and dst != src:
                text = text.replace(src, dst)
                corrections.append({"type": "session_replacement", "from": src, "to": dst})

        # Basic punctuation fixes
        punct = re.sub(r"\s+([,.!?;:])", r"\1", text)
        if punct != text:
            corrections.append({"type": "punctuation_spacing"})
            text = punct

        if text != original and not corrections:
            corrections.append({"type": "generic_normalization"})

        return text, corrections

    def _learn_session_patterns(self, session_memory: Dict[str, Any], segments: List[Dict[str, Any]], corrected_text: str):
        # Update term counts from segment words if available; otherwise from text tokens.
        term_counts: Dict[str, int] = session_memory.get("term_counts", {})

        words: List[str] = []
        for seg in segments or []:
            for w in (seg.get("words") or []):
                token = (w.get("word") or "").strip()
                if token:
                    words.append(token)

        if not words:
            words = re.findall(r"[A-Za-z][A-Za-z0-9_\-']*", corrected_text)

        for token in words:
            key = token
            term_counts[key] = term_counts.get(key, 0) + 1

        # Recompute top terms
        top_terms = sorted(term_counts.items(), key=lambda kv: kv[1], reverse=True)
        session_memory["top_terms"] = [{"term": t, "count": c} for t, c in top_terms[:100]]
        session_memory["term_counts"] = term_counts

        # Very lightweight "pattern learning": if we frequently see a token in different casings,
        # prefer the most common casing.
        casing_map: Dict[str, Dict[str, int]] = session_memory.setdefault("_casing", {})
        for token in words:
            lower = token.lower()
            casing_map.setdefault(lower, {})[token] = casing_map.setdefault(lower, {}).get(token, 0) + 1

        replacements: Dict[str, str] = session_memory.get("replacements", {})
        for lower, variants in casing_map.items():
            if len(variants) <= 1:
                continue
            preferred = max(variants.items(), key=lambda kv: kv[1])[0]
            for variant in variants.keys():
                if variant != preferred and variant not in replacements:
                    replacements[variant] = preferred

        session_memory["replacements"] = replacements

    def _build_structured_segments(self, segments: List[Dict[str, Any]]) -> List[SegmentTimestamp]:
        structured: List[SegmentTimestamp] = []
        for seg in segments or []:
            words_payload = None
            if seg.get("words"):
                words_payload = []
                for w in seg.get("words") or []:
                    words_payload.append(
                        WordTimestamp(
                            word=(w.get("word") or "").strip(),
                            start=float(w.get("start", 0.0)),
                            end=float(w.get("end", 0.0)),
                            probability=w.get("probability"),
                        )
                    )

            structured.append(
                SegmentTimestamp(
                    id=seg.get("id"),
                    start=float(seg.get("start", 0.0)),
                    end=float(seg.get("end", 0.0)),
                    text=(seg.get("text") or "").strip(),
                    avg_logprob=seg.get("avg_logprob"),
                    no_speech_prob=seg.get("no_speech_prob"),
                    words=words_payload,
                )
            )
        return structured

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
        """Apply advanced noise reduction to audio"""
        try:
            # Convert to numpy array for processing
            samples = np.array(audio.get_array_of_samples()).astype(np.float32)
            
            # Normalize to [-1, 1] range
            samples = samples / np.max(np.abs(samples))
            
            # Apply spectral subtraction for noise reduction
            try:
                import librosa
                
                # Use librosa for advanced noise reduction
                # Estimate noise from the first 0.5 seconds
                noise_sample_length = int(0.5 * self.sample_rate)
                if len(samples) > noise_sample_length:
                    noise_sample = samples[:noise_sample_length]
                else:
                    noise_sample = samples
                
                # Compute noise profile
                noise_stft = librosa.stft(noise_sample)
                noise_magnitude = np.mean(np.abs(noise_stft), axis=1)
                
                # Apply noise reduction to the entire signal
                audio_stft = librosa.stft(samples)
                audio_magnitude = np.abs(audio_stft)
                audio_phase = np.angle(audio_stft)
                
                # Spectral subtraction
                alpha = 2.0  # Over-subtraction factor
                beta = 0.01  # Spectral floor factor
                
                # Create noise mask
                noise_mask = np.expand_dims(noise_magnitude, axis=1)
                enhanced_magnitude = audio_magnitude - alpha * noise_mask
                enhanced_magnitude = np.maximum(enhanced_magnitude, beta * audio_magnitude)
                
                # Reconstruct signal
                enhanced_stft = enhanced_magnitude * np.exp(1j * audio_phase)
                enhanced_samples = librosa.istft(enhanced_stft)
                
                # Convert back to AudioSegment
                enhanced_samples = (enhanced_samples * 32767).astype(np.int16)
                enhanced_audio = AudioSegment(
                    enhanced_samples.tobytes(),
                    frame_rate=self.sample_rate,
                    channels=1,
                    sample_width=2
                )
                
                return enhanced_audio
                
            except ImportError:
                logger.warning("librosa not available, using basic noise reduction")
                # Basic high-pass filter
                from scipy import signal
                sos = signal.butter(4, 80, 'high', fs=self.sample_rate, output='sos')
                filtered_samples = signal.sosfilt(sos, samples)
                
                # Convert back to AudioSegment
                filtered_samples = (filtered_samples * 32767).astype(np.int16)
                filtered_audio = AudioSegment(
                    filtered_samples.tobytes(),
                    frame_rate=self.sample_rate,
                    channels=1,
                    sample_width=2
                )
                
                return filtered_audio
            
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
