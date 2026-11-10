"""Unit test for external codex_guarded process termination and handoff."""

from pathlib import Path
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

