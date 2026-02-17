from sqlalchemy import event, Column, String, Integer, DateTime, Text, Float, UniqueConstraint
import uuid

# ... existing code ...

def log_audit(mapper, connection, target, action):
    """Event listener for audit logging"""
    try:
        # Avoid logging the AuditLog itself to prevent recursion
        if isinstance(target, AuditLog):
            return
            
        audit_id = str(uuid.uuid4())
        # Capture changed data (simplified)
        new_data = {}
        for column in target.__table__.columns:
            new_data[column.name] = str(getattr(target, column.name))

        connection.execute(
            AuditLog.__table__.insert().values(
                id=audit_id,
                table_name=target.__tablename__,
                record_id=str(target.id) if hasattr(target, 'id') else "unknown",
                action=action,
                new_data=json.dumps(new_data),
                changed_at=datetime.utcnow()
            )
        )
    except Exception as e:
        print(f"Audit logging failed: {e}")

# Register listeners
for model in [Session, TranscriptChunk, User]:
    event.listen(model, 'after_insert', lambda m, c, t: log_audit(m, c, t, 'INSERT'))
    event.listen(model, 'after_update', lambda m, c, t: log_audit(m, c, t, 'UPDATE'))

class SessionStatus(Enum):
    recording = "recording"
    processing = "processing"
    completed = "completed"
    failed = "failed"

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=False)  # in milliseconds
    status = Column(String, nullable=False, default=SessionStatus.recording)
    total_chunks = Column(Integer, default=0)
    uploaded_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    key_points = Column(Text, nullable=True)  # JSON string
    action_items = Column(Text, nullable=True)  # JSON string
    deleted_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)

class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    __table_args__ = (
        UniqueConstraint('session_id', 'chunk_index', name='uq_session_chunk'),
    )
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, nullable=True)  # Client-side capture timestamp
    confidence = Column(Float, nullable=True)
    speaker = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified = Column(Text, nullable=True) # Bool or status
    tier = Column(String, default="free") # "free", "pro"
    is_active = Column(Text, default="true") # Using String for bool-like or actual bool
    firebase_metadata = Column(Text, nullable=True) # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, index=True)
    table_name = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    action = Column(String, nullable=False) # INSERT, UPDATE, DELETE
    old_data = Column(Text, nullable=True) # JSON string
    new_data = Column(Text, nullable=True) # JSON string
    changed_by = Column(String, nullable=True) # user_id
    changed_at = Column(DateTime, default=datetime.utcnow)

class AIMetrics(Base):
    __tablename__ = "ai_metrics"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)
    session_id = Column(String, index=True, nullable=True)
    metric_type = Column(String, nullable=False)  # e.g. "transcription_duration_ms", "model_used"
    metric_value = Column(Text, nullable=True)    # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
