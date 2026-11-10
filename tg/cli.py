"""Unified CLI entry point for tokguard (tg)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tg.budget import (
    check_guard,
    get_status_line,
    record_action,
    load_config,
    save_config,
    reset_session,
    generate_handoff,
)
from tg.map import find_symbol, generate_repo_map, read_range, read_symbol
from tg.run import execute_and_compress
from tg.slim import slim_file
from tg.setup import setup_all

DEFAULT_TGIGNORE = """# tokguard ignore list
node_modules/
dist/
build/
.git/
.tokguard/
.venv/
venv/
__pycache__/
*.pyc
*.min.js
*.min.css
*.map
*.log
*.lock
package-lock.json
pnpm-lock.yaml
yarn.lock
*.svg
*.png
*.jpg
*.jpeg
*.gif
*.ico
*.pdf
*.zip
*.tar.*
"""

AGENTS_MD_CONTENT = """# AGENTS.md - Context & Token Rules for tokguard
- Search before reading: use `tg find <symbol>` or `rg` first; read only needed ranges (never whole files >200 lines).
- Never re-read an unchanged file; remember contents or check `tg read` unchanged notice.
- Run shell commands via `tg run -- <cmd>` for compressed output and raw log persistence.
- Batch independent commands into a single execution step.
- Replies: terse. No restating code just written, no diff recaps, no pleasantries. Output unified diffs, not full files. Ask no unnecessary confirmation questions.
- Do not explore the repo broadly; start from `tg map`.
- When `tg` reports BUDGET WARNING, wrap up in <=10 lines and ask user before continuing.
- When `tg` reports BUDGET EXCEEDED, stop tool use immediately and generate handoff.
"""

MCP_CONFIG_HELP = """
=== tokguard setup ===

Run `npx -y tokguard setup` to connect Codex, Claude Code, and Antigravity
for all projects on this machine. Existing settings are preserved.
Restart the assistants after setup.
"""


def cmd_init() -> int:
    """Initialize tokguard in current directory."""
    root = Path(".")
    # 1. AGENTS.md, CLAUDE.md, .cursorrules
    for name in ["AGENTS.md", "CLAUDE.md", ".cursorrules"]:
        p = root / name
        if not p.exists():
            p.write_text(AGENTS_MD_CONTENT, encoding="utf-8")
            print(f"Created {name}")
        else:
            print(f"Preserved existing {name}")

    # 2. .tgignore
    tgignore = root / ".tgignore"
    if not tgignore.exists():
        tgignore.write_text(DEFAULT_TGIGNORE, encoding="utf-8")
        print("Created .tgignore")

    # 3. .tokguard/config.json
    cfg = load_config(root)
    save_config(cfg, root)
    print("Created .tokguard/config.json")

    # 4. Print MCP snippets
    print(MCP_CONFIG_HELP)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Execute tg run."""
    command = " ".join(args.cmd)
    action_key = f"cmd:{command}"
    allowed, guard_msg = check_guard(action_key, override=args.override)

    if not allowed:
        print(guard_msg)
        return 1

    code, output = execute_and_compress(
        command,
        max_lines=args.max_lines,
        max_chars=args.max_chars,
        full=args.full,
    )

    record_action(action_key, output)
    status = get_status_line()

    out_parts = []
    if guard_msg:
        out_parts.append(guard_msg)
    out_parts.append(output)
    out_parts.append(status)

    print("\n".join(out_parts))
    return code


def cmd_map(args: argparse.Namespace) -> int:
    """Execute tg map."""
    action_key = "map"
    allowed, guard_msg = check_guard(action_key, override=args.override)
    if not allowed:
        print(guard_msg)
        return 1

    res = generate_repo_map()
    record_action(action_key, res)
    status = get_status_line()

    if guard_msg:
        print(guard_msg)
    print(res)
    print(status)
    return 0


def cmd_find(args: argparse.Namespace) -> int:
    """Execute tg find."""
    action_key = f"find:{args.query}"
    allowed, guard_msg = check_guard(action_key, override=args.override)
    if not allowed:
        print(guard_msg)
        return 1

    res = find_symbol(args.query, max_results=args.max)
    record_action(action_key, res)
    status = get_status_line()

    if guard_msg:
        print(guard_msg)
    print(res)
    print(status)
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """Execute tg read."""
    filepath = args.file
    override = getattr(args, "override", False)

    if args.symbol:
        action_key = f"read_symbol:{filepath}:{args.symbol}"
        allowed, guard_msg = check_guard(action_key, override=override)
        if not allowed:
            print(guard_msg)
            return 1
        res = read_symbol(filepath, args.symbol)
    elif args.range:
        m = args.range.split("-")
        try:
            start, end = int(m[0]), int(m[1])
        except Exception:
            print(f"Invalid range format '{args.range}'. Use start-end (e.g. 1-50)")
            return 1
        action_key = f"read_range:{filepath}:{args.range}"
        allowed, guard_msg = check_guard(action_key, override=override)
        if not allowed:
            print(guard_msg)
            return 1
        res = read_range(filepath, start, end)
    else:
        # Default read first 100 lines
        action_key = f"read:{filepath}:1-100"
        allowed, guard_msg = check_guard(action_key, override=override)
        if not allowed:
            print(guard_msg)
            return 1
        res = read_range(filepath, 1, 100)

    record_action(action_key, res, file_touched=filepath)
    status = get_status_line()

    if guard_msg:
        print(guard_msg)
    print(res)
    print(status)
    return 0


