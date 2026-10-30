import os
import tempfile
import textwrap

from llm_eval_ci.cli import main
from llm_eval_ci.models import GoldenItem
from llm_eval_ci.validate import validate_golden


def _item(**kw):
    base = dict(id="a", input="q", reference="ans", must_include=[], must_not_include=[])
    base.update(kw)
    return GoldenItem(**base)


def test_validate_ok_example_golden():
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "rag_support_bot", "golden.jsonl")
    # password_reset has expected_tool; without --system that is a warning only
    issues = validate_golden(
        __import__("llm_eval_ci.ingest", fromlist=["load_golden"]).load_golden(path),
        system_has_respond_full=True,
    )
    assert issues == []


def test_validate_detects_unscoreable_and_overlap_and_dupes():
    items = [
        _item(id="dup", reference="x"),
        _item(id="dup", reference="y"),
        _item(id="empty", reference="", must_include=[]),
        _item(id="clash", reference="ok", must_include=["14 days"], must_not_include=["14 days"]),
        _item(id="tool", reference="ok", expected_tool="reset_password"),
    ]
    issues = validate_golden(items, system_has_respond_full=False)
    msgs = [(i.severity, i.case_id, i.message) for i in issues]
    assert any(s == "warning" and c == "dup" and "duplicate" in m for s, c, m in msgs)
    assert any(s == "error" and c == "empty" and "unscoreable" in m for s, c, m in msgs)
    assert any(s == "warning" and c == "clash" and "must_include" in m for s, c, m in msgs)
    assert any(s == "warning" and c == "tool" and "respond_full" in m for s, c, m in msgs)


def test_cli_golden_validate_exits_nonzero_on_unscoreable():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "bad.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"id": "x", "input": "hi", "reference": "", "must_include": []}\n')
        code = main(["golden", "validate", "--golden", path])
        assert code == 1


def test_cli_golden_validate_ok():
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "rag_support_bot", "golden.jsonl")
    sys_path = os.path.join(os.path.dirname(__file__), "..", "examples", "rag_support_bot", "system_v1.py")
    code = main(["golden", "validate", "--golden", path, "--system", sys_path])
    assert code == 0
