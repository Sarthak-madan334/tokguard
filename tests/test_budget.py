"""Unit tests for tokguard budget management, loop detection, and handoffs."""

from pathlib import Path
from tg.budget import (
    estimate_tokens,
    format_token_k,
    load_config,
    load_session,
    save_config,
    record_action,
    check_guard,
    get_status_line,
    generate_handoff,
    reset_session,
)


def test_estimate_tokens():
    text = "a" * 400
    assert estimate_tokens(text) == 100
    assert estimate_tokens("") == 0


def test_format_token_k():
    assert format_token_k(500) == "500"
    assert format_token_k(4500) == "4.5k"
    assert format_token_k(84000) == "84k"
    assert format_token_k(150000) == "150k"


def test_large_token_usage_never_warns_or_rolls_over(tmp_path):
    # Old limit settings must be ignored when loading existing config.
    cfg = load_config(tmp_path)
    cfg["session_token_budget"] = 1000
    cfg["warn_at"] = 0.5
    cfg["hard_stop_at"] = 1.0
    save_config(cfg, tmp_path)

    record_action("cmd:large-output", "a" * 40000, root=tmp_path)
    allowed, msg = check_guard("cmd:next-action", root=tmp_path)

    assert allowed is True
    assert msg is None
    assert "session_token_budget" not in load_config(tmp_path)
    assert load_session(tmp_path)["cumulative_tokens"] >= 10000
    assert "BUDGET WARNING" not in get_status_line(tmp_path)
    assert "/" not in get_status_line(tmp_path).split("tokens", 1)[0]
    assert not (tmp_path / ".tokguard" / "handoff.md").exists()
    assert not (tmp_path / ".tokguard" / "sessions").exists()


def test_loop_detection(tmp_path):
    reset_session(tmp_path)
    # Perform same action twice
    record_action("read:main.py:1-50", "content", root=tmp_path)
    record_action("read:main.py:1-50", "content", root=tmp_path)
    allowed, msg = check_guard("read:main.py:1-50", root=tmp_path)
    assert msg is None

    # Third time triggers loop warning
    record_action("read:main.py:1-50", "content", root=tmp_path)
    allowed, msg = check_guard("read:main.py:1-50", root=tmp_path)
    assert allowed is True
    assert msg is not None
    assert "LOOP DETECTED" in msg


def test_generate_handoff(tmp_path):
    record_action("cmd:git status", "status output", root=tmp_path, file_touched="app/main.py")
    handoff_path = generate_handoff("Fix authentication timeout bug", root=tmp_path)
    assert handoff_path.exists()
    content = handoff_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    assert len(lines) <= 30
    assert "tokguard Session Handoff" in content
    assert "Tokens Consumed" in content
    assert "/150k" not in content
    assert "Fix authentication timeout bug" in content
    assert "app/main.py" in content

