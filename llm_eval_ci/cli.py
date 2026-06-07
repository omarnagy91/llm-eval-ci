from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__
from .config import load_config
from .ingest import load_traces, load_golden, write_golden
from .models import GoldenItem
from .report import to_console, to_markdown, write_json, write_markdown
from .runner import run_eval


def _cmd_run(args) -> int:
    cfg = load_config(args.config)
    if args.judge:
        cfg.judge = args.judge
    if args.judge_model:
        cfg.judge_model = args.judge_model
    if args.baseline:
        cfg.baseline = args.baseline
    base_dir = os.path.dirname(os.path.abspath(args.config))
    system_name = args.name or (os.path.basename(args.system) if args.system else "outputs")

    rep = run_eval(cfg, base_dir=base_dir, system=args.system,
                   outputs=args.outputs, system_name=system_name)

    print(to_console(rep))
    if args.report:
        write_markdown(rep, args.report)
        print(f"[llm-eval-ci] wrote {args.report}")
    if args.json:
        write_json(rep, args.json)
        print(f"[llm-eval-ci] wrote {args.json}")
    if args.summary and os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(to_markdown(rep) + "\n")

    # The CI gate: non-zero exit fails the PR check.
    return 0 if rep.gate_passed else 1


def _cmd_golden_build(args) -> int:
    """Scaffold a golden set from production traces for human curation.

    This deliberately does NOT auto-label correctness — the judgment about what
    'correct' means is the human's job and the actual asset. It pre-fills the
    structure (and seeds `must_include` from the logged output) so curation is fast."""
    traces = load_traces(args.traces)
    if args.sample and args.sample < len(traces):
        # deterministic, even spread across the log (no randomness)
        step = len(traces) / args.sample
        traces = [traces[int(i * step)] for i in range(args.sample)]
    items = [
        GoldenItem(
            id=t.id,
            input=t.input,
            context=t.context,
            reference=t.output,                 # logged answer = starting point for the human
            must_include=[],
            must_not_include=[],
            expected_tool=(t.tool_calls[0].get("name") if t.tool_calls else None),
            notes="REVIEW: confirm reference is correct; add must_include / must_not_include facts.",
        )
        for t in traces
    ]
    write_golden(args.out, items)
    print(f"[llm-eval-ci] scaffolded {len(items)} golden cases -> {args.out}")
    print("  Next: curate each case — confirm the reference, add required facts and hallucination traps.")
    return 0


def _cmd_report(args) -> int:
    d = json.load(open(args.json, "r", encoding="utf-8"))
    print(f"# {d.get('config_name')} — {'PASS' if d.get('gate_passed') else 'FAIL'}")
    print(f"overall pass rate: {d.get('overall_pass_rate', 0):.0%}")
    for gn, sc in (d.get("grader_scores") or {}).items():
        print(f"  - {gn}: {sc:.2f}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="llm-eval-ci", description="Golden-set regression eval + CI quality gate for LLM systems.")
    p.add_argument("--version", action="version", version=f"llm-eval-ci {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the eval and fail (exit 1) if the gate does not pass")
    r.add_argument("--config", required=True, help="eval.yaml")
    r.add_argument("--system", help="path to a python module exposing respond(input, context)")
    r.add_argument("--outputs", help="precomputed outputs jsonl ({id, output, tool_calls})")
    r.add_argument("--judge", help="override judge backend: heuristic|openai|anthropic")
    r.add_argument("--judge-model", dest="judge_model", help="override judge model id")
    r.add_argument("--baseline", help="baseline report json to check regressions against")
    r.add_argument("--report", help="write a markdown report to this path")
    r.add_argument("--json", help="write a machine-readable json report (use as next baseline)")
    r.add_argument("--name", help="label for the system under test")
    r.add_argument("--summary", action="store_true", help="append markdown to $GITHUB_STEP_SUMMARY")
    r.set_defaults(func=_cmd_run)

    g = sub.add_parser("golden", help="golden-set tools")
    gsub = g.add_subparsers(dest="gcmd", required=True)
    gb = gsub.add_parser("build", help="scaffold a golden set from production traces")
    gb.add_argument("--traces", required=True, help="production traces jsonl")
    gb.add_argument("--out", required=True, help="output golden jsonl")
    gb.add_argument("--sample", type=int, default=0, help="sample N cases (deterministic spread)")
    gb.set_defaults(func=_cmd_golden_build)

    rp = sub.add_parser("report", help="re-render a json report")
    rp.add_argument("--json", required=True)
    rp.set_defaults(func=_cmd_report)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
