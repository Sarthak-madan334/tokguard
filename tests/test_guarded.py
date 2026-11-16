"""Unit test for external codex_guarded process termination and handoff."""

from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys

from tg import manager
import scripts.codex_guarded as guarded
from scripts.codex_guarded import run_guarded


def test_guarded_hard_stop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # A script that produces 20,000 characters
    py_code = "import sys; print('A' * 20000); sys.stdout.flush()"
    cmd = f'python -c "{py_code}"'

    # Set tiny budget of 200 tokens (approx 800 chars)
    exit_code = run_guarded(cmd, "test runaway task", budget_limit=200)
    assert exit_code == 99  # Custom exit code for budget stop

    handoff = tmp_path / ".tokguard" / "handoff.md"
    assert handoff.exists()
    content = handoff.read_text(encoding="utf-8")
    assert "Interrupted by tokguard: test runaway task" in content


def test_guarded_drift_check_parses_json_with_status_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(
        guarded.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"level":"OFF TRACK","score":73}\n[tg: 1k/150k tokens | drift 73 OFF | step 2/4]'),
    )
    result = guarded._run_drift_check(tmp_path)
    assert result["level"] == "OFF TRACK"
    assert result["score"] == 73


def test_guarded_terminates_on_off_track_and_writes_contextual_handoff(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "TokGuard Test"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text(".tokguard/\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("baseline\n", encoding="utf-8")
    (tmp_path / "tg").mkdir()
    (tmp_path / "tg" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "README.md", "tg/core.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=tmp_path, check=True)
    prompt = "Add task drift detection to TokGuard."
    manager.lock_prompt(prompt, tmp_path, announce=False)
    order = {
        "objective": prompt,
        "acceptance_criteria": ["command passes: python --version", "file exists: tg/core.py"],
        "in_scope": ["tg/"], "out_of_scope": ["no unrelated files", "no dependency changes"],
        "steps": [
            {"id":"one", "text":"Measure drift", "expected":"tg/manager.py"},
            {"id":"two", "text":"Stop unsafe work", "expected":"scripts/codex_guarded.py"},
            {"id":"three", "text":"Verify the task", "expected":"python --version"},
        ],
        "risks": ["Out-of-scope edits may be missed"], "max_files_changed": 1,
        "max_diff_lines": 100, "verify_command": "python --version",
        "assumptions": ["The request targets the existing Python CLI and toolkit."],
    }
    manager.submit_order(json.dumps(order), tmp_path, announce=False)
    for name in ("one.py", "two.py", "three.py"):
        (tmp_path / name).write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    script = "import time; print('started', flush=True); time.sleep(30)"
    command = f'"{sys.executable}" -c "{script}"'
    code = run_guarded(command, "watch drift", 100000, drift_interval=0.2, cwd=tmp_path)
    assert code != 0
    handoff = (tmp_path / ".tokguard" / "handoff.md").read_text(encoding="utf-8")
    assert "Drift report:" in handoff
    assert prompt in handoff

