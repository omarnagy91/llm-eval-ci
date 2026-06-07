from __future__ import annotations

from .base import Grader
from .heuristic import (
    GroundingGrader,
    HallucinationGrader,
    RelevanceGrader,
    ToolCallGrader,
    FormatGrader,
)
from .llm_judge import LLMJudgeGrader

HEURISTIC_GRADERS = {
    "grounding": GroundingGrader,
    "hallucination": HallucinationGrader,
    "relevance": RelevanceGrader,
    "tool_call": ToolCallGrader,
    "format": FormatGrader,
}


def build_grader(gc, judge_backend: str = "heuristic", judge_model: str = "") -> Grader:
    """Construct a grader from a GraderConfig.

    `judge_backend` / `judge_model` come from the top-level eval config and apply to
    any `llm_judge` graders (heuristic graders ignore them)."""
    if gc.type == "llm_judge":
        return LLMJudgeGrader(
            name=gc.name,
            threshold=gc.threshold,
            backend=judge_backend,
            model=judge_model,
            **gc.params,
        )
    cls = HEURISTIC_GRADERS.get(gc.type)
    if cls is None:
        raise ValueError(
            f"unknown grader type: {gc.type!r}. "
            f"Known: {sorted(HEURISTIC_GRADERS)} or 'llm_judge'."
        )
    g = cls(threshold=gc.threshold, **gc.params)
    g.name = gc.name
    return g


__all__ = [
    "Grader",
    "GroundingGrader",
    "HallucinationGrader",
    "RelevanceGrader",
    "ToolCallGrader",
    "FormatGrader",
    "LLMJudgeGrader",
    "HEURISTIC_GRADERS",
    "build_grader",
]
