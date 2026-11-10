"""Unit tests for tokguard MCP tools."""

from pathlib import Path
from tg.mcp_server import map as mcp_map, find as mcp_find, read_range as mcp_read_range, read_symbol as mcp_read_symbol, run as mcp_run
from tg.budget import reset_session


def test_mcp_map_and_find(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    (tmp_path / "hello.py").write_text("def say_hello():\n    return 'hi'\n", encoding="utf-8")

    map_out = mcp_map()
    assert "hello.py" in map_out
    assert "say_hello()" in map_out
    assert "[tg:" in map_out

    find_out = mcp_find("say_hello")
    assert "hello.py:1" in find_out
    assert "[tg:" in find_out


def test_mcp_read_range_and_symbol(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    code = "def greet(name):\n    # greeting\n    return f'Hello {name}'\n"
    (tmp_path / "greet.py").write_text(code, encoding="utf-8")

    sym_out = mcp_read_symbol("greet.py", "greet")
    assert "def greet(name):" in sym_out
    assert "[tg:" in sym_out


def test_mcp_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reset_session(tmp_path)
    run_out = mcp_run("python -c \"print('mcp run test')\"")
    assert "mcp run test" in run_out
    assert "[tg:" in run_out

