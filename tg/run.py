"""Command execution and output compression for tokguard."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PROGRESS_PATTERN = re.compile(
    r"(?:\r|[\b])|"
    r"\[[=\-#\s>]{5,}\]|"
    r"(?:[\d\.]+\s*(?:KB|MB|GB|B)/s)|"
    r"(?:\d{1,3}%\s*\[)|"
    r"^(?:[\s\-\|\\/]|Fetching|Downloading|Extracting|Resolving).{0,40}\.{3,}"
)
ERROR_PATTERN = re.compile(r"(?i)\b(error|fail|failed|failure|exception|traceback|panic)\b")


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return ANSI_ESCAPE.sub("", text)


def normalize_line_endings(text: str) -> str:
    """Handle carriage returns from progress spinners and normalize to newlines."""
    lines: List[str] = []
    for line in re.split(r"\r\n|\n", text):
        parts = line.split("\r")
        lines.append(parts[-1] if parts else "")
    return "\n".join(lines)


def collapse_blank_lines(lines: List[str]) -> List[str]:
    """Reduce runs of multiple blank lines to at most one."""
    res: List[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                res.append("")
                blank = True
        else:
            blank = False
            res.append(line)
    return res


def collapse_repeated_lines(lines: List[str], threshold: int = 3) -> List[str]:
    """Collapse 3 or more identical or near-identical lines."""
    if not lines:
        return []
    res: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        curr = lines[i]
        curr_clean = curr.strip()
        j = i + 1
        while j < n and lines[j].strip() == curr_clean:
            j += 1
        count = j - i
        if count >= threshold:
            res.append(curr)
            res.append(f"  ... [repeated x{count - 1}]")
            i = j
        else:
            res.append(curr)
            i += 1
    return res


def filter_progress_lines(lines: List[str]) -> List[str]:
    """Filter out progress bars, download bars, and spinner updates."""
    clean: List[str] = []
    for line in lines:
        s = line.strip()
        # Drop progress spinner updates
        if PROGRESS_PATTERN.search(s) and not ERROR_PATTERN.search(s):
            # check if it's purely a progress/download line
            if any(ch in s for ch in ["%", "MB/s", "KB/s", "===>", "----"]) or s.startswith(("[#", "[-")):
                continue
        clean.append(line)
    return clean


# ---------------- Profile Handlers ----------------

def profile_test_runner(lines: List[str], exit_code: int) -> List[str]:
    """Profile for pytest / jest / vitest / go test / cargo test."""
    if exit_code == 0:
        # Success: keep final summary and passed counts
        summary_lines = [
            l for l in lines
            if any(k in l.lower() for k in ["passed", "ok", "success", "ran ", "test result:", "seconds", "summary"])
            or l.startswith("=")
        ]
        return summary_lines[-10:] if summary_lines else lines[-5:]

    # Failures: keep failures, errors, tracebacks and final summary
    res: List[str] = []
    capturing = False
    for i, line in enumerate(lines):
        if any(marker in line for marker in ["FAIL", "ERROR", "FAILURE:", "FAILURES", "panic:", "Traceback"]):
            capturing = True
        if capturing:
            res.append(line)
            if line.startswith("=" * 5) and len(res) > 20 and i > len(lines) - 10:
                # Reached final summary bar
                pass

    # Ensure tail summary is included
    tail = lines[-10:]
    for l in tail:
        if l not in res:
            res.append(l)
    return res if len(res) > 3 else lines


def profile_package_install(lines: List[str]) -> List[str]:
    """Profile for npm / pip / cargo install."""
    res: List[str] = []
    for line in lines:
        s = line.strip()
        if ERROR_PATTERN.search(s):
            res.append(line)
        elif any(marker in s.lower() for marker in [
            "successfully installed", "added", "packages", "audited", "found 0 vulnerabilities",
            "warning", "up to date", "downloaded", "installed"
        ]):
            res.append(line)
    return res if res else lines[-10:]


def profile_linter_compiler(lines: List[str]) -> List[str]:
    """Profile for tsc / eslint / ruff: group by file and cap."""
    file_errors: dict[str, List[str]] = {}
    other: List[str] = []
    file_re = re.compile(r"^([a-zA-Z0-9_\-/\\]+\.[a-zA-Z0-9]+)[:\(\d]")

    for line in lines:
        m = file_re.match(line.strip())
        if m:
            fname = m.group(1)
            file_errors.setdefault(fname, []).append(line)
        else:
            other.append(line)

    res: List[str] = []
    for fname, errs in file_errors.items():
        res.append(f"==> {fname} ({len(errs)} issues):")
        for e in errs[:5]:
            res.append(f"  {e.strip()}")
        if len(errs) > 5:
            res.append(f"  ... [{len(errs) - 5} more issues in {fname}]")

    # Add summary/other lines
    res.extend([l for l in other if ERROR_PATTERN.search(l) or "found" in l.lower()][-5:])
    return res if res else lines


def profile_docker_build(lines: List[str]) -> List[str]:
    """Profile for docker build: errors + last 30 lines."""
    errors = [l for l in lines[:-30] if ERROR_PATTERN.search(l)]
    tail = lines[-30:] if len(lines) > 30 else lines
    return errors + (["... [steps omitted] ..."] if errors else []) + tail


def profile_git(lines: List[str], cmd: str) -> List[str]:
    """Profile for git diff / log / status."""
    if "status" in cmd:
        return [l for l in lines if l.strip() and not l.strip().startswith("(")]
    if "log" in cmd:
        # Cap to 20 commit lines
        return lines[:20] + ([f"... [{len(lines)-20} older commits omitted]"] if len(lines) > 20 else [])
    if "diff" in cmd:
        # Cap hunks: max 15 lines per file diff
        res: List[str] = []
        cur_count = 0
        in_file = False
        for line in lines:
            if line.startswith("diff --git"):
                in_file = True
                cur_count = 0
                res.append(line)
            elif in_file:
                if cur_count < 15:
                    res.append(line)
                    cur_count += 1
                elif cur_count == 15:
                    res.append("    ... [file diff truncated]")
                    cur_count += 1
            else:
                res.append(line)
        return res
    return lines


def match_command_profile(cmd: str, lines: List[str], exit_code: int) -> List[str]:
    """Detect if command matches a known profile and apply specific compression."""
    c = cmd.lower()
    if any(k in c for k in ["pytest", "jest", "vitest", "go test", "cargo test"]):
        return profile_test_runner(lines, exit_code)
    if any(k in c for k in ["npm install", "npm i", "pip install", "cargo add", "cargo install"]):
        return profile_package_install(lines)
    if any(k in c for k in ["tsc", "eslint", "ruff check", "flake8"]):
        return profile_linter_compiler(lines)
    if "docker build" in c:
        return profile_docker_build(lines)
    if c.strip().startswith("git "):
        return profile_git(lines, c)
    return lines


# ---------------- Core Compression ----------------

def compress_output(
    raw_text: str,
    command: str,
    exit_code: int,
    max_lines: int = 120,
    max_chars: int = 6000,
    raw_log_path: str | None = None,
) -> str:
    """Compress command output applying sanitization, profiles, and budget caps."""
    clean_text = strip_ansi(raw_text)
    clean_text = normalize_line_endings(clean_text)
    lines = clean_text.splitlines()

    # 1. Clean progress & blank runs
    lines = filter_progress_lines(lines)
    lines = collapse_blank_lines(lines)
    lines = collapse_repeated_lines(lines)

    # 2. Apply profile if matched
    lines = match_command_profile(command, lines, exit_code)
    lines = collapse_blank_lines(lines)

    # 3. Check caps
    total_chars = sum(len(l) + 1 for l in lines)
    if len(lines) <= max_lines and total_chars <= max_chars:
        return "\n".join(lines)

    # 4. Cap while preserving error lines with 2 lines of context
    error_indices = set()
    for idx, line in enumerate(lines):
        if ERROR_PATTERN.search(line):
            for c_idx in range(max(0, idx - 2), min(len(lines), idx + 3)):
                error_indices.add(c_idx)

    # We need to cap lines down to max_lines
    # Keep head (first 30%), tail (last 30%), and error regions in between
    budget = max_lines
    head_budget = max(10, budget // 4)
    tail_budget = max(10, budget // 4)

    head_lines = list(range(0, min(head_budget, len(lines))))
    tail_lines = list(range(max(0, len(lines) - tail_budget), len(lines)))

    included_indices = set(head_lines) | set(tail_lines) | error_indices
    sorted_indices = sorted(included_indices)

    # Format with omission marker
    omitted_marker_printed = False
    result_lines: List[str] = []
    prev_idx = -1

    omission_msg = (
        f"[... {len(lines) - len(sorted_indices)} lines omitted; "
        f"rerun with --full or inspect raw log: {raw_log_path or '.tokguard/raw/'} ...]"
    )

    for idx in sorted_indices:
        if prev_idx != -1 and idx > prev_idx + 1:
            if not omitted_marker_printed:
                result_lines.append(omission_msg)
                omitted_marker_printed = True
            else:
                result_lines.append("[... lines omitted ...]")
        result_lines.append(lines[idx])
        prev_idx = idx

    # If still over max_chars, truncate from middle
    final_text = "\n".join(result_lines)
    if len(final_text) > max_chars:
        half = (max_chars - len(omission_msg) - 20) // 2
        final_text = (
            final_text[:half]
            + f"\n{omission_msg}\n"
            + final_text[-half:]
        )

    return final_text


def save_raw_log(raw_output: str, command: str) -> Path:
    """Save raw command output to .tokguard/raw/<timestamp>.log."""
    raw_dir = Path(".tokguard/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    log_path = raw_dir / f"{timestamp}.log"
    header = f"# Command: {command}\n# Date: {datetime.now().isoformat()}\n" + ("=" * 60) + "\n"
    log_path.write_text(header + raw_output, encoding="utf-8", errors="replace")
    return log_path


def execute_and_compress(
    command: str,
    max_lines: int = 120,
    max_chars: int = 6000,
    full: bool = False,
    cwd: Path | str | None = None,
) -> Tuple[int, str]:
    """Execute command, preserve exit code, log raw output and return compressed text."""
    # Execute through shell
    proc = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    raw_output = proc.stdout or ""
    log_path = save_raw_log(raw_output, command)

    if full:
        out = raw_output + f"\n[Raw log saved: {log_path.as_posix()}]"
        return proc.returncode, out

    compressed = compress_output(
        raw_output,
        command,
        proc.returncode,
        max_lines=max_lines,
        max_chars=max_chars,
        raw_log_path=log_path.as_posix(),
    )
    # Append path note so agent can grep instead of rerunning
    compressed += f"\n[Raw log: {log_path.as_posix()}]"
    return proc.returncode, compressed
