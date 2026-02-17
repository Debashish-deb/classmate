"""
AI Agent API endpoints for the Study Assistant.
Provides Q&A, flashcards, quizzes, study guides, and concept explanations.
"""
import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from ..agents.study_assistant import StudyAssistantAgent
from ..agents.vector_store import VectorMemoryStore
from ..api.auth_api import get_current_user

router = APIRouter(prefix="/api/v1/ai", tags=["ai-agent"])

# Shared instances
_study_agent = StudyAssistantAgent()
_vector_store = VectorMemoryStore()


# ── Request Models ──────────────────────────────

class AskQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class FlashcardRequest(BaseModel):
    session_id: str
    transcript: str
    count: int = 10

class QuizRequest(BaseModel):
    session_id: str
    transcript: str
    question_count: int = 5
    difficulty: str = "medium"

class StudyGuideRequest(BaseModel):
    session_id: str
    transcript: str

class ExplainRequest(BaseModel):
    concept: str
    style: str = "simple"  # simple, detailed, visual, eli5

class IndexRequest(BaseModel):
    session_id: str
    content: str
    content_type: str = "transcript"

class SearchRequest(BaseModel):
    query: str
    content_type: Optional[str] = None
    limit: int = 10


# ── Endpoints ───────────────────────────────────

@router.post("/ask")
async def ask_question(request: AskQuestionRequest, user: dict = Depends(get_current_user)):
    """Ask a question about lecture content. Uses vector search for context."""
    try:
        result = await _study_agent.ask_question(
            question=request.question,
            user_id=user["user_id"],
            session_id=request.session_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flashcards")
async def generate_flashcards(request: FlashcardRequest, user: dict = Depends(get_current_user)):
    """Generate study flashcards from a transcript."""
    try:
        result = await _study_agent.generate_flashcards(
            transcript=request.transcript,
            session_id=request.session_id,
            count=request.count,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quiz")
async def generate_quiz(request: QuizRequest, user: dict = Depends(get_current_user)):
    """Generate a practice quiz from a transcript."""
    try:
        result = await _study_agent.generate_quiz(
            transcript=request.transcript,
            session_id=request.session_id,
            question_count=request.question_count,
            difficulty=request.difficulty,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/study-guide")
async def generate_study_guide(request: StudyGuideRequest, user: dict = Depends(get_current_user)):
    """Generate a comprehensive study guide from a transcript."""
    try:
        result = await _study_agent.generate_study_guide(
            session_id=request.session_id,
            transcript=request.transcript,
        )
        return {"guide": result.output, "meta": result.meta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain")
async def explain_concept(request: ExplainRequest, user: dict = Depends(get_current_user)):
    """Explain a concept in the requested style."""
    try:
        result = await _study_agent.explain_concept(
            concept=request.concept,
            user_id=user["user_id"],
            style=request.style,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def index_content(request: IndexRequest, user: dict = Depends(get_current_user)):
    """Index content into vector memory for future semantic search."""
    try:
        if request.content_type == "transcript":
            doc_id = _study_agent.index_transcript(
                user_id=user["user_id"],
                session_id=request.session_id,
                transcript=request.content,
            )
        else:
            doc_id = _study_agent.index_summary(
                user_id=user["user_id"],
                session_id=request.session_id,
                summary=request.content,
            )
        return {"doc_id": doc_id, "status": "indexed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_content(request: SearchRequest, user: dict = Depends(get_current_user)):
    """Semantic search across all indexed content."""
    try:
        embeddings = _study_agent._ensure_embeddings()
        query_embedding = None
        if embeddings:
            try:
                query_embedding = embeddings.embed_query(request.query)
            except Exception:
                pass

        results = _vector_store.search_similar(
            query_embedding=query_embedding,
            query_text=request.query,
            user_id=user["user_id"],
            content_type=request.content_type,
            limit=request.limit,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def ai_stats(user: dict = Depends(get_current_user)):
    """Get AI usage statistics for the current user."""
    try:
        doc_count = _vector_store.get_user_document_count(user["user_id"])
        return {
            "user_id": user["user_id"],
            "indexed_documents": doc_count,
            "ai_features": [
                "ask_question", "flashcards", "quiz",
                "study_guide", "explain", "semantic_search"
            ],
            "vector_db": "pgvector" if _vector_store._use_pgvector else "keyword_fallback",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
