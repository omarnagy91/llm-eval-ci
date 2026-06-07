<div align="center">

# llm-eval-ci

### Catch LLM quality regressions in CI — before your users do.

[![License: MIT](https://img.shields.io/badge/License-MIT-7C1A1D.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-1A1A1A.svg)
![PRs welcome](https://img.shields.io/badge/PRs-welcome-1A1A1A.svg)

*A golden-set regression gate for LLM / RAG / agent systems. Small, readable, and opinionated about the one part that actually matters — the dataset.*

</div>

---

You ship a prompt tweak, a model bump, a RAG change. Nothing throws. Tests are green. Three days later support tells you the assistant started inventing a refund policy. LLM systems don't fail loudly — they *drift*, and you find out from customers.

`llm-eval-ci` turns your real production failures into a **golden regression set**, scores every change against it with **calibrated graders**, and **fails the PR** when answer quality drops. It's a quality gate for non-deterministic systems.

```
[llm-eval-ci] gate: FAIL ❌  (v2)
  overall pass rate: 17%  (1/6)
  - grounding      mean=0.17  pass=17%
  - hallucination  mean=0.58  pass=33%
  - relevance      mean=0.58  pass=83%
  - tool_call      mean=0.83  pass=83%
  - answer_quality mean=0.38  pass=17%
  · overall pass rate 17% below required 90%
  · regression vs baseline: -83% (baseline 100%, max allowed -5%)
  · grader 'grounding' regressed -0.83 vs baseline
```
<sub>(verbatim output of `bash scripts/demo.sh` — the example's `eval.yaml` exercises 5 of the 6 grader types.)</sub>

---

## The opinion this tool has

The CI plumbing is the commodity part — a GitHub Action that runs a script and sets an exit code. Free tools (DeepEval, promptfoo, Braintrust) all do that. **The hard, valuable part is the golden set:** deciding *what "correct" means for your product*, mining your logs for the cases that actually break, and writing graders that are strict about the things that matter and quiet about the things that don't.

So this tool is built around that workflow, not around the plumbing:

1. **Ground truth comes from your logs, not a benchmark.** `golden build` scaffolds a regression set from your real traces; a human curates it. That curation *is* the asset.
2. **Graders are explicit and auditable.** Required facts, forbidden/hallucinated claims, tool-call correctness, format, and a rubric LLM-judge — each with a threshold you set. No black-box "vibe score."
3. **The gate is a real gate.** Non-zero exit, regression-vs-baseline, per-grader floors. It blocks merges.

It is intentionally small and readable (~600 lines, one dependency). You should be able to read the whole thing before you trust it to gate your releases.

---

## Quickstart

```bash
git clone https://github.com/omarnagy91/llm-eval-ci && cd llm-eval-ci
pip install -e .
bash scripts/demo.sh        # watch the gate pass on v1, then fail on a regressed v2
```

Point it at your own system:

```bash
# 1. scaffold a golden set from your production logs (jsonl), then curate it by hand
python -m llm_eval_ci.cli golden build --traces my_traces.jsonl --out golden.jsonl --sample 40

# 2. write eval.yaml (graders + thresholds + gate), then run it against your system
python -m llm_eval_ci.cli run --config eval.yaml --system my_system.py --json baseline.json

# 3. in CI, run against the committed baseline — exit 1 (failed check) on regression
python -m llm_eval_ci.cli run --config eval.yaml --system my_system.py --baseline baseline.json --report report.md --summary
```

Your `my_system.py` just exposes how to call your system:

```python
def respond(user_input: str, context: list[str]) -> str:
    return my_app.answer(user_input, context)
# or, to also check tool calls:
def respond_full(item: dict) -> dict:
    r = my_app.run(item["input"])
    return {"output": r.text, "tool_calls": r.tools}
```

---

## How it works

```
production traces ──▶ golden build ──▶  golden.jsonl  ──┐
   (jsonl logs)        (+ human curation, the asset)    │
                                                        ▼
   your system ───────────────▶  runner  ──▶  graders  ──▶  gate ──▶ exit 0 / 1
   (respond / respond_full)               (thresholds)   (pass rate, regression)
```

## Graders

| Grader | Catches | How it scores |
| --- | --- | --- |
| `grounding` | dropped/missing required facts | fraction of `must_include` facts present |
| `hallucination` | fabricated / forbidden claims | penalizes any `must_not_include` trap |
| `relevance` | off-topic or evasive answers | lexical coverage of the reference/query |
| `tool_call` | agent skipped the required tool | `expected_tool` present in the call list |
| `format` | broken JSON / contract | valid-JSON or regex contract |
| `llm_judge` | holistic quality, nuance | rubric LLM-as-judge (OpenAI / Anthropic) |

The `llm_judge` grader runs **offline-deterministic by default** (`judge: heuristic`) so CI never flakes and needs no key. Flip `judge: openai` (or `anthropic`) in `eval.yaml` for real model grading; the rubric forces a conservative, context-grounded 0–1 score with a one-line rationale.

## Wiring it into CI

Drop in `.github/workflows/eval-gate.yml` (included). It runs on every PR and fails the check when the gate fails. Make it a required status check and a regression can't merge. The report is posted to the job summary and uploaded as an artifact.

---

## Status & honest limits

`v0.1` — small and real, not a platform. It does **not** replace tracing/observability (Langfuse, Phoenix) or a labeling UI; it's the regression-gate layer that sits in front of your merges. Heuristic graders are lexical (substring/recall) — fast and deterministic, good for facts/format/tools; use the `llm_judge` backend for semantic nuance. Calibrating thresholds against your golden set is the work, and it's worth doing once.

---

<div align="center">

### Built by Omar G. Nagy — AI Systems Engineer

I build evaluation harnesses and regression datasets for LLM / RAG / agent products — turning messy production logs into graders and golden sets a team can trust between releases.

**Need a quality gate for your LLM system?** I run fixed-scope eval engagements: a golden set from your real failures, calibrated graders, and a CI gate that holds the line.

[**→ omargnagy.com/work/llm-eval-ci**](https://omargnagy.com/work/llm-eval-ci) · [neurascale.org](https://www.neurascale.org/services/llm-evaluation) · [LinkedIn](https://linkedin.com/in/omargnagy)

*MIT licensed — use it, fork it, ship it.*

</div>
