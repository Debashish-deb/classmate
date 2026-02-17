"""
Prometheus metrics instrumentation for ClassMate API.
Provides request metrics, custom business metrics, and health indicators.
"""
import time
import os
from typing import Callable
from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

# ── Application Info ────────────────────────────
APP_INFO = Info("classmate_app", "ClassMate application info")
APP_INFO.info({
    "version": os.getenv("APP_VERSION", "1.0.0"),
    "environment": os.getenv("ENVIRONMENT", "development"),
})

# ── HTTP Metrics ────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method"],
)

# ── Business Metrics ────────────────────────────
TRANSCRIPTIONS_TOTAL = Counter(
    "transcriptions_total",
    "Total transcription requests",
    ["status"],  # success, failed, queued
)

AI_AGENT_REQUESTS = Counter(
    "ai_agent_requests_total",
    "Total AI agent requests",
    ["agent_type", "status"],  # ask, flashcard, quiz, study_guide
)

AI_AGENT_DURATION = Histogram(
    "ai_agent_duration_seconds",
    "AI agent request duration",
    ["agent_type"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

ACTIVE_SESSIONS = Gauge(
    "active_recording_sessions",
    "Number of active recording sessions",
)

REGISTERED_USERS = Gauge(
    "registered_users_total",
    "Total registered users",
)

PREMIUM_USERS = Gauge(
    "premium_users_total",
    "Total premium tier users",
)

VECTOR_DOCUMENTS = Gauge(
    "vector_documents_total",
    "Total documents in vector store",
)

AUTH_EVENTS = Counter(
    "auth_events_total",
    "Authentication events",
    ["event_type", "status"],  # login, register, google_oauth
)

UPLOAD_BYTES = Counter(
    "upload_bytes_total",
    "Total bytes uploaded",
)

CELERY_TASKS = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],  # success, failure, retry
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = self._normalize_path(request.url.path)

        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=path, status_code=status_code
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                method=method, endpoint=path
            ).observe(duration)
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize path to prevent high-cardinality labels."""
        parts = path.strip("/").split("/")
        normalized = []
        for i, part in enumerate(parts):
            # Replace UUIDs and numeric IDs with placeholders
            if len(part) > 20 or part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/" + "/".join(normalized) if normalized else "/"


def setup_monitoring(app: FastAPI):
    """Set up Prometheus monitoring for the FastAPI application."""
    app.add_middleware(PrometheusMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        return StarletteResponse(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
