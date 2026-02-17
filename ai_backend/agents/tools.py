from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    name: str
    output: Any
    meta: Dict[str, Any]


class Tools:
    """Lightweight, deterministic tools that agents can call.

    This is intentionally non-LLM and pure-python so it works offline and is testable.
    """

    @staticmethod
    def classify_transcript(transcript: str) -> ToolResult:
        text = transcript.lower()

        signals = {
            "meeting": ["agenda", "minutes", "action item", "next steps", "follow up", "deadline"],
            "lecture": ["chapter", "lecture", "professor", "today we will", "slides", "syllabus"],
            "interview": ["tell me about", "walk me through", "why did you", "can you explain"],
        }

        scores: Dict[str, int] = {k: 0 for k in signals}
        for label, keywords in signals.items():
            for kw in keywords:
                if kw in text:
                    scores[label] += 1

        best = max(scores.items(), key=lambda kv: kv[1])
        label = best[0] if best[1] > 0 else "generic"

        return ToolResult(
            name="classify_transcript",
            output={"label": label, "scores": scores},
            meta={"length_chars": len(transcript)},
        )

    @staticmethod
    def extract_entities(transcript: str, max_items: int = 25) -> ToolResult:
        # Simple proper-noun-ish extractor (capitalized tokens)
        candidates = re.findall(r"\b[A-Z][a-zA-Z0-9\-']{2,}\b", transcript)
        freq: Dict[str, int] = {}
        for c in candidates:
            freq[c] = freq.get(c, 0) + 1
        entities = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:max_items]
        return ToolResult(
            name="extract_entities",
            output={"entities": [{"text": e, "count": n} for e, n in entities]},
            meta={"candidates": len(candidates)},
        )

    @staticmethod
    def extract_action_verbs(transcript: str, max_items: int = 25) -> ToolResult:
        verbs = [
            "should",
            "must",
            "need to",
            "have to",
            "will",
            "plan to",
            "decide",
            "schedule",
            "follow up",
            "email",
        ]
        text = transcript.lower()
        hits: List[str] = []
        for v in verbs:
            if v in text:
                hits.append(v)
        return ToolResult(
            name="extract_action_verbs",
            output={"verbs": hits[:max_items]},
            meta={"unique_hits": len(set(hits))},
        )
