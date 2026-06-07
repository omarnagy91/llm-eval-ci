from __future__ import annotations

import json
from typing import Iterator

from .models import Trace, GoldenItem


def _read_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_traces(path: str) -> list[Trace]:
    """Load raw production traces (jsonl) into normalized records."""
    out: list[Trace] = []
    for d in _read_jsonl(path):
        out.append(Trace(
            id=str(d.get("id", len(out))),
            input=d.get("input", ""),
            output=d.get("output", ""),
            context=d.get("context", []) or [],
            tool_calls=d.get("tool_calls", []) or [],
            meta=d.get("meta", {}) or {},
        ))
    return out


def load_golden(path: str) -> list[GoldenItem]:
    """Load a curated golden regression set (jsonl)."""
    out: list[GoldenItem] = []
    for d in _read_jsonl(path):
        out.append(GoldenItem(
            id=str(d.get("id", len(out))),
            input=d.get("input", ""),
            context=d.get("context", []) or [],
            reference=d.get("reference", ""),
            must_include=d.get("must_include", []) or [],
            must_not_include=d.get("must_not_include", []) or [],
            expected_tool=d.get("expected_tool"),
            labels=d.get("labels", {}) or {},
            notes=d.get("notes", ""),
        ))
    return out


def write_golden(path: str, items: list[GoldenItem]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps({
                "id": it.id,
                "input": it.input,
                "context": it.context,
                "reference": it.reference,
                "must_include": it.must_include,
                "must_not_include": it.must_not_include,
                "expected_tool": it.expected_tool,
                "labels": it.labels,
                "notes": it.notes,
            }, ensure_ascii=False) + "\n")
