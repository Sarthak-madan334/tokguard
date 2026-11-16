"""Budget guard, token tracking, loop detection, and session handoffs for tokguard."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_CONFIG = {
    "session_token_budget": 150000,
    "warn_at": 0.7,
    "hard_stop_at": 1.0,
    "drift_thresholds": {"minor": 21, "major": 46, "off": 71},
    "check_every_n_calls": 8,
    "max_files_changed": 8,
    "max_diff_lines": 300,
    "protected_globs": ["*lock*", ".github/**", ".gitlab-ci*", "package.json", "pyproject.toml", "*.config.*"],
    "allow_test_edits": False,
    "stall_calls": 12,
    "max_tool_output_tokens": 1500,
    "max_file_read_tokens": 2500,
}


def estimate_tokens(text: str) -> int:
    """Estimate token count: uses tiktoken if available, else chars / 4."""
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, math.ceil(len(text) / 4))


def format_token_k(count: int) -> str:
    """Format token number nicely: e.g. 84k or 150k."""
    if count >= 1000:
        val = count / 1000.0
        return f"{val:.1f}k" if val < 10 else f"{int(round(val))}k"
    return str(count)


def load_config(root: Path = Path(".")) -> dict:
    """Load config from .tokguard/config.json or create default."""
    cfg_path = root / ".tokguard" / "config.json"
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict, root: Path = Path(".")) -> None:
    """Save config to .tokguard/config.json."""
    cfg_path = root / ".tokguard" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def load_session(root: Path = Path(".")) -> dict:
    """Load session state from .tokguard/session.json."""
    session_path = root / ".tokguard" / "session.json"
    if session_path.exists():
        try:
            return json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "cumulative_tokens": 0,
        "history": [],
        "file_hashes": {},
        "files_touched": [],
    }


def save_session(session: dict, root: Path = Path(".")) -> None:
    """Save session state to .tokguard/session.json."""
    session_path = root / ".tokguard" / "session.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(session, indent=2), encoding="utf-8")


def reset_session(root: Path = Path(".")) -> None:
    """Reset the session counters and history."""
    save_session({
        "cumulative_tokens": 0,
        "history": [],
        "file_hashes": {},
        "files_touched": [],
    }, root=root)


def record_action(
    action_key: str,
    output_text: str,
    root: Path = Path("."),
    file_touched: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Record an action and its output tokens in session.
    Returns (used_tokens, budget).
    """
    session = load_session(root)
    cfg = load_config(root)

    tokens = estimate_tokens(output_text)
    session["cumulative_tokens"] = session.get("cumulative_tokens", 0) + tokens

    history: List[str] = session.setdefault("history", [])
    history.append(action_key)
    if len(history) > 100:
        session["history"] = history[-100:]

    if file_touched:
        files: List[str] = session.setdefault("files_touched", [])
        if file_touched not in files:
            files.append(file_touched)

    session["manager_call_count"] = session.get("manager_call_count", max(0, len(history) - 1)) + 1

    save_session(session, root)
    if (root / ".tokguard" / "task.json").exists():
        try:
            from tg.manager import checkpoint
            cadence = max(1, int(cfg.get("check_every_n_calls", 8)))
            if session["manager_call_count"] % cadence == 0 or action_key.startswith(("cmd:", "mcp:run:")):
                checkpoint(root, action_key, session["manager_call_count"])
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    return session["cumulative_tokens"], cfg["session_token_budget"]


