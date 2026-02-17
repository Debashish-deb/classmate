import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api.routes import router
from .api.auth_api import router as auth_router
from .api.ops import router as ops_router
from .api.ai_agent_api import router as ai_agent_router
from .database import init_db
from .core.telemetry import setup_telemetry, get_logger
from .core.monitoring import setup_monitoring
from .core.security import setup_security
import uvicorn

logger = get_logger(__name__)

app = FastAPI(title="ClassMate AI Backend")
setup_telemetry(app)
setup_monitoring(app)
setup_security(app)

# Configure CORS from environment
_cors_origins_raw = os.getenv("CORS_ALLOWED_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",")]
_allow_credentials = "*" not in _cors_origins  # credentials only with explicit origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
app.include_router(auth_router)
app.include_router(ops_router)
app.include_router(ai_agent_router)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

@app.get("/")
async def root():
    return JSONResponse({
        "message": "ClassMate AI Backend",
        "version": "1.0.0",
        "status": "running",
        "features": ["transcription", "notes_generation", "session_management"]
    })

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