def cmd_slim(args: argparse.Namespace) -> int:
    """Execute tg slim."""
    p = Path(args.file)
    if not p.exists():
        print(f"Error: file not found '{args.file}'")
        return 1
    res = slim_file(p)
    print(res)
    return 0


def cmd_budget(args: argparse.Namespace) -> int:
    """Inspect or alter budget settings."""
    cfg = load_config()
    if args.reset:
        reset_session()
        print("Session tokens and history reset to 0.")
        print(get_status_line())
        return 0
    if args.set is not None:
        cfg["session_token_budget"] = args.set
        save_config(cfg)
        print(f"Updated session_token_budget to {args.set}.")
        print(get_status_line())
        return 0

    print("--- tokguard Budget Config ---")
    for k, v in cfg.items():
        print(f"  {k}: {v}")
    print(f"Current Status: {get_status_line()}")
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    """Generate session handoff file."""
    summary = " ".join(args.summary) if args.summary else "Agent task handoff"
    p = generate_handoff(summary)
    print(f"Wrote session handoff to {p.as_posix()} (<= 30 lines)")
    print(p.read_text(encoding="utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="tg",
        description="tokguard - token-saving toolkit for coding agents",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand")

    # init
    subparsers.add_parser("init", help="Initialize AGENTS.md, .tgignore and config")

    # setup
    subparsers.add_parser(
        "setup",
        help="Configure TokGuard globally for Codex, Claude Code and Antigravity",
    )

    # run
    run_parser = subparsers.add_parser("run", help="Execute and compress command output")
    run_parser.add_argument("--max-lines", type=int, default=120, help="Max lines of output")
    run_parser.add_argument("--max-chars", type=int, default=6000, help="Max characters of output")
    run_parser.add_argument("--full", action="store_true", help="Bypass compression")
    run_parser.add_argument("--override", action="store_true", help="Override budget hard stop")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute")

    # map
    map_parser = subparsers.add_parser("map", help="Display repo symbol outline map")
    map_parser.add_argument("--override", action="store_true", help="Override budget limit")

    # find
    find_parser = subparsers.add_parser("find", help="Find symbol or pattern")
    find_parser.add_argument("query", help="Symbol or regex to search")
    find_parser.add_argument("--max", type=int, default=20, help="Max results")
    find_parser.add_argument("--override", action="store_true", help="Override budget limit")

    # read
    read_parser = subparsers.add_parser("read", help="Read range or symbol from file")
    read_parser.add_argument("file", help="File to read")
    read_parser.add_argument("range", nargs="?", help="Start-end line range, e.g. 10-40")
    read_parser.add_argument("--symbol", help="Read specific symbol body")
    read_parser.add_argument("--override", action="store_true", help="Override budget limit")

    # slim
    slim_parser = subparsers.add_parser("slim", help="Strip comments and blank lines")
    slim_parser.add_argument("file", help="File to slim")

    # budget
    budget_parser = subparsers.add_parser("budget", help="Inspect or adjust budget")
    budget_parser.add_argument("--reset", action="store_true", help="Reset session tokens and history")
    budget_parser.add_argument("--set", type=int, help="Set session_token_budget")

    # handoff
    handoff_parser = subparsers.add_parser("handoff", help="Generate .tokguard/handoff.md")
    handoff_parser.add_argument("summary", nargs="*", help="Task summary")

    # Handle '--' in tg run
    # If "run" is the first arg and "--" appears, separate correctly
    if argv and argv[0] == "run":
        # Extract flags before '--'
        flags = []
        cmd_args = []
        found_dash_dash = False
        for a in argv[1:]:
            if a == "--" and not found_dash_dash:
                found_dash_dash = True
                continue
            if found_dash_dash:
                cmd_args.append(a)
            else:
                flags.append(a)
        parsed = run_parser.parse_args(flags)
        parsed.cmd = cmd_args if found_dash_dash else getattr(parsed, "cmd", [])
        return cmd_run(parsed)

    args = parser.parse_args(argv)
    if not args.subcommand:
        parser.print_help()
        return 0

    dispatch = {
        "init": lambda a: cmd_init(),
        "setup": lambda a: setup_all(),
        "run": cmd_run,
        "map": cmd_map,
        "find": cmd_find,
        "read": cmd_read,
        "slim": cmd_slim,
        "budget": cmd_budget,
        "handoff": cmd_handoff,
    }

    handler = dispatch.get(args.subcommand)
    if handler:
        return handler(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

