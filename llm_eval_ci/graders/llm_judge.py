from __future__ import annotations

import json
import os
import re

from ..models import GoldenItem, GradeResult
from .base import Grader
from .heuristic import GroundingGrader, HallucinationGrader


RUBRIC = """You are a strict evaluation judge for an LLM product. Score the ANSWER on the \
criterion below from 0.0 (fails) to 1.0 (fully meets), grounded ONLY in the provided context \
and reference. Penalize any claim not supported by the context (hallucination) and any missing \
required fact. Be conservative: when unsure, score lower.

CRITERION: {criterion}

QUESTION:
{question}

CONTEXT (the only allowed source of truth):
{context}

REFERENCE ANSWER (ideal):
{reference}
REQUIRED FACTS: {must_include}
FORBIDDEN / FABRICATED CLAIMS (must NOT appear): {must_not_include}

ANSWER TO GRADE:
{answer}

Respond with ONLY a JSON object: {{"score": <float 0..1>, "rationale": "<one sentence>"}}"""


class LLMJudgeGrader(Grader):
    """Rubric-based LLM-as-judge.

    Backends:
      - heuristic / mock : deterministic offline approximation (grounding + factuality),
        so the harness runs in CI with no API key and no flake. Use for smoke tests / demos.
      - openai / anthropic : real model judging, calibrated by the rubric above.
    """
    name = "llm_judge"

    def __init__(self, name="llm_judge", threshold=0.7, backend="heuristic",
                 model="", criteria="overall answer quality, grounded in context", **params):
        super().__init__(threshold=threshold, **params)
        self.name = name
        self.backend = (backend or "heuristic").lower()
        self.model = model
        self.criteria = criteria

    def grade(self, item: GoldenItem, output: str, tool_calls=None) -> GradeResult:
        if self.backend in ("heuristic", "mock", ""):
            return self._offline(item, output)
        prompt = self._prompt(item, output)
        try:
            raw = self._call_model(prompt)
        except Exception as e:  # noqa: BLE001 (never let judge infra crash the gate ambiguously)
            return self._result(0.0, f"judge backend error ({self.backend}): {e}")
        return self._parse(raw)

    # --- deterministic offline judge (combines the grounding + factuality signals) ---
    def _offline(self, item, output) -> GradeResult:
        g = GroundingGrader(threshold=self.threshold).grade(item, output).score
        h = HallucinationGrader(threshold=self.threshold).grade(item, output).score
        score = 0.5 * g + 0.5 * h
        return self._result(score, f"[offline rubric judge] grounding={g:.2f} factuality={h:.2f}")

    def _prompt(self, item: GoldenItem, output: str) -> str:
        return RUBRIC.format(
            criterion=self.criteria,
            question=item.input,
            context="\n".join(f"- {c}" for c in item.context) or "(none provided)",
            reference=item.reference or "(none)",
            must_include=item.must_include or "(none)",
            must_not_include=item.must_not_include or "(none)",
            answer=output,
        )

    def _call_model(self, prompt: str) -> str:
        if self.backend == "openai":
            from openai import OpenAI  # lazy
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            resp = client.chat.completions.create(
                model=self.model or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return resp.choices[0].message.content or ""
        if self.backend == "anthropic":
            import anthropic  # lazy
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            resp = client.messages.create(
                model=self.model or "claude-haiku-4-5",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        raise ValueError(f"unknown judge backend: {self.backend}")

    def _parse(self, raw: str) -> GradeResult:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return self._result(0.0, f"judge returned unparseable output: {raw[:120]}")
        try:
            d = json.loads(m.group(0))
            score = float(d.get("score", 0.0))
            return self._result(score, str(d.get("rationale", ""))[:300])
        except Exception as e:  # noqa: BLE001
            return self._result(0.0, f"judge JSON parse error: {e}")
