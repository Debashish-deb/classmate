import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid
import base64
import io
import wave
import numpy as np
from .enhanced_transcription_service import EnhancedTranscriptionService

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time transcription"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self.transcription_service = EnhancedTranscriptionService()
        
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        
        self.active_connections[connection_id] = websocket
        
        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(connection_id)
        
        logger.info(f"WebSocket connected: {connection_id} for session {session_id}")
        
        # Send acknowledgment
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "connection_id": connection_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        return connection_id
    
    def disconnect(self, connection_id: str, session_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                # Connection might be dead, remove it
                self.disconnect(connection_id, "")
    
    async def broadcast_to_session(self, message: str, session_id: str):
        """Broadcast message to all connections in a session"""
        if session_id in self.session_connections:
            disconnected = []
            for connection_id in self.session_connections[session_id]:
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    try:
                        await websocket.send_text(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {connection_id}: {e}")
                        disconnected.append(connection_id)
                else:
                    disconnected.append(connection_id)
            
            # Clean up dead connections
            for connection_id in disconnected:
                self.disconnect(connection_id, session_id)
    
    async def process_audio_chunk(self, connection_id: str, session_id: str, audio_data: str, chunk_index: int):
        """Process incoming audio chunk and return transcription"""
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            # Convert to WAV format in memory
            audio_buffer = io.BytesIO()
            with wave.open(audio_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)  # 16kHz
                wav_file.writeframes(audio_bytes)
            
            # Save temporarily for transcription
            temp_file_path = f"temp_audio_{session_id}_{chunk_index}.wav"
            with open(temp_file_path, 'wb') as f:
                f.write(audio_buffer.getvalue())
            
            # Process with enhanced transcription service
            from ..shared_contracts.models import TranscriptionRequest
            transcription_request = TranscriptionRequest(
                session_id=session_id,
                chunk_index=chunk_index,
                audio_file_path=temp_file_path
            )
            
            result = await self.transcription_service.transcribe_audio_enhanced(transcription_request)
            
            # Clean up temporary file
            import os
            os.remove(temp_file_path)
            
            # Send transcription result back to client
            response = {
                "type": "transcription_result",
                "connection_id": connection_id,
                "session_id": session_id,
                "chunk_index": chunk_index,
                "text": result.text,
                "confidence": result.confidence,
                "timestamp": result.timestamp.isoformat(),
                "speaker": getattr(result, 'speaker', None),
                "language": getattr(result, 'language', None),
                "processing_time": getattr(result, 'processing_time', None),
                "segments": [s.model_dump() for s in (getattr(result, 'segments', None) or [])],
                "corrections": getattr(result, 'corrections', None),
                "session_context": getattr(result, 'session_context', None),
            }
            
            await self.send_personal_message(json.dumps(response), connection_id)
            
            # Broadcast to other connections in the session
            await self.broadcast_to_session(json.dumps(response), session_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            error_response = {
                "type": "error",
                "connection_id": connection_id,
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.send_personal_message(json.dumps(error_response), connection_id)
    
    async def get_session_transcript(self, session_id: str, connection_id: str):
        """Get full transcript for a session"""
        try:
            transcript = await self.transcription_service.get_session_transcript(session_id)
            speakers = await self.transcription_service.get_session_speakers(session_id)
            speaker_stats = await self.transcription_service.get_speaker_statistics(session_id)
            
            response = {
                "type": "session_transcript",
                "connection_id": connection_id,
                "session_id": session_id,
                "transcript": transcript,
                "speakers": speakers,
                "speaker_statistics": speaker_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.send_personal_message(json.dumps(response), connection_id)
            
        except Exception as e:
            logger.error(f"Error getting session transcript: {e}")
            error_response = {
                "type": "error",
                "connection_id": connection_id,
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.send_personal_message(json.dumps(error_response), connection_id)

# Global connection manager instance
manager = ConnectionManager()

class WebSocketService:
    """WebSocket service for real-time transcription"""
    
    def __init__(self):
        self.manager = manager
    
    async def handle_websocket_connection(self, websocket: WebSocket, session_id: str, user_id: str):
        """Handle WebSocket connection lifecycle"""
        connection_id = await self.manager.connect(websocket, session_id, user_id)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "audio_chunk":
                    # Process audio chunk
                    await self.manager.process_audio_chunk(
                        connection_id=connection_id,
                        session_id=session_id,
                        audio_data=message.get("audio_data"),
                        chunk_index=message.get("chunk_index", 0)
                    )
                
                elif message_type == "get_transcript":
                    # Send full transcript
                    await self.manager.get_session_transcript(session_id, connection_id)
                
                elif message_type == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                else:
                    logger.warning(f"Unknown message type: {message_type}")
                    
        except WebSocketDisconnect:
            self.manager.disconnect(connection_id, session_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.manager.disconnect(connection_id, session_id)
