"""Unit tests for tokguard budget management, loop detection, and handoffs."""

from pathlib import Path
from tg.budget import (
    estimate_tokens,
    format_token_k,
    load_config,
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


def test_budget_warning_and_hard_stop(tmp_path):
    # Set small budget for testing
    cfg = load_config(tmp_path)
    cfg["session_token_budget"] = 1000  # 1000 tokens
    cfg["warn_at"] = 0.5
    cfg["hard_stop_at"] = 1.0
    save_config(cfg, tmp_path)

    # 1. Below warning
    record_action("cmd:pytest", "a" * 1600, root=tmp_path)  # 400 tokens = 40%
    allowed, msg = check_guard("cmd:pytest2", root=tmp_path)
    assert allowed is True
    assert msg is None

    # 2. At or above warn_at (50%)
    record_action("cmd:pytest2", "a" * 800, root=tmp_path)  # +200 tokens = 600 total (60%)
    allowed, msg = check_guard("cmd:pytest3", root=tmp_path)
    assert allowed is True
    assert msg is not None
    assert "BUDGET WARNING" in msg

    # 3. At or above hard_stop_at (100%)
    record_action("cmd:pytest3", "a" * 1800, root=tmp_path)  # +450 tokens = 1050 total (105%)
    allowed, msg = check_guard("cmd:pytest4", root=tmp_path)
    assert allowed is False
    assert "BUDGET EXCEEDED" in msg

    # 4. Override bypasses hard stop
    allowed_override, _ = check_guard("cmd:pytest4", override=True, root=tmp_path)
    assert allowed_override is True


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
    assert "Fix authentication timeout bug" in content
    assert "app/main.py" in content

