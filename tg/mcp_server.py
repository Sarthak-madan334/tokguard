"""tokguard MCP server exposing map, find, read_range, read_symbol, and run."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from tg.budget import (
    check_guard,
    get_status_line,
    record_action,
)
from tg.map import find_symbol, generate_repo_map, read_range as map_read_range, read_symbol as map_read_symbol
from tg.run import execute_and_compress

# Support both MCP 2.x (MCPServer) and 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer
    app = MCPServer("tokguard")
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("tokguard")


@app.tool()
def map() -> str:
    """Repo tree with outline symbols (classes/functions)."""
    action_key = "mcp:map"
    allowed, guard_msg = check_guard(action_key)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = generate_repo_map()
    record_action(action_key, res)
    status = get_status_line()
    return f"{guard_msg + '\n' if guard_msg else ''}{res}\n{status}"


@app.tool()
def find(query: str, max_results: int = 20) -> str:
    """Find symbol or regex with 1-line context (max 20 hits)."""
    action_key = f"mcp:find:{query}"
    allowed, guard_msg = check_guard(action_key)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = find_symbol(query, max_results=max_results)
    record_action(action_key, res)
    status = get_status_line()
    return f"{guard_msg + '\n' if guard_msg else ''}{res}\n{status}"


@app.tool()
def read_range(filepath: str, start: int, end: int) -> str:
    """Read line range from file with line numbers."""
    action_key = f"mcp:read_range:{filepath}:{start}-{end}"
    allowed, guard_msg = check_guard(action_key)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = map_read_range(filepath, start, end)
    record_action(action_key, res, file_touched=filepath)
    status = get_status_line()
    return f"{guard_msg + '\n' if guard_msg else ''}{res}\n{status}"


@app.tool()
def read_symbol(filepath: str, symbol_name: str) -> str:
    """Read full body of class/function by name."""
    action_key = f"mcp:read_symbol:{filepath}:{symbol_name}"
    allowed, guard_msg = check_guard(action_key)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = map_read_symbol(filepath, symbol_name)
    record_action(action_key, res, file_touched=filepath)
    status = get_status_line()
    return f"{guard_msg + '\n' if guard_msg else ''}{res}\n{status}"


@app.tool()
def run(command: str, max_lines: int = 120, max_chars: int = 6000, full: bool = False) -> str:
    """Run shell command with compressed output and raw log."""
    action_key = f"mcp:run:{command}"
    allowed, guard_msg = check_guard(action_key)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    code, output = execute_and_compress(
        command,
        max_lines=max_lines,
        max_chars=max_chars,
        full=full,
    )
    record_action(action_key, output)
    status = get_status_line()
    return f"{guard_msg + '\n' if guard_msg else ''}{output}\n{status}"


def main() -> None:
    """Run tokguard MCP server over stdio."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()

