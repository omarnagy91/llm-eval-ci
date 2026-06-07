from __future__ import annotations

from dataclasses import dataclass, field

import yaml


@dataclass
class GraderConfig:
    name: str
    type: str                       # heuristic grader key, or "llm_judge"
    threshold: float = 0.7
    weight: float = 1.0
    params: dict = field(default_factory=dict)


@dataclass
class EvalConfig:
    name: str
    golden: str                     # path to golden jsonl
    graders: list[GraderConfig]
    gate_min_pass_rate: float = 0.9        # fraction of items that must pass ALL graders
    gate_max_regression: float = 0.02      # vs baseline: allowed drop in overall pass rate
    judge: str = "heuristic"               # llm-judge backend: heuristic | openai | anthropic
    judge_model: str = ""
    baseline: str = ""                     # optional path to a baseline report json


def load_config(path: str) -> EvalConfig:
    d = yaml.safe_load(open(path, "r", encoding="utf-8"))
    graders = [
        GraderConfig(
            name=g.get("name", g["type"]),
            type=g["type"],
            threshold=float(g.get("threshold", 0.7)),
            weight=float(g.get("weight", 1.0)),
            params=g.get("params", {}) or {},
        )
        for g in d.get("graders", [])
    ]
    return EvalConfig(
        name=d.get("name", "eval"),
        golden=d["golden"],
        graders=graders,
        gate_min_pass_rate=float(d.get("gate_min_pass_rate", 0.9)),
        gate_max_regression=float(d.get("gate_max_regression", 0.02)),
        judge=d.get("judge", "heuristic"),
        judge_model=d.get("judge_model", ""),
        baseline=d.get("baseline", ""),
    )
