import os

from llm_eval_ci.config import load_config
from llm_eval_ci.runner import run_eval

EX = os.path.join(os.path.dirname(__file__), "..", "examples", "rag_support_bot")


def _cfg():
    return load_config(os.path.join(EX, "eval.yaml"))


def test_v1_passes_gate():
    rep = run_eval(_cfg(), base_dir=EX, system=os.path.join(EX, "system_v1.py"), system_name="v1")
    assert rep.gate_passed is True
    assert rep.overall_pass_rate == 1.0


def test_v2_regression_fails_gate():
    rep = run_eval(_cfg(), base_dir=EX, system=os.path.join(EX, "system_v2_regression.py"), system_name="v2")
    assert rep.gate_passed is False
    assert rep.overall_pass_rate < 0.5
    # the regression must be caught by the grounding / hallucination / tool graders
    assert rep.grader_scores["hallucination"] < 1.0
    assert rep.grader_scores["grounding"] < 1.0


def test_baseline_regression_detected():
    cfg = _cfg()
    base = run_eval(cfg, base_dir=EX, system=os.path.join(EX, "system_v1.py"), system_name="v1")
    import tempfile, json
    from llm_eval_ci.report import write_json
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        write_json(base, f.name)
        cfg.baseline = f.name
    rep = run_eval(cfg, base_dir=EX, system=os.path.join(EX, "system_v2_regression.py"), system_name="v2")
    assert rep.gate_passed is False
    assert rep.baseline_delta["overall"] < 0
