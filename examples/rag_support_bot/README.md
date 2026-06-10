# Example: support-bot regression gate

A tiny "Nimbus" SaaS support bot grounded in 6 policy facts. It shows the whole loop:
real traces → curated golden set → graders → CI gate.

## Run it

```bash
pip install -e .          # from the repo root
bash scripts/demo.sh
```

You'll see:

- **`system_v1.py`** (answers grounded in the docs) → **gate PASS** (exit 0), writes `baseline.json`.
- **`system_v2_regression.py`** (a "helpful" rewrite that silently invented a *30-day* refund window, *unlimited* storage, the wrong price + region, and dropped the password-reset tool call) → **gate FAIL** (exit 1), with a regression flagged against the v1 baseline.

That non-zero exit is the entire product: it's what blocks the bad PR from merging.

## Files

| File | What it is |
| --- | --- |
| `traces.jsonl` | raw production logs (input/output/context/tool_calls) |
| `golden.jsonl` | the curated regression set, the judgment-heavy asset |
| `eval.yaml` | which graders run, their thresholds, and the gate |
| `system_v1.py` / `system_v2_regression.py` | the "system under test" (good vs regressed) |

Build a golden scaffold from your own logs:

```bash
python -m llm_eval_ci.cli golden build --traces examples/rag_support_bot/traces.jsonl --out my_golden.jsonl --sample 5
```
