from __future__ import annotations

from typing import Any, Dict, List, Optional

from .memory import AgentMemory
from .memory_store import build_default_store
from .note_agents import SummaryAgent, KeyPointsAgent, ActionItemsAgent, EvaluatorAgent, RefinerAgent
from .router_agent import RouterAgent


class NotesOrchestrator:
    def __init__(self, memory: Optional[AgentMemory] = None):
        self.memory = memory or AgentMemory(store=build_default_store())
        self._agents = {
            "router": RouterAgent(),
            "summary": SummaryAgent(),
            "key_points": KeyPointsAgent(),
            "action_items": ActionItemsAgent(),
            "evaluator": EvaluatorAgent(),
            "refiner": RefinerAgent(),
        }

    async def run(self, *, session_id: str, transcript: str, include_summary: bool, include_key_points: bool, include_action_items: bool) -> Dict[str, Any]:
        # First step is always router/tool-use.
        plan: List[str] = ["router"]

        # Router can influence ordering or defaults, but explicit flags win.
        prefer_action_items = include_action_items
        prefer_key_points = include_key_points
        prefer_summary = include_summary

        router_result = await self._agents["router"].run(
            session_id=session_id,
            transcript=transcript,
            memory=self.memory,
            context=None,
        )
        router_output = router_result.output
        plan_hints = (router_output or {}).get("plan_hints") or {}

        prefer_action_items = prefer_action_items or bool(plan_hints.get("prefer_action_items"))
        prefer_key_points = prefer_key_points or bool(plan_hints.get("prefer_key_points"))
        prefer_summary = prefer_summary or bool(plan_hints.get("prefer_summary"))

        # Specialist plan in priority order.
        if prefer_summary:
            plan.append("summary")
        if prefer_key_points:
            plan.append("key_points")
        if prefer_action_items:
            plan.append("action_items")
        plan.append("evaluator")
        plan.append("refiner")
        plan.append("evaluator")

        self.memory.add_event(session_id, "plan_created", {"plan": plan})

        # Router already executed above; keep it in outputs/meta.
        outputs: Dict[str, Any] = {"router": router_output}
        meta: Dict[str, Any] = {"router": router_result.meta}

        for step in plan:
            if step == "router":
                continue

            # Only run refiner if evaluator found issues.
            if step == "refiner":
                evaluation = outputs.get("evaluator") or {}
                issues = evaluation.get("issues") or []
                if not issues:
                    meta["refiner"] = {"skipped": True, "reason": "no_issues"}
                    outputs["refiner"] = {"skipped": True}
                    continue

            agent = self._agents[step]
            result = await agent.run(
                session_id=session_id,
                transcript=transcript,
                memory=self.memory,
                context=outputs,
            )
            outputs[step] = result.output
            meta[step] = result.meta

            # If refiner produced updated artifacts, apply them to the working context
            if step == "refiner" and isinstance(result.output, dict):
                if "summary" in result.output:
                    outputs["summary"] = result.output.get("summary")
                if "key_points" in result.output:
                    outputs["key_points"] = result.output.get("key_points")
                if "action_items" in result.output:
                    outputs["action_items"] = result.output.get("action_items")

        return {
            "session_id": session_id,
            "summary": outputs.get("summary"),
            "key_points": outputs.get("key_points", []) or [],
            "action_items": outputs.get("action_items", []) or [],
            "evaluation": outputs.get("evaluator"),
            "agent_meta": meta,
            "memory": self.memory.snapshot(session_id),
        }
