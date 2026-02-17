"""
Vector memory store using pgvector for semantic search over lecture content.
Falls back to in-memory store when PostgreSQL with pgvector is unavailable.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# ──────────────────────────────────────────────
# Database Models for Vector Storage
# ──────────────────────────────────────────────

class VectorDocument(Base):
    __tablename__ = "vector_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=False, default="transcript")  # transcript, summary, note, flashcard
    metadata_json = Column(Text, nullable=True)
    embedding_text = Column(Text, nullable=True)  # text used to generate embedding
    created_at = Column(DateTime, default=datetime.utcnow)


class VectorMemoryStore:
    """
    Manages vector embeddings for semantic search.
    Uses pgvector when available, falls back to keyword search on SQLite.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./classmate.db")
        self._use_pgvector = "postgresql" in self.database_url
        self._engine = create_engine(self.database_url)
        self._Session = sessionmaker(bind=self._engine)
        self._initialized = False

    def initialize(self):
        """Create tables and enable pgvector extension if on PostgreSQL."""
        if self._initialized:
            return

        if self._use_pgvector:
            try:
                with self._engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
            except Exception as e:
                print(f"pgvector extension not available: {e}")
                self._use_pgvector = False

        Base.metadata.create_all(self._engine)

        # Add vector column if pgvector is available
        if self._use_pgvector:
            try:
                with self._engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE vector_documents ADD COLUMN IF NOT EXISTS embedding vector(1536)"
                    ))
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_vector_embedding ON vector_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                    ))
                    conn.commit()
            except Exception as e:
                print(f"Could not create vector column: {e}")
                self._use_pgvector = False

        self._initialized = True

    def store_document(
        self,
        user_id: str,
        content: str,
        content_type: str = "transcript",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Store a document with optional vector embedding."""
        self.initialize()
        doc_id = str(uuid.uuid4())

        session = self._Session()
        try:
            doc = VectorDocument(
                id=doc_id,
                user_id=user_id,
                session_id=session_id,
                content=content,
                content_type=content_type,
                metadata_json=json.dumps(metadata or {}),
                embedding_text=content[:2000],
            )
            session.add(doc)

            if embedding and self._use_pgvector:
                emb_str = "[" + ",".join(str(x) for x in embedding) + "]"
                session.execute(
                    text("UPDATE vector_documents SET embedding = :emb WHERE id = :id"),
                    {"emb": emb_str, "id": doc_id}
                )

            session.commit()
            return doc_id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def search_similar(
        self,
        query_embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        Uses vector similarity on pgvector, keyword matching on SQLite.
        """
        self.initialize()
        session = self._Session()
        try:
            if self._use_pgvector and query_embedding:
                return self._pgvector_search(
                    session, query_embedding, user_id, content_type, limit
                )
            elif query_text:
                return self._keyword_search(
                    session, query_text, user_id, content_type, limit
                )
            else:
                return self._recent_documents(session, user_id, content_type, limit)
        finally:
            session.close()

    def _pgvector_search(
        self, session, query_embedding: List[float],
        user_id: Optional[str], content_type: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Cosine similarity search using pgvector."""
        emb_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        where_clauses = ["embedding IS NOT NULL"]
        params: Dict[str, Any] = {"emb": emb_str, "limit": limit}

        if user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        if content_type:
            where_clauses.append("content_type = :content_type")
            params["content_type"] = content_type

        where = " AND ".join(where_clauses)

        rows = session.execute(
            text(f"""
                SELECT id, user_id, session_id, content, content_type, metadata_json,
                       1 - (embedding <=> :emb::vector) AS similarity
                FROM vector_documents
                WHERE {where}
                ORDER BY embedding <=> :emb::vector
                LIMIT :limit
            """),
            params
        ).fetchall()

        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "session_id": r.session_id,
                "content": r.content,
                "content_type": r.content_type,
                "metadata": json.loads(r.metadata_json or "{}"),
                "similarity": float(r.similarity),
            }
            for r in rows
        ]

    def _keyword_search(
        self, session, query_text: str,
        user_id: Optional[str], content_type: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword search for SQLite."""
        where_clauses = ["content LIKE :query"]
        params: Dict[str, Any] = {"query": f"%{query_text}%", "limit": limit}

        if user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        if content_type:
            where_clauses.append("content_type = :content_type")
            params["content_type"] = content_type

        where = " AND ".join(where_clauses)

        rows = session.execute(
            text(f"""
                SELECT id, user_id, session_id, content, content_type, metadata_json
                FROM vector_documents
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            params
        ).fetchall()

        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "session_id": r.session_id,
                "content": r.content,
                "content_type": r.content_type,
                "metadata": json.loads(r.metadata_json or "{}"),
                "similarity": 0.5,
            }
            for r in rows
        ]

    def _recent_documents(
        self, session, user_id: Optional[str],
        content_type: Optional[str], limit: int
    ) -> List[Dict[str, Any]]:
        """Return most recent documents."""
        where_clauses = ["1=1"]
        params: Dict[str, Any] = {"limit": limit}

        if user_id:
            where_clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        if content_type:
            where_clauses.append("content_type = :content_type")
            params["content_type"] = content_type

        where = " AND ".join(where_clauses)

        rows = session.execute(
            text(f"""
                SELECT id, user_id, session_id, content, content_type, metadata_json
                FROM vector_documents
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            params
        ).fetchall()

        return [
            {
                "id": r.id,
                "user_id": r.user_id,
                "session_id": r.session_id,
                "content": r.content,
                "content_type": r.content_type,
                "metadata": json.loads(r.metadata_json or "{}"),
                "similarity": 0.0,
            }
            for r in rows
        ]

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        session = self._Session()
        try:
            result = session.execute(
                text("DELETE FROM vector_documents WHERE id = :id"),
                {"id": doc_id}
            )
            session.commit()
            return result.rowcount > 0
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    def get_user_document_count(self, user_id: str) -> int:
        """Get total document count for a user."""
        session = self._Session()
        try:
            result = session.execute(
                text("SELECT COUNT(*) as cnt FROM vector_documents WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            return result.cnt if result else 0
        finally:
            session.close()
