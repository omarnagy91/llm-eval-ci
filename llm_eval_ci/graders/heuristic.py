from __future__ import annotations

import json
import re

from ..models import GoldenItem, GradeResult
from .base import Grader, contains, recall


class GroundingGrader(Grader):
    """Are the required, source-grounded facts actually present in the answer?"""
    name = "grounding"

    def grade(self, item: GoldenItem, output: str, tool_calls=None) -> GradeResult:
        facts = item.must_include
        if facts:
            present = [f for f in facts if contains(output, f)]
            missing = [f for f in facts if f not in present]
            score = len(present) / len(facts)
            rat = f"{len(present)}/{len(facts)} required facts present"
            if missing:
                rat += f"; missing: {missing}"
            return self._result(score, rat, {"missing": missing})
        score = recall(output, item.reference)
        return self._result(score, f"reference coverage={score:.2f} (no explicit required facts)")


class HallucinationGrader(Grader):
    """Did the answer assert any forbidden / fabricated claim (a known trap)?"""
    name = "hallucination"

    def grade(self, item: GoldenItem, output: str, tool_calls=None) -> GradeResult:
        traps = item.must_not_include
        if not traps:
            return self._result(1.0, "no forbidden claims configured")
        hits = [t for t in traps if contains(output, t)]
        score = 1.0 - (len(hits) / len(traps))
        rat = "no forbidden/fabricated claims" if not hits else f"hallucinated/forbidden claim(s): {hits}"
        return self._result(score, rat, {"violations": hits})


class RelevanceGrader(Grader):
    """Does the answer actually address the question / reference?"""
    name = "relevance"

    def grade(self, item: GoldenItem, output: str, tool_calls=None) -> GradeResult:
        target = item.reference or item.input
        score = recall(output, target)
        anchor = "reference" if item.reference else "query"
        return self._result(score, f"lexical relevance to {anchor}={score:.2f}")


class ToolCallGrader(Grader):
    """Did the agent invoke the tool the case requires?"""
    name = "tool_call"

    def grade(self, item: GoldenItem, output: str, tool_calls=None) -> GradeResult:
        if not item.expected_tool:
            return self._result(1.0, "no tool expected")
        names = [(tc.get("name") or tc.get("tool")) for tc in (tool_calls or [])]
        ok = item.expected_tool in names
        return self._result(
            1.0 if ok else 0.0,
            f"expected tool '{item.expected_tool}' " + ("called" if ok else f"NOT called (got {names})"),
        )


class FormatGrader(Grader):
    """Structural / format compliance (valid JSON, or a regex contract)."""
    name = "format"

    def grade(self, item: GoldenItem, output: str, tool_calls=None) -> GradeResult:
        if self.params.get("json"):
            try:
                json.loads(output)
                return self._result(1.0, "valid JSON")
            except Exception as e:  # noqa: BLE001
                return self._result(0.0, f"invalid JSON: {e}")
        pattern = self.params.get("regex")
        if pattern:
            ok = re.search(pattern, output or "") is not None
            return self._result(1.0 if ok else 0.0, f"regex {'matched' if ok else 'did not match'}")
        return self._result(1.0, "no format constraint configured")
