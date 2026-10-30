"""Offline lint for curated golden sets."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

from .models import GoldenItem


@dataclass(frozen=True)
class GoldenIssue:
    """One lint finding. severity 'error' means the case cannot be scored."""

    severity: str  # "error" | "warning"
    message: str
    case_id: Optional[str] = None


def validate_golden(
    items: list[GoldenItem],
    *,
    system_has_respond_full: Optional[bool] = None,
) -> list[GoldenIssue]:
    """Return actionable lint issues for a golden set.

    Checks:
    - duplicate ids
    - cases with neither ``reference`` nor any ``must_include`` (unscoreable
      for grounding / relevance against a real answer contract)
    - ``must_include`` strings that also appear in ``must_not_include``
    - ``expected_tool`` set when the system under test has no ``respond_full``
      (tool calls stay empty with plain ``respond``)

    Deterministic and offline. ``system_has_respond_full`` is None when the
    caller did not supply a system module; then any ``expected_tool`` is a
    warning that tool grading needs ``respond_full`` or ``--outputs`` with
    ``tool_calls``.
    """
    issues: list[GoldenIssue] = []

    counts = Counter(it.id for it in items)
    for case_id, n in sorted(counts.items()):
        if n > 1:
            issues.append(
                GoldenIssue(
                    "warning",
                    f"duplicate id appears {n} times",
                    case_id,
                )
            )

    for it in items:
        has_ref = bool((it.reference or "").strip())
        has_must = any((s or "").strip() for s in (it.must_include or []))
        if not has_ref and not has_must:
            issues.append(
                GoldenIssue(
                    "error",
                    "unscoreable: set a reference and/or must_include so grounding/relevance have something to score against",
                    it.id,
                )
            )

        must = [(s or "").strip() for s in (it.must_include or []) if (s or "").strip()]
        must_not = [(s or "").strip() for s in (it.must_not_include or []) if (s or "").strip()]
        must_not_lower = {s.lower() for s in must_not}
        for fact in must:
            if fact.lower() in must_not_lower:
                issues.append(
                    GoldenIssue(
                        "warning",
                        f"must_include {fact!r} also appears in must_not_include",
                        it.id,
                    )
                )

        if it.expected_tool:
            if system_has_respond_full is False:
                issues.append(
                    GoldenIssue(
                        "warning",
                        f"expected_tool={it.expected_tool!r} but system has no respond_full (tool_calls will be empty)",
                        it.id,
                    )
                )
            elif system_has_respond_full is None:
                issues.append(
                    GoldenIssue(
                        "warning",
                        f"expected_tool={it.expected_tool!r}: tool grading needs respond_full or --outputs with tool_calls",
                        it.id,
                    )
                )

    return issues
