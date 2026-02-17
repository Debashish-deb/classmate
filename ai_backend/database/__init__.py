import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database configuration
# Default to PostgreSQL in production; SQLite only for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./classmate.db")

if DATABASE_URL.startswith("sqlite"):
    logger.warning(
        "Using SQLite database — this is NOT suitable for production or "
        "multi-worker setups. Set DATABASE_URL to a PostgreSQL connection string."
    )
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from .models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
