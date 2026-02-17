from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .memory import AgentMemory


@dataclass
class AgentResult:
    output: Any
    meta: Dict[str, Any]


class BaseAgent:
    name: str = "base"

    async def run(self, *, session_id: str, transcript: str, memory: AgentMemory, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        raise NotImplementedError
