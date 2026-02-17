# ── Stage 1: Builder ──────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ai_backend/requirements_simple.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────
FROM python:3.13-slim

# Security: create non-root user
RUN groupadd -r classmate && useradd -r -g classmate -d /app -s /sbin/nologin classmate

WORKDIR /app

# Install only runtime dependencies (no gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY ai_backend/ ./ai_backend/

# Set ownership
RUN chown -R classmate:classmate /app

# Security: run as non-root
USER classmate

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Run the application (no --reload in production)
CMD ["uvicorn", "ai_backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
