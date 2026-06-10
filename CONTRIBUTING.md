# Contributing to llm-eval-ci

Thanks for considering a contribution. This project values small, readable, deterministic code, and it tries to stay that way.

## Ground rules

- **Keep the core small.** The whole package is about 660 lines of Python with one runtime dependency (PyYAML). A change that adds a dependency or a large new surface needs an issue and a short discussion first.
- **Deterministic by default.** Anything that runs in CI must work offline with no API key and produce the same result on every run. LLM-backed behavior belongs behind an explicit opt-in (like the `openai` / `anthropic` judge backends).
- **Tests for behavior.** If your change alters what the gate passes or fails, add or extend a test in `tests/`. The suite is offline and runs in under a second; there is no excuse to skip it.
- **No em dashes in docs or user-facing strings.** Use commas, colons, periods, or parentheses. House style.

## Dev setup

```bash
git clone https://github.com/omarnagy91/llm-eval-ci && cd llm-eval-ci
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest            # 3 tests, all offline
bash scripts/demo.sh        # end-to-end: v1 passes, v2 fails with exit 1
```

Supported Python: 3.10 and newer. CI runs the suite on 3.10, 3.11, and 3.12.

## Making a change

1. Open or pick an issue. For anything beyond a small fix, say what you plan to do before writing it.
2. Fork, branch, and make the change. Match the existing style: type hints, dataclasses, standard library first.
3. Run `python -m pytest` and `bash scripts/demo.sh`. Both must pass (the demo's v2 run is supposed to fail the gate; the script itself exits 0).
4. Open a PR using the template. Describe the behavior change, not just the diff.

## What makes a good first contribution

Issues labeled [good first issue](https://github.com/omarnagy91/llm-eval-ci/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) are scoped to one file or one function and have acceptance criteria written out. Grader improvements, CLI ergonomics, and report formatting are all friendly territory. New grader types are welcome when they are deterministic and configurable from `eval.yaml`.

## Reporting bugs

Use the bug report template. The most useful artifact is a minimal `eval.yaml` plus one or two golden lines that reproduce the problem, with the command you ran and the output you got.

## Security issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).
