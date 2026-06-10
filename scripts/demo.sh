#!/usr/bin/env bash
# Shows the gate passing on a grounded system, then FAILING (non-zero exit) on a
# silently-regressed one: the exact signal that blocks a bad PR from merging.
set -uo pipefail
cd "$(dirname "$0")/.."
EX=examples/rag_support_bot

# Pick a Python that can import the package's one dependency (PyYAML).
# Prefers $PYTHON, then a local .venv, then python / python3, whichever works.
# (Modern macOS has no bare `python`, so we can't hardcode it.)
PY=""
for cand in "${PYTHON:-}" ".venv/bin/python" python python3; do
  [ -z "$cand" ] && continue
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import yaml" >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "No Python with the package installed was found."
  echo "Set it up first:  python3 -m venv .venv && .venv/bin/pip install -e ."
  exit 1
fi
echo "(using: $PY)"
echo

echo "==> v1 (grounded answers): expect PASS, write baseline"
"$PY" -m llm_eval_ci.cli run --config $EX/eval.yaml --system $EX/system_v1.py \
  --name v1 --json $EX/baseline.json
echo "v1 exit=$?"

echo
echo "==> v2 (silently regressed): expect FAIL + regression vs the v1 baseline"
"$PY" -m llm_eval_ci.cli run --config $EX/eval.yaml --system $EX/system_v2_regression.py \
  --name v2 --baseline $EX/baseline.json --report $EX/last-report.md
echo "v2 exit=$?  (non-zero = the gate correctly failed the build)"
