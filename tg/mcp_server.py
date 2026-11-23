"""tokguard MCP server exposing map, find, read_range, read_symbol, and run."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
from contextlib import redirect_stdout
from io import StringIO
import json

from tg.budget import (
    check_guard,
    get_status_line,
    load_config,
    record_action,
)
from tg.map import find_symbol, generate_repo_map, read_range as map_read_range, read_symbol as map_read_symbol
from tg.run import execute_and_compress
from tg import manager

# Support both MCP 2.x (MCPServer) and 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer
    app = MCPServer("tokguard")
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP
    app = FastMCP("tokguard")


@app.tool()
def map(override: bool = False, focus: str = "") -> str:
    """Repo symbol outline; optionally focus on one repository directory."""
    action_key = f"mcp:map:{focus}"
    allowed, guard_msg = check_guard(action_key, override=override)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = generate_repo_map(focus=focus)
    record_action(action_key, res)
    status = get_status_line(only_changes=True)
    return "\n".join(part for part in (guard_msg, res, status) if part)


@app.tool()
def find(query: str, max_results: int = 5, override: bool = False, context: int = 0) -> str:
    """Find symbol or regex: 5 matching lines by default. Increase max_results or context to expand."""
    action_key = f"mcp:find:{query}:{max_results}:{context}"
    allowed, guard_msg = check_guard(action_key, override=override)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = find_symbol(query, max_results=max_results, context=context)
    record_action(action_key, res)
    status = get_status_line(only_changes=True)
    return "\n".join(part for part in (guard_msg, res, status) if part)


@app.tool()
def read_range(filepath: str, start: int, end: int, override: bool = False) -> str:
    """Read line range from file with line numbers."""
    action_key = f"mcp:read_range:{filepath}:{start}-{end}"
    allowed, guard_msg = check_guard(action_key, override=override)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = map_read_range(filepath, start, end)
    record_action(action_key, res, file_touched=filepath)
    status = get_status_line(only_changes=True)
    return "\n".join(part for part in (guard_msg, res, status) if part)


@app.tool()
def read_symbol(filepath: str, symbol_name: str, override: bool = False) -> str:
    """Read full body of class/function by name."""
    action_key = f"mcp:read_symbol:{filepath}:{symbol_name}"
    allowed, guard_msg = check_guard(action_key, override=override)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    res = map_read_symbol(filepath, symbol_name)
    record_action(action_key, res, file_touched=filepath)
    status = get_status_line(only_changes=True)
    return "\n".join(part for part in (guard_msg, res, status) if part)


@app.tool()
def run(command: str, max_lines: int = 120, max_chars: int = 6000, full: bool = False, override: bool = False) -> str:
    """Run shell command with compressed output and raw log."""
    action_key = f"mcp:run:{command}"
    allowed, guard_msg = check_guard(action_key, override=override)
    if not allowed:
        return guard_msg or "BUDGET EXCEEDED"

    code, output = execute_and_compress(
        command,
        max_lines=max_lines,
        max_chars=max_chars,
        full=full,
    )
    record_action(action_key, output)
    status = get_status_line(only_changes=True)
    return "\n".join(part for part in (guard_msg, output, status) if part)


@app.tool()
def plan_lock(prompt: str, new: bool = False, override: bool = False) -> str:
    """Lock the user's original task prompt verbatim before coding."""
    key = "mcp:plan_lock"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    try:
        path = manager.lock_prompt(prompt, new=new, announce=False)
        output = f"Prompt locked at {path.as_posix()}. Now write a manager work order and submit it with plan_submit."
    except (ValueError, OSError) as exc:
        output = f"plan_lock: {exc}"
    record_action(key, output)
    return f"{output}\n{get_status_line()}"


@app.tool()
def plan_submit(work_order_json: str, override: bool = False) -> str:
    """Validate and store the senior-manager work order as JSON."""
    key = "mcp:plan_submit"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    try:
        path = manager.submit_order(work_order_json, config=load_config(), announce=False)
        output = f"Work order submitted: {path.as_posix()}"
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        output = f"plan_submit: {exc}"
    record_action(key, output)
    return f"{output}\n{get_status_line()}"


@app.tool()
def check(override: bool = False) -> str:
    """Score task drift and return the next corrective instruction."""
    key = "mcp:check"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    output = StringIO()
    with redirect_stdout(output):
        manager.print_drift(manager.check_drift())
    text = output.getvalue().strip()
    record_action(key, text)
    return f"{text}\n{get_status_line()}"


@app.tool()
def step(action: str, step_id: str = "", note: str = "", text: str = "", reason: str = "", override: bool = False) -> str:
    """Show, complete, or add a manager work-order step."""
    key = f"mcp:step:{action}"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    output = StringIO()
    try:
        with redirect_stdout(output):
            if action == "show": manager.show_step()
            elif action == "done": manager.step_done(step_id, note=note)
            elif action == "add": manager.add_step(text, reason)
            else: raise ValueError("action must be show, done, or add")
    except (ValueError, OSError) as exc:
        output.write(f"step: {exc}\n")
    text_out = output.getvalue().strip()
    record_action(key, text_out)
    return f"{text_out}\n{get_status_line()}"


@app.tool()
def verify(override: bool = False) -> str:
    """Run the work-order verification and report each criterion."""
    key = "mcp:verify"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    output = StringIO()
    with redirect_stdout(output):
        code = manager.verify()
    text_out = output.getvalue().strip()
    record_action(key, f"exit={code}\n{text_out}")
    return f"{text_out}\n{get_status_line()}"


@app.tool()
def scope_add(path: str, reason: str, override: bool = False) -> str:
    """Add one justified path to the work-order scope and log the reason."""
    key = f"mcp:scope_add:{path}"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    output = StringIO()
    try:
        with redirect_stdout(output): manager.scope_add(path, reason)
    except (ValueError, OSError) as exc:
        output.write(f"scope_add: {exc}\n")
    text_out = output.getvalue().strip()
    record_action(key, text_out)
    return f"{text_out}\n{get_status_line()}"


@app.tool()
def revert_plan(execute: bool = False, override: bool = False) -> str:
    """Show or execute restore commands for out-of-scope changes."""
    key = "mcp:revert-plan"
    allowed, message = check_guard(key, override=override)
    if not allowed:
        return message or "Task manager is locked."
    output = StringIO()
    with redirect_stdout(output): manager.revert_plan(execute=execute)
    text_out = output.getvalue().strip()
    record_action(key, text_out)
    return f"{text_out}\n{get_status_line()}"


def main() -> None:
    """Run tokguard MCP server over stdio."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()

