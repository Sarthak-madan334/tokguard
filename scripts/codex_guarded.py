#!/usr/bin/env python3
"""Drift-aware wrapper for Codex CLI (and any agent execution).

Usage:
    python -m scripts.codex_guarded "Implement user authentication"
    python scripts.codex_guarded.py --cmd "codex exec 'refactor db'"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

# Add parent to path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from tg.budget import (
    estimate_tokens,
    format_token_k,
    generate_handoff,
    record_action,
)

USAGE_REGEX = re.compile(r"(?i)(?:tokens|usage|total_tokens)\s*[:=]\s*(\d+)")


def parse_usage_line(line: str) -> Optional[int]:
    """Extract reported tokens from codex / agent logs if present."""
    m = USAGE_REGEX.search(line)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return None


def run_guarded(
    command_str: str,
    task_desc: str,
    poll_interval: float = 0.05,
    drift_interval: float = 5.0,
    cwd: Optional[Path] = None,
) -> int:
    """Run a command to completion while watching for task drift."""
    print("[tokguard] Launching drift-aware execution (no token limit)")
    print(f"[tokguard] Command: {command_str}\n" + ("=" * 60))

    start_time = time.time()
    reported_tokens: Optional[int] = None

    task_root = Path(cwd or Path.cwd()).resolve()
    proc = subprocess.Popen(
        command_str,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        cwd=task_root,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    drift_stop = threading.Event()
    drift_report: dict = {}

    def watch_drift() -> None:
        while not drift_stop.wait(max(0.1, drift_interval)):
            report = _run_drift_check(task_root)
            if report and report.get("level") == "OFF TRACK":
                drift_report.update(report)
                _terminate_process_tree(proc)
                return

    watcher = None
    if (task_root / ".tokguard" / "task.json").exists():
        watcher = threading.Thread(target=watch_drift, name="tokguard-drift", daemon=True)
        watcher.start()

    captured_lines: List[str] = []

    try:
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
            captured_lines.append(line)

            reported = parse_usage_line(line)
            if reported:
                reported_tokens = reported

        proc.stdout.close()
        proc.wait()
        drift_stop.set()
        if watcher:
            watcher.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[tokguard] Interrupted by user.")
        drift_stop.set()
        _terminate_process_tree(proc)
        return 130

    final_tokens = reported_tokens if reported_tokens else estimate_tokens("".join(captured_lines))
    record_action(f"guarded:{task_desc}", "".join(captured_lines), root=task_root)

    if drift_report:
        summary = f"Interrupted by tokguard: {task_desc}"
        if drift_report:
            summary += "\nDrift report: " + json.dumps(drift_report, ensure_ascii=False, separators=(",", ":"))
        handoff_path = generate_handoff(summary, root=task_root)
        print(f"[tokguard] Auto-generated emergency handoff: {handoff_path.as_posix()}")
        return 99

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"[tokguard] Completed in {elapsed:.1f}s. Tokens consumed: ~{format_token_k(final_tokens)} ({final_tokens:,})")
    return proc.returncode


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=5)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass


def _run_drift_check(cwd: Path) -> dict:
    """Run the compact JSON drift check and tolerate its trailing status line."""
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(root_dir), env.get("PYTHONPATH", "")]))
        result = subprocess.run(
            [sys.executable, "-m", "tg.cli", "check", "--json"],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if result.returncode:
            return {}
        start = result.stdout.find("{")
        if start < 0:
            return {}
        report, _ = json.JSONDecoder().raw_decode(result.stdout[start:])
        return report if isinstance(report, dict) else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a command while watching TokGuard task drift.")
    parser.add_argument("task", nargs="*", help="Task description or command")
    parser.add_argument("--cmd", help="Explicit command to execute (defaults to: codex exec '<task>')")

    args = parser.parse_args()

    task_str = " ".join(args.task) if args.task else "Guarded task"

    if args.cmd:
        cmd = args.cmd
    elif args.task:
        # If task looks like a full command, run it; else wrap in codex exec
        first = args.task[0]
        if first in ["codex", "python", "pytest", "bash", "sh", "node"]:
            cmd = " ".join(args.task)
        else:
            cmd = f'codex exec "{task_str}"'
    else:
        cmd = 'codex exec "Perform requested task"'

    return run_guarded(cmd, task_str)


if __name__ == "__main__":
    sys.exit(main())

