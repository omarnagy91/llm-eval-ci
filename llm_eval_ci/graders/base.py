from __future__ import annotations

import re

from ..models import GoldenItem, GradeResult


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def contains(haystack: str, needle: str) -> bool:
    return norm(needle) in norm(haystack)


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", norm(s)))


def recall(output: str, target: str) -> float:
    """Fraction of the target's tokens that appear in the output (lexical recall)."""
    to = tokens(target)
    if not to:
        return 1.0
    return len(tokens(output) & to) / len(to)


class Grader:
    """A grader scores a single (golden item, system output) pair in [0,1]."""
    name = "base"

    def __init__(self, threshold: float = 0.7, **params):
        self.threshold = threshold
        self.params = params

    def grade(self, item: GoldenItem, output: str, tool_calls: list | None = None) -> GradeResult:
        raise NotImplementedError

    def _result(self, score: float, rationale: str, meta: dict | None = None) -> GradeResult:
        score = max(0.0, min(1.0, float(score)))
        return GradeResult(
            grader=self.name,
            score=round(score, 4),
            passed=score >= self.threshold,
            rationale=rationale,
            meta=meta or {},
        )
