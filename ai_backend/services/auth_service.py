import firebase_admin
from firebase_admin import auth, credentials
import os
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Initialize Firebase Admin
# In production, use credentials from environment variable or file
# For dev, we might need a service account file
try:
    # Check if app is already initialized to avoid errors on reload
    if not firebase_admin._apps:
        # Check for service account path env var
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized with service account")
        else:
            # Fallback to default credentials (works on GCP) or no-auth/mock for dev if needed
            # WARNING: This might fail smoothly if not configured, handling that later
            firebase_admin.initialize_app()
            logger.info("Firebase Admin initialized with default credentials")
except Exception as e:
    logger.warning(f"Firebase Admin initialization failed: {e}")

class AuthService:
    @staticmethod
    def verify_firebase_token(id_token: str) -> dict:
        """
        Verify Firebase ID token and return decoded token.
        Raises HTTPException if invalid.
        """
        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
