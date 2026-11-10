"""Unit tests for repo mapping, finding symbols, targeted reads and unchanged caching."""

import json
from pathlib import Path
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
    out = read_symbol("data.py", "process_data", root=tmp_path)
    assert "def process_data(items):" in out
    assert "return total" in out
    assert "def other():" not in out

