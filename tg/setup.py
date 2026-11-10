"""Install TokGuard for supported coding assistants on this machine."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Callable


_START = "<!-- tokguard:begin -->"
_END = "<!-- tokguard:end -->"
_SERVER = {"command": "npx", "args": ["-y", "tokguard", "mcp"]}
_GUIDANCE = (
    "Use the TokGuard MCP tools for repository work when available. Start with `map`, "
    "then use `find` and targeted `read_range` or `read_symbol` calls. Use `run` for "
    "shell commands when appropriate, and avoid broad file dumps. Keep responses focused."
)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _upsert_guidance(path: Path) -> None:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    block = f"{_START}\n{_GUIDANCE}\n{_END}"
    if _START in old and _END in old:
        start = old.index(_START)
        end = old.index(_END, start) + len(_END)
        updated = old[:start] + block + old[end:]
    else:
        updated = old.rstrip()
        updated = f"{updated}\n\n{block}\n" if updated else f"{block}\n"
    if updated != old:
        _atomic_write(path, updated)


def _upsert_json_server(path: Path) -> None:
    data: dict[str, object] = {}
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("expected a JSON object")
        data = loaded
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise ValueError("mcpServers must be a JSON object")
    servers["tokguard"] = dict(_SERVER)
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _upsert_codex_server(path: Path) -> None:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    try:
        import tomllib  # Python 3.11+

        tomllib.loads(old)
    except ModuleNotFoundError:
        pass
    except Exception as exc:
        raise ValueError(f"existing TOML is invalid: {exc}") from exc

    kept: list[str] = []
    skip = False
    section_re = re.compile(r"^\s*\[([^\[\]]+)\]\s*(?:#.*)?$")
    for line in old.splitlines():
        match = section_re.match(line)
        if match:
            section = match.group(1).strip()
            skip = section == "mcp_servers.tokguard" or section.startswith(
                "mcp_servers.tokguard."
            )
        if not skip:
            kept.append(line)

    entry = "\n".join(
        [
            "[mcp_servers.tokguard]",
            'command = "npx"',
            'args = ["-y", "tokguard", "mcp"]',
            "startup_timeout_sec = 30",
            "",
            "[mcp_servers.tokguard.tools.map]",
            'approval_mode = "approve"',
            "",
            "[mcp_servers.tokguard.tools.find]",
            'approval_mode = "approve"',
            "",
            "[mcp_servers.tokguard.tools.read_range]",
            'approval_mode = "approve"',
            "",
            "[mcp_servers.tokguard.tools.read_symbol]",
            'approval_mode = "approve"',
            "",
        ]
    )
    base = "\n".join(kept).rstrip()
    updated = f"{base}\n\n{entry}" if base else entry
    if updated != old:
        _atomic_write(path, updated)


def setup_all() -> int:
    """Configure Codex, Claude Code, and Antigravity for all projects."""
    home = Path.home()
    codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(home / ".claude")))
    targets: list[tuple[str, Path, Callable[[Path], None]]] = [
        ("Codex MCP", codex_home / "config.toml", _upsert_codex_server),
        ("Claude Code MCP", home / ".claude.json", _upsert_json_server),
        (
            "Antigravity MCP",
            home / ".gemini" / "config" / "mcp_config.json",
            _upsert_json_server,
        ),
        ("Codex instructions", codex_home / "AGENTS.md", _upsert_guidance),
        ("Claude Code instructions", claude_home / "CLAUDE.md", _upsert_guidance),
        ("Antigravity instructions", home / ".gemini" / "GEMINI.md", _upsert_guidance),
    ]

    failed = False
    for label, path, update in targets:
        try:
            update(path)
            print(f"Configured {label}: {path}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            failed = True
            print(f"Skipped {label} ({path}): {exc}")

    print("\nRestart Codex, Claude Code, and Antigravity to load the MCP server.")
    return 1 if failed else 0
