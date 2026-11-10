"""Unit tests for tg/run.py compression and execution."""

import os
from pathlib import Path
from tg.run import (
    strip_ansi,
    normalize_line_endings,
    collapse_blank_lines,
    collapse_repeated_lines,
    filter_progress_lines,
    compress_output,
    execute_and_compress,
)


def test_strip_ansi():
    raw = "\x1b[31mError:\x1b[0m \x1b[1mFile not found\x1b[0m"
    assert strip_ansi(raw) == "Error: File not found"


def test_normalize_line_endings_spinners():
    raw = "Spinning: /\rSpinning: -\rSpinning: \\\rDone!"
    assert normalize_line_endings(raw) == "Done!"


def test_collapse_blank_lines():
    lines = ["a", "", "   ", "", "b", "", "c", "", ""]
    collapsed = collapse_blank_lines(lines)
    assert collapsed == ["a", "", "b", "", "c", ""]


def test_collapse_repeated_lines():
    lines = ["info: ping", "info: ping", "info: ping", "info: ping", "info: pong"]
    collapsed = collapse_repeated_lines(lines)
    assert len(collapsed) == 3
    assert collapsed[0] == "info: ping"
    assert "repeated x3" in collapsed[1]
    assert collapsed[2] == "info: pong"


def test_filter_progress_lines():
    lines = [
        "Fetching packages...",
        "Downloading [====>     ] 45% (1.2 MB/s)",
        "Downloading [=========>] 100% (2.4 MB/s)",
        "Unpacking files...",
    ]
    filtered = filter_progress_lines(lines)
    assert len(filtered) == 2
    assert "Fetching packages..." in filtered
    assert "Unpacking files..." in filtered


def test_pytest_profile_success():
    raw = "\n".join([
        "test_one.py .",
        "test_two.py ..",
        "================ 3 passed in 0.12s ================",
    ])
    compressed = compress_output(raw, "pytest tests/", exit_code=0)
    assert "3 passed in 0.12s" in compressed
    assert "test_one.py" not in compressed  # Filtered non-summary in success


def test_pytest_profile_failure_with_error_context():
    lines = [
        "test_one.py F",
        "=" * 20 + " FAILURES " + "=" * 20,
        "___ test_one ___",
        "    def test_one():",
        ">       assert 1 == 2",
        "E       AssertionError: assert 1 == 2",
        "test_one.py:5: AssertionError",
        "=" * 20 + " 1 failed in 0.15s " + "=" * 20,
    ]
    raw = "\n".join(lines)
    compressed = compress_output(raw, "pytest tests/", exit_code=1)
    assert "AssertionError" in compressed
    assert "1 failed in 0.15s" in compressed


def test_hard_cap_preserves_error_context():
    # 300 lines with an error in the middle
    lines = [f"line {i}" for i in range(150)]
    lines.append("Traceback (most recent call last):")
    lines.append("  File 'app.py', line 42, in boom")
    lines.append("    raise RuntimeError('Fatal error in process')")
    lines.extend([f"tail {i}" for i in range(150)])
    raw = "\n".join(lines)

    compressed = compress_output(raw, "run_all.sh", exit_code=1, max_lines=50, max_chars=2000)
    assert "lines omitted" in compressed
    assert "RuntimeError('Fatal error in process')" in compressed
    assert "File 'app.py', line 42, in boom" in compressed  # Context preserved


def test_execute_and_compress(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out = execute_and_compress("python -c \"print('Hello from tokguard')\"")
    assert code == 0
    assert "Hello from tokguard" in out
    assert "[Raw log:" in out
    assert Path(".tokguard/raw").exists()

