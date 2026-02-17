from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from .memory import AgentMemory


class SummaryAgent(BaseAgent):
    name = "summary"

    async def run(self, *, session_id: str, transcript: str, memory: AgentMemory, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript.strip()) if s.strip()]
        if len(sentences) <= 2:
            summary = transcript.strip()
        else:
            summary = " ".join(sentences[:3]).strip()
        memory.add_event(session_id, "summary_generated", {"length": len(summary)})
        return AgentResult(output=summary, meta={"sentences_used": min(len(sentences), 3)})


class KeyPointsAgent(BaseAgent):
    name = "key_points"

    async def run(self, *, session_id: str, transcript: str, memory: AgentMemory, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        important_keywords = [
            "important", "key", "main", "primary", "essential", "critical",
            "remember", "note", "pay attention", "focus on", "highlight",
        ]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript.strip()) if s.strip()]
        key_points: List[str] = []
        for s in sentences:
            s_l = s.lower()
            if any(k in s_l for k in important_keywords):
                cleaned = s[0].upper() + s[1:] if s else s
                if len(cleaned) > 10:
                    key_points.append(cleaned)
        key_points = key_points[:5]
        memory.add_event(session_id, "key_points_generated", {"count": len(key_points)})
        return AgentResult(output=key_points, meta={"candidates": len(sentences)})


class ActionItemsAgent(BaseAgent):
    name = "action_items"

    async def run(self, *, session_id: str, transcript: str, memory: AgentMemory, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        action_verbs = [
            "should", "must", "need to", "have to", "will", "can",
            "do", "make", "create", "implement", "complete", "finish",
        ]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript.strip()) if s.strip()]
        action_items: List[str] = []
        for s in sentences:
            s_l = s.lower()
            if any(v in s_l for v in action_verbs):
                cleaned = s[0].upper() + s[1:] if s else s
                if len(cleaned) > 10:
                    action_items.append(cleaned)
        action_items = action_items[:5]
        memory.add_event(session_id, "action_items_generated", {"count": len(action_items)})
        return AgentResult(output=action_items, meta={"candidates": len(sentences)})


class EvaluatorAgent(BaseAgent):
    name = "evaluator"

    async def run(self, *, session_id: str, transcript: str, memory: AgentMemory, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        summary = (context or {}).get("summary")
        key_points = (context or {}).get("key_points") or []
        action_items = (context or {}).get("action_items") or []

        issues: List[Dict[str, Any]] = []

        if summary is not None and len(summary.strip()) == 0:
            issues.append({"type": "empty_summary"})

        if len(key_points) > 7:
            issues.append({"type": "too_many_key_points", "count": len(key_points)})

        if len(action_items) > 7:
            issues.append({"type": "too_many_action_items", "count": len(action_items)})

        memory.add_event(session_id, "evaluation_done", {"issues": issues})
        return AgentResult(output={"issues": issues}, meta={"issues_count": len(issues)})


class RefinerAgent(BaseAgent):
    name = "refiner"

    async def run(self, *, session_id: str, transcript: str, memory: AgentMemory, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Refine outputs based on evaluator issues.

        Deterministic heuristic refiner (offline):
        - trims overlong lists
        - ensures summary is non-empty
        - injects detected entities into summary if missing and relevant
        """
        ctx = context or {}
        summary: str = (ctx.get("summary") or "").strip()
        key_points: List[str] = list(ctx.get("key_points") or [])
        action_items: List[str] = list(ctx.get("action_items") or [])
        evaluation = ctx.get("evaluator") or {}
        issues = evaluation.get("issues") or []

        entities = (memory.get(session_id, "entities") or {}).get("entities") or []
        top_entities = [e.get("text") for e in entities[:5] if e.get("text")]

        applied: List[Dict[str, Any]] = []

        for issue in issues:
            if issue.get("type") == "empty_summary":
                # Fallback: first 1-2 sentences
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript.strip()) if s.strip()]
                summary = (" ".join(sentences[:2]) if sentences else transcript.strip()).strip()
                applied.append({"type": "refiner_filled_summary"})

            if issue.get("type") == "too_many_key_points":
                key_points = key_points[:5]
                applied.append({"type": "refiner_trim_key_points", "to": 5})

            if issue.get("type") == "too_many_action_items":
                action_items = action_items[:5]
                applied.append({"type": "refiner_trim_action_items", "to": 5})

        # Entity-aware polish: if summary exists but doesn't mention any top entity, append a small context hint.
        if summary and top_entities:
            if not any(e in summary for e in top_entities):
                summary = f"{summary} (Context: {', '.join(top_entities[:3])}.)"
                applied.append({"type": "refiner_entity_context_added", "entities": top_entities[:3]})

        memory.add_event(session_id, "refiner_applied", {"applied": applied})
        return AgentResult(
            output={"summary": summary, "key_points": key_points, "action_items": action_items},
            meta={"applied": applied, "entities_used": top_entities[:3]},
        )
