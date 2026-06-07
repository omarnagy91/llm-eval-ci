from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Trace:
    """A single production interaction loaded from a client's logs."""
    id: str
    input: str
    output: str = ""
    context: list[str] = field(default_factory=list)   # retrieved docs / grounding context
    tool_calls: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@dataclass
class GoldenItem:
    """A curated regression case. This is the asset — the result of human judgment
    about what "correct" means for *this* product, distilled from real failures."""
    id: str
    input: str
    context: list[str] = field(default_factory=list)
    reference: str = ""                                  # ideal / reference answer
    must_include: list[str] = field(default_factory=list)      # facts the answer MUST contain
    must_not_include: list[str] = field(default_factory=list)  # hallucination traps / forbidden claims
    expected_tool: Optional[str] = None
    labels: dict = field(default_factory=dict)
    notes: str = ""


@dataclass
class GradeResult:
    grader: str
    score: float            # 0..1
    passed: bool
    rationale: str = ""
    meta: dict = field(default_factory=dict)


@dataclass
class ItemResult:
    item_id: str
    output: str
    grades: list[GradeResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.grades) if self.grades else False


@dataclass
class EvalReport:
    config_name: str = ""
    system_name: str = ""
    items: list[ItemResult] = field(default_factory=list)
    grader_scores: dict = field(default_factory=dict)      # grader -> mean score
    grader_pass_rate: dict = field(default_factory=dict)   # grader -> fraction of items passing
    overall_pass_rate: float = 0.0                         # fraction of items passing ALL graders
    gate_passed: bool = False
    gate_reasons: list[str] = field(default_factory=list)
    baseline_delta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "config_name": self.config_name,
            "system_name": self.system_name,
            "overall_pass_rate": self.overall_pass_rate,
            "gate_passed": self.gate_passed,
            "gate_reasons": self.gate_reasons,
            "grader_scores": self.grader_scores,
            "grader_pass_rate": self.grader_pass_rate,
            "baseline_delta": self.baseline_delta,
            "items": [
                {
                    "item_id": it.item_id,
                    "passed": it.passed,
                    "output": it.output,
                    "grades": [
                        {"grader": g.grader, "score": g.score, "passed": g.passed, "rationale": g.rationale}
                        for g in it.grades
                    ],
                }
                for it in self.items
            ],
        }
