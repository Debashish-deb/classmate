from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..services.auth_service import AuthService
from ..services.identity_bridge import IdentityBridge
from ..database import get_db

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    Validates the Bearer token against Firebase, syncs with local DB, and returns the user payload.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    user_payload = AuthService.verify_firebase_token(token)
    
    # Idempotent sync with local DB
    bridge = IdentityBridge(db)
    await bridge.sync_user(user_payload["uid"])
    
    return user_payload
