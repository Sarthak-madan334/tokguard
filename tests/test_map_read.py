"""Unit tests for repo mapping, finding symbols, targeted reads and unchanged caching."""

import json
from pathlib import Path
import tg.map as map_module
from tg.budget import estimate_tokens, save_config
from tg.map import (
    generate_repo_map,
    find_symbol,
    read_range,
    read_symbol,
    extract_python_symbols,
)


def test_extract_python_symbols():
    code = """
class Calculator:
    def add(self, a, b):
        return a + b
    def subtract(self, a, b):
        return a - b

def helper():
    pass
"""
    symbols = extract_python_symbols(code)
    assert any("Calculator" in s and "add" in s for s in symbols)
    assert any("helper()" in s for s in symbols)


def test_repo_map_and_cache(tmp_path):
    # Setup sample files
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def run():\n    pass\n", encoding="utf-8")
    (src / "util.js").write_text("function formatDate() {}\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("var junk = 1;", encoding="utf-8")

    tree = generate_repo_map(tmp_path)
    assert "src/main.py" in tree
    assert "run()" in tree
    assert "src/util.js" in tree
    assert "node_modules" not in tree  # Ignored

    # Check cache file was created
    cache_file = tmp_path / ".tokguard" / "map.json"
    assert cache_file.exists()


def test_find_symbol(tmp_path):
    (tmp_path / "service.py").write_text(
        "def calculate_tax(amount):\n    rate = 0.05\n    return amount * rate\n",
        encoding="utf-8",
    )
    result = find_symbol("calculate_tax", root=tmp_path)
    assert "service.py:1" in result
    assert "calculate_tax(amount)" in result


def test_find_symbol_compact_default_and_optional_context(tmp_path):
    (tmp_path / "service.py").write_text(
        "def target():\n    first = 1\n    second = 2\n    return first + second\n",
        encoding="utf-8",
    )
    compact = find_symbol("target", root=tmp_path)
    expanded = find_symbol("target", root=tmp_path, context=1)
    assert "service.py:1: def target():" in compact
    assert "first = 1" not in compact
    assert "first = 1" in expanded


def test_repo_map_scan_limits_return_partial_results_and_can_continue(tmp_path):
    (tmp_path / "a.py").write_text("def first(): pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def second(): pass\n", encoding="utf-8")

    limited = generate_repo_map(tmp_path, max_scan_files=1)
    assert ("a.py" in limited) != ("b.py" in limited)
    assert "Partial results: scan file limit" in limited

    continued = generate_repo_map(tmp_path, max_scan_files=2)
    assert "a.py" in continued
    assert "b.py" in continued
    assert "Partial results" not in continued


def test_find_symbol_scan_limits_report_partial_results(tmp_path):
    (tmp_path / "a.txt").write_text("no match here\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("target marker\n", encoding="utf-8")

    limited = find_symbol("target", root=tmp_path, max_scan_files=1)
    assert "Partial results: scan file limit" in limited

    continued = find_symbol("target", root=tmp_path, max_scan_files=2)
    assert "b.txt:1" in continued
    assert "Partial results" not in continued


def test_scan_byte_limit_and_time_limit(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("target\n", encoding="utf-8")

    byte_limited = find_symbol("target", root=tmp_path, max_scan_bytes=2)
    assert "Partial results: scan byte limit" in byte_limited
    map_byte_limited = generate_repo_map(tmp_path, max_scan_bytes=2)
    assert "Partial results: scan byte limit" in map_byte_limited

    ticks = iter([0.0, 1.0])
    monkeypatch.setattr(map_module.time, "monotonic", lambda: next(ticks, 1.0))
    time_limited = generate_repo_map(tmp_path, max_scan_seconds=0.01)
    assert "Partial results: scan time limit" in time_limited

    ticks = iter([0.0, 1.0])
    monkeypatch.setattr(map_module.time, "monotonic", lambda: next(ticks, 1.0))
    time_limited_find = find_symbol("absent", root=tmp_path, max_scan_seconds=0.01)
    assert "Partial results: scan time limit" in time_limited_find


def test_repo_map_focus_is_confined_and_relative(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def run():\n    pass\n", encoding="utf-8")
    (tmp_path / "root.py").write_text("def root():\n    pass\n", encoding="utf-8")
    focused = generate_repo_map(tmp_path, focus="src")
    assert "main.py" in focused
    assert "src/main.py" in focused
    assert "root.py" not in focused
    assert "inside" in generate_repo_map(tmp_path, focus="../outside")


def test_read_range_and_unchanged_detection(tmp_path):
    file_path = tmp_path / "module.py"
    file_path.write_text("line1\nline2\nline3\nline4\nline5\n", encoding="utf-8")

    # First read
    first = read_range("module.py", 2, 4, root=tmp_path)
    assert "line2" in first
    assert "line3" in first
    assert "line4" in first
    assert "unchanged" not in first

    # Second read without modifying file
    second = read_range("module.py", 2, 4, root=tmp_path)
    assert "[unchanged since last read: lines 2-4 of 5 in module.py]" in second

    different_range = read_range("module.py", 1, 1, root=tmp_path)
    assert "line1" in different_range
    assert "unchanged" not in different_range
    assert "unchanged since last read" in read_range("module.py", 1, 1, root=tmp_path)

    # Modify file
    file_path.write_text("line1\nmodified line2\nline3\nline4\nline5\n", encoding="utf-8")
    third = read_range("module.py", 2, 4, root=tmp_path)
    assert "modified line2" in third
    assert "unchanged" not in third


def test_read_symbol(tmp_path):
    code = """
def process_data(items):
    # Process items
    total = 0
    for x in items:
        total += x
    return total

def other():
    pass
"""
    (tmp_path / "data.py").write_text(code, encoding="utf-8")
    read_range("data.py", 1, 1, root=tmp_path)
    out = read_symbol("data.py", "process_data", root=tmp_path)
    assert "def process_data(items):" in out
    assert "return total" in out
    assert "def other():" not in out
    assert "unchanged" not in out
    assert "unchanged since last read" in read_symbol("data.py", "process_data", root=tmp_path)


def test_file_reads_and_find_context_respect_token_limit(tmp_path):
    (tmp_path / ".tokguard").mkdir()
    save_config({"max_file_read_tokens": 120}, root=tmp_path)
    source = "\n".join(f"def item_{i}(): return '{'x' * 40}'" for i in range(30))
    symbol_source = "def large_symbol():\n" + "\n".join(
        f"    value_{i} = '{'x' * 40}'" for i in range(30)
    )
    (tmp_path / "module.py").write_text(source, encoding="utf-8")
    (tmp_path / "symbol.py").write_text(symbol_source, encoding="utf-8")

    range_output = read_range("module.py", 1, 30, root=tmp_path)
    symbol_output = read_symbol("symbol.py", "large_symbol", root=tmp_path)
    find_output = find_symbol("item_", root=tmp_path, max_results=30, context=1)

    assert estimate_tokens(range_output) <= 120
    assert "next chunk: tg read module.py --range" in range_output
    assert estimate_tokens(symbol_output) <= 120
    assert "next chunk: tg read symbol.py --range" in symbol_output
    assert estimate_tokens(find_output) <= 120
    assert "next chunk: tg find --offset" in find_output
    next_find_chunk = find_symbol("item_", root=tmp_path, max_results=2, offset=1)
    assert "module.py:2" in next_find_chunk
    assert "module.py:1" not in next_find_chunk


def test_repository_tools_reject_symlinks_outside_root(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text("def external_secret_marker():\n    pass\n", encoding="utf-8")
    (tmp_path / "linked.py").symlink_to(outside)

    assert "outside repository root" in read_range("linked.py", 1, 2, root=tmp_path)
    assert "outside repository root" in read_symbol("linked.py", "external_secret_marker", root=tmp_path)
    assert "No matches found" in find_symbol("external_secret_marker", root=tmp_path)
    assert "linked.py" not in generate_repo_map(tmp_path)


def test_repository_tools_allow_symlinks_inside_root(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("def internal_marker():\n    pass\n", encoding="utf-8")
    (tmp_path / "linked.py").symlink_to(target)
    (tmp_path / "range_link.py").symlink_to(target)

    assert "internal_marker" in read_range("range_link.py", 1, 2, root=tmp_path)
    assert "internal_marker" in read_symbol("linked.py", "internal_marker", root=tmp_path)
    assert "linked.py:1" in find_symbol("internal_marker", root=tmp_path)
    assert "linked.py: internal_marker()" in generate_repo_map(tmp_path)
