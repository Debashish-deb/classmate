"""
Advanced security hardening for ClassMate API.
Includes rate limiting, security headers, input sanitization,
CSRF protection, and request validation.
"""
import os
import re
import time
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .telemetry import get_logger

logger = get_logger(__name__)


# ══════════════════════════════════════════════
# 1. Rate Limiting (In-Memory + Redis-ready)
# ══════════════════════════════════════════════

class RateLimitStore:
    """In-memory rate limit store. Replace with Redis in production cluster."""

    def __init__(self):
        self._store: Dict[str, list] = {}

    def add_request(self, key: str, now: float):
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(now)

    def count_requests(self, key: str, window_start: float) -> int:
        if key not in self._store:
            return 0
        self._store[key] = [t for t in self._store[key] if t >= window_start]
        return len(self._store[key])


_rate_store = RateLimitStore()

# Rate limit tiers: endpoint_pattern -> (requests, window_seconds)
RATE_LIMITS = {
    "/auth/login": (10, 60),          # 10 login attempts per minute
    "/auth/register": (5, 60),         # 5 registrations per minute
    "/api/v1/ai/": (30, 60),          # 30 AI requests per minute
    "/api/v1/transcribe": (10, 60),   # 10 transcriptions per minute
    "/api/v1/": (100, 60),            # 100 API requests per minute
    "/": (200, 60),                    # 200 total requests per minute
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting with configurable limits per endpoint."""

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        path = request.url.path
        now = time.time()

        for pattern, (max_requests, window) in RATE_LIMITS.items():
            if path.startswith(pattern):
                key = f"{client_ip}:{pattern}"
                window_start = now - window
                count = _rate_store.count_requests(key, window_start)

                if count >= max_requests:
                    logger.warning(
                        "rate_limit_exceeded",
                        ip=client_ip,
                        path=path,
                        limit=max_requests,
                        window=window,
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Too many requests. Please try again later.",
                            "retry_after": window,
                        },
                        headers={"Retry-After": str(window)},
                    )

                _rate_store.add_request(key, now)
                break

        response = await call_next(request)
        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# ══════════════════════════════════════════════
# 2. Security Headers Middleware
# ══════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

        # Strict Transport Security (HTTPS)
        if os.getenv("ENVIRONMENT", "development") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=(), payment=()"
        )

        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]

        return response


# ══════════════════════════════════════════════
# 3. Request Validation Middleware
# ══════════════════════════════════════════════

# Suspicious patterns that indicate attack attempts
SUSPICIOUS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"on\w+\s*=",
    r"union\s+select",
    r"drop\s+table",
    r"insert\s+into",
    r"delete\s+from",
    r"\.\./\.\.",
    r"/etc/passwd",
    r"cmd\.exe",
    r"powershell",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests for suspicious content."""

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB max body

    async def dispatch(self, request: Request, call_next):
        # Check Content-Length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )

        # Check query parameters for injection
        query_string = str(request.url.query)
        if self._is_suspicious(query_string):
            logger.warning(
                "suspicious_request_blocked",
                ip=request.client.host if request.client else "unknown",
                path=request.url.path,
                reason="suspicious_query_params",
            )
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid request"},
            )

        # Check path for traversal
        if ".." in request.url.path or "%" in request.url.path:
            path_decoded = request.url.path.replace("%2e", ".").replace("%2f", "/")
            if ".." in path_decoded:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Invalid request path"},
                )

        response = await call_next(request)
        return response

    @staticmethod
    def _is_suspicious(text: str) -> bool:
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(text):
                return True
        return False


# ══════════════════════════════════════════════
# 4. Input Sanitization Utilities
# ══════════════════════════════════════════════

def sanitize_string(value: str, max_length: int = 10000) -> str:
    """Sanitize a string input by removing dangerous content."""
    if not value:
        return value

    # Truncate
    value = value[:max_length]

    # Remove null bytes
    value = value.replace("\x00", "")

    # Basic HTML entity escaping
    value = (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

    return value


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal."""
    # Remove path separators
    filename = filename.replace("/", "").replace("\\", "")
    # Remove null bytes
    filename = filename.replace("\x00", "")
    # Remove leading dots
    filename = filename.lstrip(".")
    # Only allow safe characters
    filename = re.sub(r"[^\w\-.]", "_", filename)
    return filename[:255]


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """Verify a CSRF token using constant-time comparison."""
    return secrets.compare_digest(token, expected)


# ══════════════════════════════════════════════
# 5. Setup Function
# ══════════════════════════════════════════════

def setup_security(app: FastAPI):
    """Apply all security middleware to the FastAPI application."""
    # Order matters: outermost middleware runs first
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    logger.info("security_middleware_initialized")
