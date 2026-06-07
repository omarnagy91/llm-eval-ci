from __future__ import annotations

import importlib.util
import json
import os

from .config import EvalConfig
from .graders import build_grader
from .ingest import load_golden
from .models import EvalReport, GoldenItem, ItemResult


def _resolve(path: str, base_dir: str) -> str:
    return path if os.path.isabs(path) else os.path.join(base_dir, path)


def _load_system(path: str):
    spec = importlib.util.spec_from_file_location("system_under_test", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load system module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _system_output(mod, item: GoldenItem):
    if hasattr(mod, "respond_full"):
        r = mod.respond_full({"input": item.input, "context": item.context, "id": item.id})
        return r.get("output", ""), r.get("tool_calls", [])
    if hasattr(mod, "respond"):
        out = mod.respond(item.input, item.context)
        if isinstance(out, dict):
            return out.get("output", ""), out.get("tool_calls", [])
        return out, []
    raise AttributeError("system module must define respond(input, context) or respond_full(item)")


def _load_outputs(path: str) -> dict:
    m = {}
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                d = json.loads(ln)
                m[str(d.get("id"))] = (d.get("output", ""), d.get("tool_calls", []))
    return m


def run_eval(cfg: EvalConfig, base_dir: str = ".", system: str | None = None,
             outputs: str | None = None, system_name: str = "") -> EvalReport:
    items = load_golden(_resolve(cfg.golden, base_dir))
    graders = [build_grader(gc, cfg.judge, cfg.judge_model) for gc in cfg.graders]

    # --system / --outputs are CLI args, relative to the caller's CWD (not the config dir);
    # only paths referenced *inside* the config (golden, baseline) are config-relative.
    out_map = _load_outputs(outputs) if outputs else None
    mod = _load_system(system) if system else None
    if out_map is None and mod is None:
        raise ValueError("provide a system module (--system) or precomputed outputs (--outputs)")

    results: list[ItemResult] = []
    for it in items:
        if out_map is not None:
            output, tool_calls = out_map.get(it.id, ("", []))
        else:
            output, tool_calls = _system_output(mod, it)
        grades = [g.grade(it, output, tool_calls) for g in graders]
        results.append(ItemResult(item_id=it.id, output=output, grades=grades))

    baseline = None
    if cfg.baseline:
        # CLI --baseline is CWD-relative; a baseline set inside the yaml is config-relative.
        bpath = cfg.baseline if os.path.exists(cfg.baseline) else _resolve(cfg.baseline, base_dir)
        if os.path.exists(bpath):
            baseline = json.load(open(bpath, "r", encoding="utf-8"))

    return _aggregate(cfg, results, system_name, baseline)


def _aggregate(cfg: EvalConfig, results: list[ItemResult], system_name: str,
               baseline: dict | None) -> EvalReport:
    rep = EvalReport(config_name=cfg.name, system_name=system_name, items=results)
    n = len(results) or 1

    grader_names: list[str] = []
    for it in results:
        for g in it.grades:
            if g.grader not in grader_names:
                grader_names.append(g.grader)

    for gn in grader_names:
        scores = [g.score for it in results for g in it.grades if g.grader == gn]
        passes = [g.passed for it in results for g in it.grades if g.grader == gn]
        rep.grader_scores[gn] = round(sum(scores) / len(scores), 4) if scores else 0.0
        rep.grader_pass_rate[gn] = round(sum(1 for p in passes if p) / len(passes), 4) if passes else 0.0

    rep.overall_pass_rate = round(sum(1 for it in results if it.passed) / n, 4)

    gate = True
    reasons: list[str] = []

    if rep.overall_pass_rate < cfg.gate_min_pass_rate:
        gate = False
        reasons.append(
            f"overall pass rate {rep.overall_pass_rate:.0%} below required {cfg.gate_min_pass_rate:.0%}"
        )

    if baseline:
        prev = float(baseline.get("overall_pass_rate", 0.0))
        delta = round(rep.overall_pass_rate - prev, 4)
        rep.baseline_delta["overall"] = delta
        rep.baseline_delta["baseline_pass_rate"] = prev
        if delta < -cfg.gate_max_regression:
            gate = False
            reasons.append(
                f"regression vs baseline: {delta:+.0%} (baseline {prev:.0%}, "
                f"max allowed -{cfg.gate_max_regression:.0%})"
            )
        for gn, score in rep.grader_scores.items():
            prev_g = baseline.get("grader_scores", {}).get(gn)
            if prev_g is not None:
                dg = round(score - float(prev_g), 4)
                if dg < -cfg.gate_max_regression:
                    gate = False
                    reasons.append(f"grader '{gn}' regressed {dg:+.2f} vs baseline")

    rep.gate_passed = gate
    rep.gate_reasons = reasons if reasons else ["all gate checks passed"]
    return rep
