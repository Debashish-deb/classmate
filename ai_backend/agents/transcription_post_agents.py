from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PostProcessResult:
    text: str
    corrections: List[Dict[str, Any]]


class CleanupAgent:
    name = "cleanup"

    def run(self, text: str) -> PostProcessResult:
        corrections: List[Dict[str, Any]] = []
        original = text

        # Normalize whitespace
        text2 = re.sub(r"\s+", " ", text).strip()
        if text2 != text:
            corrections.append({"type": "cleanup_whitespace"})
        text = text2

        # Fix spacing before punctuation
        text2 = re.sub(r"\s+([,.!?;:])", r"\1", text)
        if text2 != text:
            corrections.append({"type": "cleanup_punctuation_spacing"})
        text = text2

        # Ensure single space after punctuation where appropriate
        text2 = re.sub(r"([,.!?;:])(\S)", r"\1 \2", text)
        if text2 != text:
            corrections.append({"type": "cleanup_punctuation_after"})
        text = text2

        if text != original and not corrections:
            corrections.append({"type": "cleanup_generic"})

        return PostProcessResult(text=text, corrections=corrections)


class TermConsistencyAgent:
    name = "term_consistency"

    def run(self, text: str, learned_replacements: Optional[Dict[str, str]] = None) -> PostProcessResult:
        corrections: List[Dict[str, Any]] = []
        replacements = learned_replacements or {}
        for src, dst in replacements.items():
            if src and dst and src != dst and src in text:
                text = text.replace(src, dst)
                corrections.append({"type": "term_consistency_replacement", "from": src, "to": dst})
        return PostProcessResult(text=text, corrections=corrections)


class ConfidenceFilterAgent:
    name = "confidence_filter"

    def run(self, text: str, confidence: Optional[float]) -> PostProcessResult:
        # If confidence is extremely low, soften output (do not hallucinate).
        corrections: List[Dict[str, Any]] = []
        if confidence is None:
            return PostProcessResult(text=text, corrections=corrections)

        if confidence < -1.5:
            # Whisper avg_logprob is negative; lower = worse.
            corrections.append({"type": "low_confidence_flag", "confidence": confidence})
            text = f"[low confidence] {text}" if text else "[low confidence]"
        return PostProcessResult(text=text, corrections=corrections)


class SpeakerTurnAgent:
    name = "speaker_turn"

    def run(self, text: str, primary_speaker: Optional[str]) -> PostProcessResult:
        # If we have a speaker label and text isn't already labeled, add a simple prefix.
        corrections: List[Dict[str, Any]] = []
        if primary_speaker and text and not re.match(r"^Speaker\s*\d+\s*:\s*", text):
            text = f"{primary_speaker}: {text}"
            corrections.append({"type": "speaker_prefix_added", "speaker": primary_speaker})
        return PostProcessResult(text=text, corrections=corrections)


class PostTranscriptionChain:
    def __init__(self):
        self.cleanup = CleanupAgent()
        self.term = TermConsistencyAgent()
        self.conf = ConfidenceFilterAgent()
        self.speaker = SpeakerTurnAgent()

    def run(
        self,
        *,
        text: str,
        confidence: Optional[float],
        primary_speaker: Optional[str],
        learned_replacements: Optional[Dict[str, str]],
    ) -> PostProcessResult:
        corrections: List[Dict[str, Any]] = []

        r = self.cleanup.run(text)
        text = r.text
        corrections.extend(r.corrections)

        r = self.term.run(text, learned_replacements=learned_replacements)
        text = r.text
        corrections.extend(r.corrections)

        r = self.conf.run(text, confidence)
        text = r.text
        corrections.extend(r.corrections)

        r = self.speaker.run(text, primary_speaker)
        text = r.text
        corrections.extend(r.corrections)

        return PostProcessResult(text=text, corrections=corrections)
