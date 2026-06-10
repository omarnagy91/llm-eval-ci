from __future__ import annotations

import json

from .models import EvalReport


def to_markdown(rep: EvalReport) -> str:
    mark = "✅ PASS" if rep.gate_passed else "❌ FAIL"
    lines = [
        f"# LLM eval gate: {mark}",
        "",
        f"**Config:** `{rep.config_name}`  •  **System:** `{rep.system_name or 'n/a'}`",
        f"**Overall pass rate:** {rep.overall_pass_rate:.0%}  ({sum(1 for it in rep.items if it.passed)}/{len(rep.items)} cases pass every grader)",
        "",
        "| Grader | Mean score | Case pass rate |",
        "| --- | --- | --- |",
    ]
    for gn in rep.grader_scores:
        lines.append(f"| {gn} | {rep.grader_scores[gn]:.2f} | {rep.grader_pass_rate.get(gn, 0):.0%} |")

    if rep.baseline_delta:
        d = rep.baseline_delta.get("overall")
        if d is not None:
            lines += ["", f"**Vs baseline:** {d:+.0%} overall (baseline {rep.baseline_delta.get('baseline_pass_rate', 0):.0%})"]

    lines += ["", "## Gate decision", ""]
    for r in rep.gate_reasons:
        lines.append(f"- {r}")

    failing = [it for it in rep.items if not it.passed]
    if failing:
        lines += ["", "## Failing cases", ""]
        for it in failing:
            lines.append(f"### `{it.item_id}`")
            for g in it.grades:
                if not g.passed:
                    lines.append(f"- **{g.grader}** {g.score:.2f}: {g.rationale}")
            lines.append("")
    return "\n".join(lines)


def to_console(rep: EvalReport) -> str:
    mark = "PASS ✅" if rep.gate_passed else "FAIL ❌"
    out = [
        f"[llm-eval-ci] gate: {mark}  ({rep.system_name or rep.config_name})",
        f"  overall pass rate: {rep.overall_pass_rate:.0%}  "
        f"({sum(1 for it in rep.items if it.passed)}/{len(rep.items)})",
    ]
    for gn in rep.grader_scores:
        out.append(f"  - {gn:<14} mean={rep.grader_scores[gn]:.2f}  pass={rep.grader_pass_rate.get(gn, 0):.0%}")
    for r in rep.gate_reasons:
        out.append(f"  · {r}")
    out.append(
        "[llm-eval-ci] PASS: the gate passed, merge allowed" if rep.gate_passed
        else "[llm-eval-ci] FAIL: the gate failed the build (PR blocked)"
    )
    return "\n".join(out)


def write_json(rep: EvalReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rep.to_dict(), f, indent=2, ensure_ascii=False)


def write_markdown(rep: EvalReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_markdown(rep))
