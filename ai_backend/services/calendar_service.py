import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
import asyncio

# Google Calendar imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False

# Microsoft Graph imports (disabled)
# Microsoft authentication has been removed
MICROSOFT_GRAPH_AVAILABLE = False

logger = logging.getLogger(__name__)

class CalendarService:
    """Calendar integration service supporting Google Calendar only"""
    
    def __init__(self):
        self.google_credentials = None
        
        # Initialize Google Calendar
        if GOOGLE_CALENDAR_AVAILABLE:
            self._init_google_calendar()
    
    def _init_google_calendar(self):
        """Initialize Google Calendar service"""
        try:
            # Load credentials from environment or file
            credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
            
            if os.path.exists(credentials_path):
                with open(credentials_path, 'r') as f:
                    self.google_config = json.load(f)
            else:
                self.google_config = {
                    "web": {
                        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")]
                    }
                }
            
            logger.info("Google Calendar service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar: {e}")
    
    # Microsoft Graph methods removed
    
    def get_google_auth_url(self, state: str = None) -> str:
        """Get Google Calendar authorization URL"""
        if not GOOGLE_CALENDAR_AVAILABLE:
            raise HTTPException(status_code=501, detail="Google Calendar not available")
        
        try:
            flow = Flow.from_client_config(
                self.google_config,
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )
            
            flow.redirect_uri = self.google_config["web"]["redirect_uris"][0]
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state
            )
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate Google auth URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate auth URL")
    
    # Microsoft auth methods removed
    
    async def handle_google_callback(self, code: str) -> Dict[str, Any]:
        """Handle Google Calendar OAuth callback"""
        if not GOOGLE_CALENDAR_AVAILABLE:
            raise HTTPException(status_code=501, detail="Google Calendar not available")
        
        try:
            flow = Flow.from_client_config(
                self.google_config,
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )
            
            flow.redirect_uri = self.google_config["web"]["redirect_uris"][0]
            
            # Exchange authorization code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Store credentials
            self.google_credentials = credentials
            
            return {
                "provider": "google",
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
            }
            
        except Exception as e:
            logger.error(f"Failed to handle Google callback: {e}")
            raise HTTPException(status_code=500, detail="Failed to handle callback")
    
    # Microsoft callback methods removed
    
    async def sync_google_calendar(self, user_id: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Sync events from Google Calendar"""
        if not GOOGLE_CALENDAR_AVAILABLE or not self.google_credentials:
            raise HTTPException(status_code=501, detail="Google Calendar not available or not authenticated")
        
        try:
            service = build('calendar', 'v3', credentials=self.google_credentials)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            # Get events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events
            processed_events = []
            for event in events:
                processed_event = {
                    "id": event.get('id'),
                    "summary": event.get('summary', 'No Title'),
                    "description": event.get('description', ''),
                    "start": event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                    "end": event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                    "location": event.get('location', ''),
                    "attendees": [attendee.get('email') for attendee in event.get('attendees', [])],
                    "provider": "google",
                    "user_id": user_id
                }
                processed_events.append(processed_event)
            
            # Store events in database
            await self._store_calendar_events(processed_events, user_id)
            
            return processed_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            raise HTTPException(status_code=500, detail=f"Calendar sync failed: {str(e)}")
    
    async def _store_calendar_events(self, events: List[Dict[str, Any]], user_id: str):
        """Store calendar events in database"""
        try:
            from ..database import get_db
            from ..database.models import CalendarEvent
            
            with get_db() as db:
                # Clear existing events for this user
                db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id).delete()
                
                # Add new events
                for event in events:
                    calendar_event = CalendarEvent(
                        id=event["id"],
                        user_id=user_id,
                        provider=event["provider"],
                        summary=event["summary"],
                        description=event["description"],
                        start_time=datetime.fromisoformat(event["start"].replace('Z', '+00:00')) if event["start"] else None,
                        end_time=datetime.fromisoformat(event["end"].replace('Z', '+00:00')) if event["end"] else None,
                        location=event["location"],
                        attendees=json.dumps(event["attendees"]),
                        created_at=datetime.utcnow()
                    )
                    db.add(calendar_event)
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to store calendar events: {e}")
            # Don't raise here - calendar sync can continue even if storage fails
    
    async def get_upcoming_meetings(self, user_id: str, hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Get upcoming meetings for a user"""
        try:
            from ..database import get_db
            from ..database.models import CalendarEvent
            
            with get_db() as db:
                # Calculate time range
                now = datetime.utcnow()
                future_time = now + timedelta(hours=hours_ahead)
                
                # Query events
                events = db.query(CalendarEvent).filter(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time >= now,
                    CalendarEvent.start_time <= future_time
                ).order_by(CalendarEvent.start_time).all()
                
                # Convert to dict
                upcoming_meetings = []
                for event in events:
                    meeting = {
                        "id": event.id,
                        "summary": event.summary,
                        "description": event.description,
                        "start_time": event.start_time.isoformat(),
                        "end_time": event.end_time.isoformat(),
                        "location": event.location,
                        "provider": event.provider,
                        "attendees": json.loads(event.attendees) if event.attendees else []
                    }
                    upcoming_meetings.append(meeting)
                
                return upcoming_meetings
                
        except Exception as e:
            logger.error(f"Failed to get upcoming meetings: {e}")
            return []
    
    async def create_meeting_reminder(self, user_id: str, event_id: str, reminder_minutes: int = 15) -> bool:
        """Create a reminder for a meeting"""
        try:
            from ..database import get_db
            from ..database.models import CalendarEvent, MeetingReminder
            
            with get_db() as db:
                # Get event
                event = db.query(CalendarEvent).filter(
                    CalendarEvent.id == event_id,
                    CalendarEvent.user_id == user_id
                ).first()
                
                if not event:
                    return False
                
                # Create reminder
                reminder = MeetingReminder(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    event_id=event_id,
                    reminder_time=event.start_time - timedelta(minutes=reminder_minutes),
                    reminder_minutes=reminder_minutes,
                    created_at=datetime.utcnow()
                )
                
                db.add(reminder)
                db.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to create meeting reminder: {e}")
            return False
    
    async def detect_meeting_from_session(self, session_title: str, session_time: datetime, user_id: str) -> Optional[Dict[str, Any]]:
        """Try to match a recording session with a calendar event"""
        try:
            from ..database import get_db
            from ..database.models import CalendarEvent
            
            with get_db() as db:
                # Look for events around the session time (within 1 hour)
                time_window = timedelta(hours=1)
                
                events = db.query(CalendarEvent).filter(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time >= session_time - time_window,
                    CalendarEvent.start_time <= session_time + time_window
                ).all()
                
                # Simple matching based on title similarity and time proximity
                best_match = None
                best_score = 0
                
                for event in events:
                    # Calculate match score
                    score = 0
                    
                    # Time proximity (closer = higher score)
                    time_diff = abs((event.start_time - session_time).total_seconds())
                    if time_diff < 300:  # 5 minutes
                        score += 50
                    elif time_diff < 1800:  # 30 minutes
                        score += 25
                    
                    # Title similarity (simple keyword matching)
                    title_words = set(session_title.lower().split())
                    event_words = set(event.summary.lower().split())
                    common_words = title_words.intersection(event_words)
                    score += len(common_words) * 10
                    
                    if score > best_score:
                        best_score = score
                        best_match = event
                
                if best_match and best_score > 30:  # Minimum threshold
                    return {
                        "id": best_match.id,
                        "summary": best_match.summary,
                        "start_time": best_match.start_time.isoformat(),
                        "end_time": best_match.end_time.isoformat(),
                        "provider": best_match.provider,
                        "match_score": best_score
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to detect meeting from session: {e}")
            return None

# Global calendar service instance
calendar_service = CalendarService()