def check_guard(
    action_key: str,
    override: bool = False,
    root: Path = Path("."),
) -> Tuple[bool, Optional[str]]:
    """
    Check loop detection and budget constraints.
    Returns (allowed, optional_message).
    If allowed is False, command should be blocked.
    """
    session = load_session(root)
    cfg = load_config(root)

    recovery = (
        action_key in {"cmd:handoff", "mcp:check", "mcp:handoff", "mcp:revert-plan", "check", "handoff", "revert-plan"}
        or action_key.startswith(("cmd:budget --reset", "mcp:scope_add:", "scope:add:"))
    )
    if recovery or override:
        return True, None

    try:
        from tg.manager import lockout_message
        blocked = lockout_message(root)
        if blocked:
            return False, blocked
    except (OSError, ValueError, json.JSONDecodeError):
        pass

    used = session.get("cumulative_tokens", 0)
    budget = cfg.get("session_token_budget", 150000)
    ratio = used / float(budget) if budget > 0 else 0.0

    # 1. Hard stop check
    hard_stop = cfg.get("hard_stop_at", 1.0)
    if ratio >= hard_stop:
        # Save context and roll over instead of permanently locking the CLI.
        handoff = generate_handoff("Automatic TokGuard budget rollover", root=root)
        import time
        state = root / ".tokguard"
        archive = state / "sessions"
        archive.mkdir(parents=True, exist_ok=True)
        stamp = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{time.time_ns()}"
        (state / "session.json").replace(archive / f"session-{stamp}.json")
        reset_session(root=root)
        return True, f"BUDGET ROLLOVER: handoff saved to {handoff.as_posix()}; session archived.\n{get_status_line(root)}"

    # 2. Loop detection check
    history: List[str] = session.get("history", [])
    # Check if this exact action repeated 3+ times in recent history
    recent = history[-6:]
    if recent.count(action_key) >= 3 and not override:
        msg = f"LOOP DETECTED: change approach (action repeated {recent.count(action_key)} times)\n"
        return True, msg

    # 3. Budget warning check
    warn_at = cfg.get("warn_at", 0.7)
    if ratio >= warn_at:
        msg = f"BUDGET WARNING: nearing session token limit ({format_token_k(used)}/{format_token_k(budget)})"
        return True, msg

    return True, None


def get_status_line(root: Path = Path(".")) -> str:
    """Return compact session, drift, and step status."""
    session = load_session(root)
    cfg = load_config(root)
    used = session.get("cumulative_tokens", 0)
    budget = cfg.get("session_token_budget", 150000)
    detail = "drift -- | step 0/0"
    if (root / ".tokguard" / "task.json").exists():
        try:
            from tg.manager import check_drift
            order = json.loads((root / ".tokguard" / "task.json").read_text(encoding="utf-8"))
            result = check_drift(root, history=False)
            step_state_path = root / ".tokguard" / "step.json"
            done = json.loads(step_state_path.read_text(encoding="utf-8")).get("done", []) if step_state_path.exists() else []
            level = {"ON TRACK": "OK", "MINOR DRIFT": "MINOR", "MAJOR DRIFT": "MAJOR", "OFF TRACK": "OFF"}.get(result["level"], "?")
            detail = f"drift {result['score']} {level} | step {len(done)}/{len(order['steps'])}"
        except Exception:
            pass
    status = f"[tg: {format_token_k(used)}/{format_token_k(budget)} tokens | {detail}]"
    try:
        from tg.manager import consume_checkpoint_notice
        notice = consume_checkpoint_notice(root)
        if notice:
            return notice + "\n" + status
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return status


def generate_handoff(task_summary: str = "In-progress task", root: Path = Path(".")) -> Path:
    """Generate .tokguard/handoff.md under 30 lines for fresh session continuation."""
    session = load_session(root)
    cfg = load_config(root)
    used = session.get("cumulative_tokens", 0)
    budget = cfg.get("session_token_budget", 150000)
    files = session.get("files_touched", [])
    history = session.get("history", [])[-5:]

    handoff_path = root / ".tokguard" / "handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = [
        "# tokguard Session Handoff",
        f"- **Task**: {task_summary}",
        f"- **Tokens Consumed**: {format_token_k(used)} / {format_token_k(budget)} ({int((used/budget)*100)}%)",
        "- **Files Touched**:",
    ]
    if files:
        for f in files[:8]:
            lines.append(f"  - `{f}`")
    else:
        lines.append("  - None recorded")

    lines.append("- **Recent Actions**:")
    for h in history:
        lines.append(f"  - {h}")

    lines.extend([
        "- **Next Steps**:",
        "  1. Review raw logs in `.tokguard/raw/` if debugging previous test/command failure.",
        "  2. Consult `tg map` or `tg find` for unresolved symbols.",
        "  3. Execute required changes and verify using `tg run -- <test_command>`.",
        "  4. Reset budget for new session via `tg budget --reset`.",
    ])

    try:
        from tg.manager import handoff_context
        context = handoff_context(root)
        if context:
            lines.extend(context.strip().splitlines())
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    handoff_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return handoff_path

