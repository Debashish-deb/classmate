"""
LangChain-powered Study Assistant Agent.
Provides smart Q&A, flashcard generation, quiz creation, and study planning
based on lecture transcripts and notes stored in vector memory.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .base import AgentResult, BaseAgent
from .memory import AgentMemory
from .vector_store import VectorMemoryStore


def _get_openai_client():
    """Lazy import to avoid hard dependency at module load."""
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    except Exception:
        return None


def _get_embeddings():
    """Lazy import for embeddings model."""
    try:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    except Exception:
        return None


class StudyAssistantAgent(BaseAgent):
    """
    AI-powered study assistant that uses LangChain for:
    - Answering questions about lecture content
    - Generating flashcards from transcripts
    - Creating practice quizzes
    - Building study plans
    - Explaining complex concepts simply
    """
    name = "study_assistant"

    def __init__(self):
        self._vector_store = VectorMemoryStore()
        self._llm = None
        self._embeddings = None

    def _ensure_llm(self):
        if self._llm is None:
            self._llm = _get_openai_client()
        return self._llm

    def _ensure_embeddings(self):
        if self._embeddings is None:
            self._embeddings = _get_embeddings()
        return self._embeddings

    async def run(
        self,
        *,
        session_id: str,
        transcript: str,
        memory: AgentMemory,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        """Default run: generate a comprehensive study guide."""
        return await self.generate_study_guide(session_id, transcript, memory)

    async def ask_question(
        self,
        question: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Answer a question using relevant lecture content from vector memory."""
        llm = self._ensure_llm()
        if not llm:
            return {"answer": "AI service unavailable. Please check API key.", "sources": []}

        # Search for relevant content
        embeddings = self._ensure_embeddings()
        query_embedding = None
        if embeddings:
            try:
                query_embedding = embeddings.embed_query(question)
            except Exception:
                pass

        relevant_docs = self._vector_store.search_similar(
            query_embedding=query_embedding,
            query_text=question,
            user_id=user_id,
            limit=5,
        )

        context_text = "\n\n---\n\n".join(
            [f"[{d['content_type']}] {d['content'][:1000]}" for d in relevant_docs]
        )

        prompt = f"""You are a brilliant study assistant for a university student.
Answer the following question based on the lecture content provided.
Be clear, concise, and use examples when helpful.
If the content doesn't cover the topic, say so honestly.

LECTURE CONTENT:
{context_text}

QUESTION: {question}

Provide a helpful, educational answer:"""

        try:
            response = await llm.ainvoke(prompt)
            answer = response.content
        except Exception as e:
            answer = f"Could not generate answer: {str(e)}"

        return {
            "answer": answer,
            "sources": [{"session_id": d.get("session_id"), "similarity": d.get("similarity", 0)} for d in relevant_docs],
            "question": question,
        }

    async def generate_flashcards(
        self,
        transcript: str,
        session_id: str,
        count: int = 10,
    ) -> Dict[str, Any]:
        """Generate study flashcards from a transcript."""
        llm = self._ensure_llm()
        if not llm:
            return {"flashcards": [], "error": "AI service unavailable"}

        prompt = f"""You are an expert educator creating flashcards for a student.
Generate exactly {count} flashcards from this lecture transcript.
Each flashcard should test a key concept.

TRANSCRIPT:
{transcript[:4000]}

Return ONLY a JSON array of objects with "front" (question) and "back" (answer) keys.
Example: [{{"front": "What is X?", "back": "X is..."}}]

JSON:"""

        try:
            response = await llm.ainvoke(prompt)
            text = response.content.strip()
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            flashcards = json.loads(text)
        except Exception as e:
            flashcards = [{"front": "Error generating flashcards", "back": str(e)}]

        return {
            "flashcards": flashcards,
            "session_id": session_id,
            "count": len(flashcards),
        }

    async def generate_quiz(
        self,
        transcript: str,
        session_id: str,
        question_count: int = 5,
        difficulty: str = "medium",
    ) -> Dict[str, Any]:
        """Generate a practice quiz from a transcript."""
        llm = self._ensure_llm()
        if not llm:
            return {"questions": [], "error": "AI service unavailable"}

        prompt = f"""You are an expert educator creating a {difficulty} difficulty quiz.
Generate exactly {question_count} multiple-choice questions from this lecture.

TRANSCRIPT:
{transcript[:4000]}

Return ONLY a JSON array where each question has:
- "question": the question text
- "options": array of 4 options (strings)
- "correct_index": index (0-3) of the correct answer
- "explanation": brief explanation of the correct answer

JSON:"""

        try:
            response = await llm.ainvoke(prompt)
            text = response.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            questions = json.loads(text)
        except Exception as e:
            questions = []

        return {
            "questions": questions,
            "session_id": session_id,
            "difficulty": difficulty,
            "count": len(questions),
        }

    async def generate_study_guide(
        self,
        session_id: str,
        transcript: str,
        memory: Optional[AgentMemory] = None,
    ) -> AgentResult:
        """Generate a comprehensive study guide from a transcript."""
        llm = self._ensure_llm()
        if not llm:
            return AgentResult(
                output={"error": "AI service unavailable"},
                meta={"agent": self.name, "status": "error"},
            )

        prompt = f"""You are an expert study coach. Create a comprehensive study guide from this lecture.

TRANSCRIPT:
{transcript[:5000]}

Create a study guide with these sections:
1. OVERVIEW - 2-3 sentence summary
2. KEY CONCEPTS - List of main concepts with brief explanations
3. IMPORTANT TERMS - Glossary of key terms
4. STUDY TIPS - Specific tips for mastering this material
5. CONNECTIONS - How this connects to broader topics
6. PRACTICE QUESTIONS - 3 questions to test understanding

Return as JSON with keys: overview, key_concepts (array), important_terms (array of {{term, definition}}), study_tips (array), connections (array), practice_questions (array of {{question, answer}})

JSON:"""

        try:
            response = await llm.ainvoke(prompt)
            text = response.content.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            guide = json.loads(text)
        except Exception as e:
            guide = {"error": str(e)}

        return AgentResult(
            output=guide,
            meta={"agent": self.name, "session_id": session_id, "status": "success"},
        )

    async def explain_concept(
        self,
        concept: str,
        user_id: str,
        style: str = "simple",
    ) -> Dict[str, Any]:
        """Explain a concept in the requested style."""
        llm = self._ensure_llm()
        if not llm:
            return {"explanation": "AI service unavailable", "concept": concept}

        style_instructions = {
            "simple": "Explain like I'm 5 years old. Use simple analogies.",
            "detailed": "Give a thorough academic explanation with examples.",
            "visual": "Describe using visual metaphors and mental models.",
            "eli5": "Explain like I'm 5. Use everyday examples.",
        }

        instruction = style_instructions.get(style, style_instructions["simple"])

        # Search for relevant context
        embeddings = self._ensure_embeddings()
        query_embedding = None
        if embeddings:
            try:
                query_embedding = embeddings.embed_query(concept)
            except Exception:
                pass

        relevant_docs = self._vector_store.search_similar(
            query_embedding=query_embedding,
            query_text=concept,
            user_id=user_id,
            limit=3,
        )

        context_text = "\n".join([d["content"][:500] for d in relevant_docs])

        prompt = f"""You are a brilliant tutor.

CONTEXT FROM LECTURES:
{context_text}

CONCEPT: {concept}

{instruction}

Provide a clear explanation:"""

        try:
            response = await llm.ainvoke(prompt)
            explanation = response.content
        except Exception as e:
            explanation = f"Could not generate explanation: {str(e)}"

        return {
            "concept": concept,
            "explanation": explanation,
            "style": style,
        }

    def index_transcript(
        self,
        user_id: str,
        session_id: str,
        transcript: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Index a transcript into vector memory for future searches."""
        self._vector_store.initialize()

        embedding = None
        embeddings_model = self._ensure_embeddings()
        if embeddings_model:
            try:
                embedding = embeddings_model.embed_query(transcript[:2000])
            except Exception:
                pass

        doc_id = self._vector_store.store_document(
            user_id=user_id,
            session_id=session_id,
            content=transcript,
            content_type="transcript",
            metadata=metadata or {},
            embedding=embedding,
        )
        return doc_id

    def index_summary(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Index a summary into vector memory."""
        self._vector_store.initialize()

        embedding = None
        embeddings_model = self._ensure_embeddings()
        if embeddings_model:
            try:
                embedding = embeddings_model.embed_query(summary[:2000])
            except Exception:
                pass

        doc_id = self._vector_store.store_document(
            user_id=user_id,
            session_id=session_id,
            content=summary,
            content_type="summary",
            metadata=metadata or {},
            embedding=embedding,
        )
        return doc_id
