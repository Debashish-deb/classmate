import logging
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

_logger = logging.getLogger(__name__)

Base = declarative_base()

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    owner = relationship("User", back_populates="owned_teams")
    members = relationship("TeamMember", back_populates="team")
    shared_sessions = relationship("SharedSession", back_populates="team")

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False, default="member")  # owner, admin, member
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")

class SharedSession(Base):
    __tablename__ = "shared_sessions"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    shared_by = Column(String, ForeignKey("users.id"), nullable=False)
    permissions = Column(Text, nullable=True)  # JSON string: ["read", "comment", "annotate"]
    shared_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    session = relationship("Session", back_populates="shared_with_teams")
    team = relationship("Team", back_populates="shared_sessions")
    sharer = relationship("User")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False, default=0.0)  # Audio timestamp in seconds
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    parent_comment_id = Column(String, ForeignKey("comments.id"), nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent_comment = relationship("Comment", remote_side=[id])
    replies = relationship("Comment", back_populates="parent_comment")

class Annotation(Base):
    __tablename__ = "annotations"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float, nullable=False)    # End time in seconds
    annotation_type = Column(String, nullable=False, default="note")  # note, highlight, action_item
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="annotations")
    user = relationship("User", back_populates="annotations")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    app_name = Column(String, nullable=False)
    api_key_hash = Column(String, nullable=False)
    permissions = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

# Update User model with collaboration relationships
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # OAuth tokens — stored encrypted via EncryptionService
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expires = Column(DateTime, nullable=True)
    
    # Email/Password authentication
    password_hash = Column(String, nullable=True)  # For email login
    auth_method = Column(String, nullable=False, default="google")  # 'google' or 'email'
    
    # Encryption keys
    encryption_key = Column(Text, nullable=True)
    public_key = Column(Text, nullable=True)
    
    # Relationships
    calendar_events = relationship("CalendarEvent", back_populates="user")
    reminders = relationship("MeetingReminder", back_populates="user")
    owned_teams = relationship("Team", back_populates="owner")
    team_memberships = relationship("TeamMember", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    annotations = relationship("Annotation", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")

    def set_oauth_token(self, provider: str, token_type: str, value: str):
        """Encrypt and store an OAuth token.
        provider: 'google' only
        token_type: 'access_token' or 'refresh_token'
        """
        from ..services.encryption_service import encryption_service
        try:
            encrypted = encryption_service.encrypt_sensitive_data({"token": value})
            setattr(self, f"{provider}_{token_type}", encrypted)
        except Exception as e:
            _logger.error(f"Failed to encrypt {provider} {token_type}: {e}")
            raise

    def set_password(self, password: str):
        """Hash and set password for email authentication."""
        import bcrypt
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        self.auth_method = "email"

    def check_password(self, password: str) -> bool:
        """Verify password for email authentication."""
        import bcrypt
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def get_oauth_token(self, provider: str, token_type: str) -> str | None:
        """Decrypt and return an OAuth token.
        provider: 'google' only
        token_type: 'access_token' or 'refresh_token'
        """
        from ..services.encryption_service import encryption_service
        raw = getattr(self, f"{provider}_{token_type}", None)
        if not raw:
            return None
        try:
            decrypted = encryption_service.decrypt_sensitive_data(raw)
            return decrypted.get("token")
        except Exception:
            # Fallback: token may be stored in plaintext from before encryption was added
            _logger.warning(f"Could not decrypt {provider} {token_type}, returning raw value")
            return raw
