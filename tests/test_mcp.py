"""Unit tests for tokguard MCP tools."""

from pathlib import Path
from tg.mcp_server import map as mcp_map, find as mcp_find, read_range as mcp_read_range, read_symbol as mcp_read_symbol, run as mcp_run
from tg.mcp_server import plan_lock as mcp_plan_lock, plan_submit as mcp_plan_submit, check as mcp_check, step as mcp_step, scope_add as mcp_scope_add
from tg.budget import reset_session
import json


def test_mcp_map_and_find(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    (tmp_path / "hello.py").write_text("def say_hello():\n    return 'hi'\n", encoding="utf-8")

    map_out = mcp_map()
    assert "hello.py" in map_out
    assert "say_hello()" in map_out
    assert "[tg:" not in map_out

    find_out = mcp_find("say_hello")
    assert "hello.py:1" in find_out
    assert "[tg:" not in find_out


def test_mcp_read_range_and_symbol(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    code = "def greet(name):\n    # greeting\n    return f'Hello {name}'\n"
    (tmp_path / "greet.py").write_text(code, encoding="utf-8")

    sym_out = mcp_read_symbol("greet.py", "greet")
    assert "def greet(name):" in sym_out
    assert "[tg:" not in sym_out


def test_mcp_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    run_out = mcp_run("python -c \"print('mcp run test')\"")
    assert "mcp run test" in run_out
    assert "[tg:" not in run_out


def test_mcp_manager_tools_lock_submit_check_step_and_scope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    prompt = "Add a task manager to TokGuard that locks prompts and checks drift."
    assert "Prompt locked" in mcp_plan_lock(prompt)
    order = {
        "objective": prompt,
        "acceptance_criteria": ["command passes: python --version", "file exists: README.md"],
        "in_scope": ["tg/"],
        "out_of_scope": ["no dependencies", "no refactors"],
        "steps": [
            {"id": "one", "text": "Lock the task", "expected": "tg/manager.py"},
            {"id": "two", "text": "Measure drift", "expected": "tg/manager.py"},
            {"id": "three", "text": "Verify the result", "expected": "python --version"},
        ],
        "risks": ["Vague scope could cause drift"],
        "verify_command": "python --version",
    }
    assert "Work order submitted" in mcp_plan_submit(json.dumps(order))
    assert "DRIFT" in mcp_check()
    assert "Step one" in mcp_step("show")
    assert "Step one done" in mcp_step("done", step_id="one")
    assert "Scope added" in mcp_scope_add("tg/generated/", "The task explicitly requires this generated output.")

