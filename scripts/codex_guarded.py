#!/usr/bin/env python3
"""External token-guarded wrapper for Codex CLI (and any agent execution).

Usage:
    python -m scripts.codex_guarded "Implement user authentication"
    python scripts/codex_guarded.py --budget 50000 -- "codex exec 'refactor db'"
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
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
    load_config,
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
    budget_limit: int,
    poll_interval: float = 0.05,
) -> int:
    """Execute command, stream output, count tokens, kill process if budget exceeded."""
    print(f"[tokguard] Launching guarded execution with budget: {format_token_k(budget_limit)} tokens")
    print(f"[tokguard] Command: {command_str}\n" + ("=" * 60))

    start_time = time.time()
    accumulated_chars = 0
    reported_tokens: Optional[int] = None
    stop_triggered = False

    proc = subprocess.Popen(
        command_str,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    captured_lines: List[str] = []

    try:
        assert proc.stdout is not None
        for line in iter(proc.stdout.readline, ""):
            sys.stdout.write(line)
            sys.stdout.flush()
            captured_lines.append(line)
            accumulated_chars += len(line)

            # Check if line reported token count
            reported = parse_usage_line(line)
            if reported:
                reported_tokens = reported

            current_tokens = reported_tokens if reported_tokens else estimate_tokens("".join(captured_lines))

            if current_tokens >= budget_limit:
                stop_triggered = True
                print("\n" + "!" * 60)
                print(f"[tokguard] HARD STOP TRIGGERED: Reached {format_token_k(current_tokens)} / {format_token_k(budget_limit)} tokens!")
                print("[tokguard] Terminating process immediately to prevent runaway cost...")
                print("!" * 60 + "\n")

                # Terminate subprocess
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
                break

        proc.stdout.close()
        proc.wait()
    except KeyboardInterrupt:
        print("\n[tokguard] Interrupted by user.")
        proc.kill()
        return 130

    final_tokens = reported_tokens if reported_tokens else estimate_tokens("".join(captured_lines))
    record_action(f"guarded:{task_desc}", "".join(captured_lines))

    if stop_triggered:
        handoff_path = generate_handoff(f"Interrupted by tokguard: {task_desc}")
        print(f"[tokguard] Auto-generated emergency handoff: {handoff_path.as_posix()}")
        return 99

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"[tokguard] Completed in {elapsed:.1f}s. Tokens consumed: ~{format_token_k(final_tokens)} ({final_tokens:,})")
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="External budget guard for Codex and coding agents.")
    parser.add_argument("task", nargs="*", help="Task description or command")
    parser.add_argument("--budget", type=int, help="Override token budget for this run")
    parser.add_argument("--cmd", help="Explicit command to execute (defaults to: codex exec '<task>')")

    args = parser.parse_args()
    cfg = load_config()
    budget = args.budget or cfg.get("session_token_budget", 150000)

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

    return run_guarded(cmd, task_str, budget)


if __name__ == "__main__":
    sys.exit(main())

