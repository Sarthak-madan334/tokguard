"""Unit test for external codex_guarded process termination and handoff."""

from pathlib import Path
from types import SimpleNamespace
import json
import subprocess
import sys

from tg import manager
import scripts.codex_guarded as guarded
from scripts.codex_guarded import run_guarded


def test_guarded_does_not_stop_on_token_usage(tmp_path, capsys):
    py_code = "print('tokens: 200000'); print('A' * 20000)"
    cmd = f'"{sys.executable}" -c "{py_code}"'

    exit_code = run_guarded(cmd, "long task", cwd=tmp_path)

    assert exit_code == 0
    assert not (tmp_path / ".tokguard" / "handoff.md").exists()
    output = capsys.readouterr().out
    assert "HARD STOP" not in output
    assert "Completed in" in output


def test_guarded_drift_check_parses_json_with_status_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr(
        guarded.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='{"level":"OFF TRACK","score":73}\n[tg: 1k tokens | drift 73 OFF | step 2/4]'),
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
    code = run_guarded(command, "watch drift", drift_interval=0.2, cwd=tmp_path)
    assert code != 0
    handoff = (tmp_path / ".tokguard" / "handoff.md").read_text(encoding="utf-8")
    assert "Drift report:" in handoff
    assert prompt in handoff

