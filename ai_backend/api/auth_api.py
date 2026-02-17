import os
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
from typing import Optional

from ..database import get_db
from ..database.collaboration_models import User
from .public_api import APIKeyManager

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
api_key_manager = APIKeyManager()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
    auth_method: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current authenticated user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email/password"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    import uuid
    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        email=request.email,
        name=request.name,
        auth_method="email"
    )
    user.set_password(request.password)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "auth_method": user.auth_method
        },
        auth_method="email"
    )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email/password"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not user.check_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.auth_method != "email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account uses OAuth login. Please use Google authentication."
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    
    return AuthResponse(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "auth_method": user.auth_method
        },
        auth_method="email"
    )

@router.post("/google", response_model=AuthResponse)
async def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authenticate with Google OAuth"""
    from ..services.calendar_service import CalendarService
    
    calendar_service = CalendarService()
    
    try:
        # Exchange code for tokens
        token_data = await calendar_service.handle_google_callback(request.code)
        
        # Get user info from Google
        # Note: You should decode the ID token or use Google API to get user info
        # For now, we'll create a placeholder user structure
        
        # Check if user exists by email (you'd get email from Google)
        # This is a simplified version - in production, decode the ID token
        user_email = "user@example.com"  # Replace with actual email from Google
        user_name = "Google User"  # Replace with actual name from Google
        
        user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            # Create new user
            user = User(
                email=user_email,
                name=user_name,
                auth_method="google"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Store OAuth tokens
        user.set_oauth_token("google", "access_token", token_data["access_token"])
        if "refresh_token" in token_data:
            user.set_oauth_token("google", "refresh_token", token_data["refresh_token"])
        user.google_token_expires = datetime.fromisoformat(token_data["expires_at"]) if token_data.get("expires_at") else None
        
        db.commit()
        db.refresh(user)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id, "email": user.email})
        
        return AuthResponse(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "auth_method": user.auth_method
            },
            auth_method="google"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "auth_method": current_user.auth_method,
        "created_at": current_user.created_at
    }

@router.get("/google/url")
async def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    from ..services.calendar_service import CalendarService
    
    calendar_service = CalendarService()
    try:
        auth_url = calendar_service.get_google_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Google auth URL: {str(e)}"
        )
