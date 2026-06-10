<div align="center">

# llm-eval-ci

### A CI quality gate for LLM products: golden regression set in, exit 1 out when answer quality drops.

[![CI](https://github.com/omarnagy91/llm-eval-ci/actions/workflows/ci.yml/badge.svg)](https://github.com/omarnagy91/llm-eval-ci/actions/workflows/ci.yml)
[![LLM eval gate](https://github.com/omarnagy91/llm-eval-ci/actions/workflows/eval-gate.yml/badge.svg)](https://github.com/omarnagy91/llm-eval-ci/actions/workflows/eval-gate.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-7C1A1D.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-1A1A1A.svg)

*Small and readable on purpose: 667 lines of Python, one runtime dependency (PyYAML), deterministic by default.*

</div>

---

## Why this exists

You ship a prompt tweak, a model bump, a retrieval change. Tests are green, the deploy goes out. Three days later support reports that the assistant has been quoting a refund window that does not exist. Nothing failed, because nothing was gating the part that matters: whether the answers are still correct.

LLM regressions are silent. Unit tests cannot catch them, and a vibes check before big releases does not survive a real release cadence. `llm-eval-ci` makes answer quality something CI can fail on:

1. **Golden set from your logs.** `golden build` scaffolds a regression set from real production traces; a human curates it. That curation is the asset.
2. **Explicit graders.** Required facts, hallucination traps, relevance, tool calls, format, and a rubric LLM-judge. Each has a threshold you set; each failure comes with a rationale.
3. **A real gate.** Non-zero exit, minimum pass rate, regression-vs-baseline checks per grader. Make it a required status check and a regression cannot merge.

## Quickstart (2 minutes)

```bash
git clone https://github.com/omarnagy91/llm-eval-ci && cd llm-eval-ci
pip install -e .
bash scripts/demo.sh    # gate passes on v1, fails (exit 1) on a regressed v2
```

Point it at your own system:

```bash
# 1. scaffold a golden set from production logs (jsonl), then curate it by hand
llm-eval-ci golden build --traces my_traces.jsonl --out golden.jsonl --sample 40

# 2. write eval.yaml (graders, thresholds, gate), run it, commit the baseline
llm-eval-ci run --config eval.yaml --system my_system.py --json baseline.json

# 3. in CI: exit 1 (failed check) when quality drops below the bar or regresses vs baseline
llm-eval-ci run --config eval.yaml --system my_system.py --baseline baseline.json --report report.md --summary
```

`my_system.py` is a thin adapter that exposes how to call your system:

```python
def respond(user_input: str, context: list[str]) -> str:
    return my_app.answer(user_input, context)

# or, to also check tool calls:
def respond_full(item: dict) -> dict:
    r = my_app.run(item["input"])
    return {"output": r.text, "tool_calls": r.tools}
```

No adapter? Pass precomputed outputs instead: `--outputs outputs.jsonl` (lines of `{"id", "output", "tool_calls"}`).

## The demo, run for real

The repo ships a 6-case support-bot example. Output below is captured verbatim from `bash scripts/demo.sh` on this codebase. First the grounded version, which passes and writes the baseline:

```text
==> v1 (grounded answers): expect PASS, write baseline
[llm-eval-ci] gate: PASS ✅  (v1)
  overall pass rate: 100%  (6/6)
  - grounding      mean=1.00  pass=100%
  - hallucination  mean=1.00  pass=100%
  - relevance      mean=0.99  pass=100%
  - tool_call      mean=1.00  pass=100%
  - answer_quality mean=1.00  pass=100%
  · all gate checks passed
[llm-eval-ci] PASS: the gate passed, merge allowed
[llm-eval-ci] wrote examples/rag_support_bot/baseline.json
v1 exit=0
```

Then a "helpful" rewrite that silently invented a 30-day refund window, the wrong price, the wrong data region, and dropped a required tool call:

```text
==> v2 (silently regressed): expect FAIL + regression vs the v1 baseline
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
  · grader 'hallucination' regressed -0.42 vs baseline
  · grader 'relevance' regressed -0.41 vs baseline
  · grader 'tool_call' regressed -0.17 vs baseline
  · grader 'answer_quality' regressed -0.62 vs baseline
[llm-eval-ci] FAIL: the gate failed the build (PR blocked)
[llm-eval-ci] wrote examples/rag_support_bot/last-report.md
v2 exit=1  (non-zero = the gate correctly failed the build)
```

That `exit=1` is the product. It is the thing that blocks the bad PR.

## How it works

```
production traces ──▶ golden build ──▶  golden.jsonl  ──┐
   (jsonl logs)        (+ human curation, the asset)    │
                                                        ▼
   your system ───────────────▶  runner  ──▶  graders  ──▶  gate ──▶ exit 0 / 1
   (respond / respond_full)               (thresholds)   (pass rate, regression)
```

A case passes only when **every** configured grader passes. The gate fails when the overall pass rate is below `gate_min_pass_rate`, or, when a baseline is given, when the overall pass rate or any grader's mean score drops by more than `gate_max_regression`.

### The six graders

| Grader | Catches | How it scores |
| --- | --- | --- |
| `grounding` | dropped or missing required facts | fraction of `must_include` facts present |
| `hallucination` | fabricated or forbidden claims | penalizes each `must_not_include` trap that appears |
| `relevance` | off-topic or evasive answers | lexical recall against the reference (or query) |
| `tool_call` | agent skipped a required tool | `expected_tool` present in the call list |
| `format` | broken output contract | valid-JSON check or a regex the output must match |
| `llm_judge` | semantic quality, nuance | rubric LLM-as-judge, scored 0 to 1 with a one-line rationale |

The `llm_judge` grader is **offline-deterministic by default** (`judge: heuristic`): it combines the grounding and hallucination signals, needs no API key, and produces the same score on every run, so the CI gate never flakes. Set `judge: openai` or `judge: anthropic` in `eval.yaml` for real model grading (defaults: `gpt-4o-mini` / `claude-haiku-4-5`); the rubric instructs a conservative, context-grounded score.

The heuristic graders are lexical (normalized substring and token recall). That is a feature for facts, prices, regions, and tool names, and a limitation for paraphrase-heavy answers; use the LLM judge backend for those.

## Honest comparison

| Tool | What it is | Where it beats this tool |
| --- | --- | --- |
| [DeepEval](https://github.com/confident-ai/deepeval) | pytest-style LLM eval framework with a large catalog of research-backed metrics | Far more built-in metrics (G-Eval, RAG, safety) and a hosted platform. Most metrics call an LLM judge, so CI runs need an API key. |
| [promptfoo](https://github.com/promptfoo/promptfoo) | config-driven prompt and model comparison with a web viewer and red-teaming | Better at side-by-side prompt/model comparison and adversarial testing, with a mature UI. Node-based, much larger surface. |
| [Ragas](https://github.com/explodinggradients/ragas) | research-grade RAG metrics plus synthetic test-set generation | Deeper RAG-specific measurement (faithfulness, context precision/recall). It is a metrics library, not a merge gate. |

`llm-eval-ci` stays in one lane: a regression gate built around a golden set you curated from your own traces, deterministic by default, small enough to read in one sitting before you let it gate your releases. If you need a metrics catalog, a comparison UI, or red-teaming, use the tools above; they are good at it.

## Wiring it into your CI

Copy-paste recipe for a consumer repo (adjust the three paths):

```yaml
name: LLM eval gate
on: [pull_request]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "git+https://github.com/omarnagy91/llm-eval-ci@v0.1.0"

      - name: Run eval gate
        # exit 1 fails this check and blocks the merge when quality regresses
        run: |
          llm-eval-ci run \
            --config eval/eval.yaml \
            --system eval/system.py \
            --baseline eval/baseline.json \
            --report eval-report.md \
            --summary

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: eval-report
          path: eval-report.md
```

`--summary` appends the markdown report to the GitHub job summary. This repo runs the same gate on itself: [.github/workflows/eval-gate.yml](.github/workflows/eval-gate.yml).

## Configuration reference

### `eval.yaml`

```yaml
name: my-eval                 # label used in reports
golden: golden.jsonl          # golden set path, relative to this file
judge: heuristic              # heuristic | openai | anthropic (backend for llm_judge graders)
judge_model: ""               # optional model id (default gpt-4o-mini / claude-haiku-4-5)
baseline: ""                  # optional baseline report json (CLI --baseline overrides)
gate_min_pass_rate: 0.9       # fraction of cases that must pass EVERY grader
gate_max_regression: 0.02     # max allowed drop vs baseline (overall and per grader mean)

graders:
  - type: grounding           # grounding | hallucination | relevance | tool_call | format | llm_judge
    threshold: 0.99           # per-grader pass bar, 0 to 1 (default 0.7)
  - type: format
    params: { json: true }    # or: params: { regex: "^Order #\\d+" }
  - type: llm_judge
    name: answer_quality      # optional display name (defaults to type)
    threshold: 0.7
    params:
      criteria: "a factual support answer, grounded only in the policy context"
```

API keys are read from the environment when a real judge backend is set: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. A judge backend error scores 0.0 with the error in the rationale; it never crashes the run.

### `golden.jsonl` (one case per line)

```json
{"id": "refund", "input": "What is your refund policy?",
 "context": ["Refunds: full refund within 14 days of purchase."],
 "reference": "You can request a full refund within 14 days of purchase.",
 "must_include": ["14 days"], "must_not_include": ["30 days"],
 "expected_tool": null, "labels": {"topic": "billing"}, "notes": ""}
```

### CLI

```text
llm-eval-ci run          --config eval.yaml (--system mod.py | --outputs out.jsonl)
                         [--baseline rep.json] [--report report.md] [--json rep.json]
                         [--name label] [--judge backend] [--judge-model id] [--summary]
llm-eval-ci golden build --traces traces.jsonl --out golden.jsonl [--sample N]
llm-eval-ci report       --json rep.json
```

`run` exits 0 when the gate passes and 1 when it fails. `--json` writes the machine-readable report you commit as the next baseline.

## Roadmap

- Publish to PyPI (today the install is from the git URL).
- Honor the grader `weight` field in gate aggregation, or remove it (it is currently parsed and unused, [#1](https://github.com/omarnagy91/llm-eval-ci/issues/1)).
- Per-label breakdown in reports; golden items already carry `labels`, reports ignore them ([#4](https://github.com/omarnagy91/llm-eval-ci/issues/4)).
- OpenAI-compatible `base_url` judge backend for local and self-hosted models ([#6](https://github.com/omarnagy91/llm-eval-ci/issues/6)).
- Fail loudly when `--outputs` is missing a golden id instead of grading an empty answer ([#2](https://github.com/omarnagy91/llm-eval-ci/issues/2)).

## Contributing

Bug reports, grader ideas, and small PRs are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the [good first issues](https://github.com/omarnagy91/llm-eval-ci/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22). Security reports go to the address in [SECURITY.md](SECURITY.md).

Dev loop:

```bash
pip install -e ".[dev]"
python -m pytest          # 3 tests, all offline, sub-second
bash scripts/demo.sh      # end-to-end check
```

## License and author

MIT, see [LICENSE](LICENSE).

Built by [Omar G. Nagy](https://omargnagy.com), AI Systems Engineer. I build evaluation harnesses and regression datasets for LLM, RAG, and agent products. If you want a golden set curated from your real failures and graders calibrated to your task, shipped as a CI gate your team owns: [omargnagy.com/work/llm-eval-ci](https://omargnagy.com/work/llm-eval-ci).
