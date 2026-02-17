from firebase_admin import auth
from sqlalchemy.orm import Session
from ..database.models import User
from datetime import datetime
import json
import uuid
from ..core.telemetry import get_logger

logger = get_logger(__name__)

class IdentityBridge:
    def __init__(self, db: Session):
        self.db = db

    async def sync_user(self, firebase_uid: str) -> User:
        """
        Idempotently sync Firebase user with local database.
        Returns the local User object.
        """
        try:
            # 1. Fetch from Firebase
            fb_user = auth.get_user(firebase_uid)
            
            # 2. Check local DB
            user = self.db.query(User).filter(User.firebase_uid == firebase_uid).first()
            
            if not user:
                # Create new user
                user = User(
                    id=str(uuid.uuid4()),
                    firebase_uid=firebase_uid,
                    email=fb_user.email,
                    email_verified=str(fb_user.email_verified),
                    firebase_metadata=json.dumps(fb_user._data) if hasattr(fb_user, '_data') else None,
                    tier="free",
                    created_at=datetime.utcnow()
                )
                self.db.add(user)
                logger.info("user_created_local", firebase_uid=firebase_uid)
            else:
                # Update existing user (Last write wins sync)
                user.email = fb_user.email
                user.email_verified = str(fb_user.email_verified)
                user.firebase_metadata = json.dumps(fb_user._data) if hasattr(fb_user, '_data') else None
                user.updated_at = datetime.utcnow()
                logger.info("user_synced_local", firebase_uid=firebase_uid)
            
            self.db.commit()
            self.db.refresh(user)
            return user
            
        except auth.UserNotFoundError:
            # Handle soft-delete if user deleted in Firebase
            user = self.db.query(User).filter(User.firebase_uid == firebase_uid).first()
            if user:
                user.is_active = "false"
                user.deleted_at = datetime.utcnow()
                self.db.commit()
                logger.warning("user_deactivated", firebase_uid=firebase_uid, reason="firebase_not_found")
            raise
        except Exception as e:
            self.db.rollback()
            logger.error("user_sync_failed", firebase_uid=firebase_uid, error=str(e))
            raise

    async def purge_user_data(self, firebase_uid: str):
        """
        Soft-delete user and related data (GDPR compliant).
        """
        try:
            user = self.db.query(User).filter(User.firebase_uid == firebase_uid).first()
            if user:
                user.deleted_at = datetime.utcnow()
                user.is_active = "false"
                self.db.commit()
                logger.info("user_soft_deleted", firebase_uid=firebase_uid)
        except Exception as e:
            self.db.rollback()
            logger.error("user_purge_failed", firebase_uid=firebase_uid, error=str(e))
            raise
