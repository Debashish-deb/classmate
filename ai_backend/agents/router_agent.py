from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from .memory import AgentMemory
from .tools import Tools


class RouterAgent(BaseAgent):
    name = "router"

    async def run(
        self,
        *,
        session_id: str,
        transcript: str,
        memory: AgentMemory,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentResult:
        classification = Tools.classify_transcript(transcript)
        entities = Tools.extract_entities(transcript)
        action_verbs = Tools.extract_action_verbs(transcript)

        memory.add_event(session_id, "tool_call", {"tool": classification.name, "result": classification.output})
        memory.add_event(session_id, "tool_call", {"tool": entities.name, "result": entities.output})
        memory.add_event(session_id, "tool_call", {"tool": action_verbs.name, "result": action_verbs.output})

        label = classification.output["label"]

        # Router decides priorities/plan hints.
        # This doesn't run specialists; it only suggests which specialists should run.
        plan_hints: Dict[str, Any] = {
            "label": label,
            "prefer_action_items": label in {"meeting", "interview"},
            "prefer_key_points": label in {"lecture", "meeting"},
            "prefer_summary": True,
        }

        # Example: if we detected many action verbs, prioritize action_items.
        if len(action_verbs.output.get("verbs", [])) >= 2:
            plan_hints["prefer_action_items"] = True

        # Store useful context in memory for downstream agents.
        memory.put(session_id, "classification", classification.output)
        memory.put(session_id, "entities", entities.output)
        memory.put(session_id, "action_verbs", action_verbs.output)
        memory.put(session_id, "plan_hints", plan_hints)

        return AgentResult(
            output={
                "classification": classification.output,
                "entities": entities.output,
                "action_verbs": action_verbs.output,
                "plan_hints": plan_hints,
            },
            meta={"label": label},
        )
