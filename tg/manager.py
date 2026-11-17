"""Task locking and observable drift checks for coding-agent work."""
from __future__ import annotations

import base64
import difflib
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _state(root: Path) -> Path:
    p = root / ".tokguard"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _git(root: Path, *args: str) -> str:
    try:
        resolved = root.resolve()
        top = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
        if not top or Path(top).resolve() != resolved:
            return ""
        return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _tracked_snapshot(root: Path) -> dict[str, str]:
    files = _git(root, "ls-files").splitlines()
    out = {}
    for name in files:
        p = root / name
        if p.is_file():
            out[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _fallback_snapshot(root: Path) -> dict[str, str]:
    excluded = {".git", ".tokguard", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next"}
    result = {}
    for directory, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [name for name in dirs if name not in excluded]
        base = Path(directory)
        for name in files:
            path = base / name
            try:
                rel = path.relative_to(root).as_posix()
                result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
    return result


def _status(root: Path) -> list[tuple[str, str]]:
    rows = []
    if not _git(root, "rev-parse", "--show-toplevel"):
        return rows
    try:
        result = subprocess.check_output(["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, stderr=subprocess.DEVNULL, text=True)
    except (OSError, subprocess.CalledProcessError):
        return rows
    for line in result.splitlines():
        if len(line) < 4:
            continue
        code, name = line[:2], line[3:]
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        rows.append((code, name.replace("\\", "/")))
    return rows


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lock_prompt(prompt: str, root: Path = Path("."), new: bool = False, announce: bool = True) -> Path:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    state = _state(root)
    path = state / "task.lock.json"
    if path.exists():
        if not new:
            raise ValueError("task lock already exists; pass --new to archive it")
        archive = state / "archive"
        archive.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path.chmod(0o666)
        path.replace(archive / f"task.lock.{stamp}.json")
        sidecar = state / "task.lock.sha256"
        if sidecar.exists():
            sidecar.replace(archive / f"task.lock.{stamp}.sha256")
    status = _status(root)
    dirty = [name for _, name in status]
    head = _git(root, "rev-parse", "HEAD")
    snapshot = _tracked_snapshot(root) if head else _fallback_snapshot(root)
    dirty_content = {}
    for name in dirty:
        source = root / name
        if source.is_file():
            dirty_content[name] = base64.b64encode(source.read_bytes()).decode("ascii")
    data: dict[str, Any] = {"prompt": prompt, "sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "baseline_head": head, "baseline_dirty": dirty,
                            "baseline_untracked": [name for code, name in status if "?" in code],
                            "baseline_snapshot": snapshot, "baseline_dirty_content": dirty_content,
                            "immutable": True}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    sidecar = state / "task.lock.sha256"
    sidecar.write_text(_sha(path.read_bytes()) + "\n", encoding="ascii")
    path.chmod(0o444)
    if announce:
        print("Task locked. Manager protocol: restate the prompt; define checkable criteria, scope and non-goals; order steps; identify risks; choose limits and a verification command; submit the work order with `tg plan --submit <file>`.")
    return path


def read_lock(root: Path = Path(".")) -> dict[str, Any]:
    path = root / ".tokguard" / "task.lock.json"
    if not path.is_file():
        raise ValueError("no task lock; start with tg plan --prompt")
    sidecar = root / ".tokguard" / "task.lock.sha256"
    if sidecar.exists() and sidecar.read_text(encoding="ascii").strip() != _sha(path.read_bytes()):
        raise ValueError("task lock is immutable; its integrity hash does not match")
    data = json.loads(path.read_text(encoding="utf-8"))
    if hashlib.sha256(data["prompt"].encode()).hexdigest() != data["sha256"]:
        raise ValueError("task lock integrity check failed")
    return data


def _validate(order: dict[str, Any], prompt: str, config: dict[str, Any]) -> dict[str, Any]:
    required = ("objective", "acceptance_criteria", "in_scope", "out_of_scope", "steps", "risks", "verify_command")
    missing = [x for x in required if x not in order]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    ambiguous = len(prompt.split()) < 8 or bool(re.search(r"\b(fix it|make it better|do that|change this|improve this|something)\b", prompt, re.I))
    if ambiguous and not isinstance(order.get("assumptions"), list):
        raise ValueError("ambiguous prompt requires an assumptions list; ask the user at most one clarifying question")
    objective = str(order["objective"]).strip()
    if not objective or len(re.findall(r"[.!?](?:\s|$)", objective)) > 1 or "\n" in objective:
        raise ValueError("objective must be one sentence that restates the locked user prompt")
    norm = lambda x: re.sub(r"[^a-z0-9]+", " ", x.lower()).strip()
    stop = {"about", "after", "also", "and", "any", "are", "as", "be", "before", "by", "do", "does", "for", "from", "how", "in", "into", "is", "it", "its", "must", "of", "on", "or", "plus", "that", "the", "this", "to", "use", "with"}
    prompt_words = {w for w in norm(prompt).split() if len(w) >= 4 and w not in stop}
    obj_words = {w for w in norm(objective).split() if len(w) >= 4 and w not in stop}
    if not ambiguous and (len(obj_words) < min(10, len(prompt_words)) or len(prompt_words & obj_words) < min(6, max(3, round(len(prompt_words) * 0.08)))):
        raise ValueError("objective is too vague or does not restate the locked prompt")
    criteria, steps, risks = order["acceptance_criteria"], order["steps"], order["risks"]
    if not isinstance(criteria, list) or not 2 <= len(criteria) <= 6 or any(not isinstance(x, str) or len(x.strip()) < 8 for x in criteria):
        raise ValueError("acceptance_criteria must contain 2-6 checkable statements")
    checkable_prefixes = ("command passes:", "file exists:", "file contains:", "line count <=:")
    vague = [x for x in criteria if not x.lower().startswith(checkable_prefixes)]
    if vague:
        raise ValueError("acceptance criteria must be checkable and use command passes:, file exists:, file contains:, or line count <=:")
    if not isinstance(order["in_scope"], list) or not order["in_scope"] or any(not isinstance(x, str) or not x.strip() for x in order["in_scope"]):
        raise ValueError("in_scope must list at least one file glob or directory")
    if not isinstance(order["out_of_scope"], list) or not order["out_of_scope"] or any(not isinstance(x, str) or not x.strip() for x in order["out_of_scope"]):
        raise ValueError("out_of_scope must explicitly list non-goals")
    if not isinstance(steps, list) or not 3 <= len(steps) <= 8:
        raise ValueError("steps must contain 3-8 ordered steps")
    for step in steps:
        if not isinstance(step, dict) or not step.get("id") or not step.get("expected") or not step.get("text"):
            raise ValueError("each step needs id, text, and expected file or command")
    if len({str(x["id"]) for x in steps}) != len(steps):
        raise ValueError("step ids must be unique")
    if not isinstance(risks, list) or len(risks) > 3 or any(not isinstance(x, str) or not x.strip() for x in risks):
        raise ValueError("risks must contain at most 3 items")
    order.setdefault("max_files_changed", int(config.get("max_files_changed", 8)))
    order.setdefault("max_diff_lines", int(config.get("max_diff_lines", 300)))
    if int(order["max_files_changed"]) < 1 or int(order["max_diff_lines"]) < 1:
        raise ValueError("max_files_changed and max_diff_lines must be positive integers")
    if not isinstance(order["verify_command"], str) or not order["verify_command"].strip():
        raise ValueError("verify_command must be a command")
    return order


def submit_order(source: str, root: Path = Path("."), config: dict[str, Any] | None = None, announce: bool = True) -> Path:
    lock = read_lock(root)
    order = json.loads(source)
    order = _validate(order, lock["prompt"], config or {})
    state = _state(root)
    (state / "task.json").write_text(json.dumps(order, indent=2) + "\n", encoding="utf-8")
    lines = _render_order(order)
    if len(lines) > 40:
        raise ValueError("work order exceeds the 40-line limit")
    (state / "task.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if announce:
        print(f"Work order accepted: {len(order['steps'])} steps; {len(lines)} lines")
    return state / "task.md"


def _render_order(order: dict[str, Any]) -> list[str]:
    lines = [f"# Work order: {order['objective']}", "", "## Acceptance", *[f"- [ ] {x}" for x in order["acceptance_criteria"]],
             "", "## Scope", ", ".join(order["in_scope"]), "", "## Non-goals", ", ".join(order["out_of_scope"]), "", "## Steps"]
    lines.extend(f"{i}. [{s['id']}] {s['text']} — expect: {s['expected']}" for i, s in enumerate(order["steps"], 1))
    lines += ["", "## Risks", "; ".join(order["risks"]), "", f"Verify: `{order['verify_command']}`"]
    if order.get("assumptions"):
        lines += ["", "## Assumptions", "; ".join(order["assumptions"])]
    return lines


def _load_order(root: Path) -> dict[str, Any]:
    p = root / ".tokguard" / "task.json"
    if not p.is_file():
        raise ValueError("no work order; submit one with tg plan --submit")
    return json.loads(p.read_text(encoding="utf-8"))


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) or path.startswith(p.rstrip("/") + "/") for p in patterns)


def _baseline_bytes(root: Path, path: str, lock: dict[str, Any]) -> bytes | None:
    encoded = lock.get("baseline_dirty_content", {}).get(path)
    if encoded:
        try:
            return base64.b64decode(encoded)
        except (ValueError, TypeError):
            return None
    head = lock.get("baseline_head")
    if head:
        try:
            return subprocess.check_output(["git", "show", f"{head}:{path}"], cwd=root, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return None
    return None


def _diff_summary(root: Path, paths: list[str], lock: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    total = 0
    formatting: list[str] = []
    deleted: list[str] = []
    markers = ("#", "//", "/*", "*", "<!--", "--", ";")
    for name in paths:
        target = root / name
        before = _baseline_bytes(root, name, lock)
        after = target.read_bytes() if target.is_file() else b""
        if not target.exists():
            deleted.append(name)
        if before is None:
            before_lines: list[str] = []
            approximate = True
        else:
            before_lines = before.decode("utf-8", errors="replace").splitlines()
            approximate = False
        after_lines = after.decode("utf-8", errors="replace").splitlines()
        if approximate:
            total += max(len(before_lines), len(after_lines), 1)
            continue
        changes = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))
        body = [line for line in changes if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        total += len(body)
        changed_content = [line[1:].strip() for line in body if line[1:].strip()]
        whitespace_only = ["".join(line.split()) for line in before_lines] == ["".join(line.split()) for line in after_lines]
        if whitespace_only and body:
            formatting.append(name)
        elif changed_content and all(line.startswith(markers) for line in changed_content):
            formatting.append(name)
        elif body and all(not line[1:].strip() for line in body):
            formatting.append(name)
    return total, formatting, deleted


def _step_file_paths(order: dict[str, Any]) -> set[str]:
    paths: set[str] = set()
    for step in order["steps"]:
        text = str(step.get("expected", ""))
        paths.update(re.findall(r"[\w./*-]+\.(?:py|md|json|toml|ya?ml|js|ts|tsx|css|sh|ps1)", text))
    return paths


def check_drift(root: Path = Path("."), history: bool = True) -> dict[str, Any]:
    order, lock = _load_order(root), read_lock(root)
    baseline = lock.get("baseline_snapshot", {})
    now = _tracked_snapshot(root) if lock.get("baseline_head") else _fallback_snapshot(root)
    changed = {p for p in set(baseline) | set(now) if baseline.get(p) != now.get(p)}
    baseline_dirty = {p.replace("\\", "/") for p in lock.get("baseline_dirty", [])}
    base_untracked = set(lock.get("baseline_untracked", [])) | (baseline_dirty & set(_git(root, "ls-files").splitlines()))
    live_status = _status(root) if lock.get("baseline_head") else []
    current_untracked = {name for code, name in live_status if "?" in code}
    changed.update(current_untracked - base_untracked - baseline_dirty)
    changed.update(name for name in base_untracked if not (root / name).exists())
    # Older locks do not have snapshots. Keep their pre-existing dirty paths out of the score.
    if not baseline:
        changed = set(_git(root, "diff", "--name-only", lock.get("baseline_head", "HEAD")).splitlines()) if lock.get("baseline_head") else set()
        changed -= baseline_dirty
        changed.update(current_untracked - base_untracked - baseline_dirty)
    changed = sorted(changed)
    diff_lines, formatting_only, deleted = _diff_summary(root, changed, lock)
    reasons: list[str] = []
    signals: dict[str, Any] = {}
    score = 0
    outside = [p for p in changed if not _matches(p, order["in_scope"])]
    if outside:
        points = min(50, 30 + 5 * len(outside)); score += points
        signals["outside_scope"] = {"points": points, "files": outside}
        reasons.append("out of scope: " + ", ".join(outside[:3]))
    cfgpath = root / ".tokguard" / "config.json"
    cfg = json.loads(cfgpath.read_text(encoding="utf-8")) if cfgpath.exists() else {}
    protected_globs = cfg.get("protected_globs", ["*lock*", ".github/**", ".gitlab-ci*", "package.json", "pyproject.toml", "*.config.*"])
    protected = [p for p in changed if _matches(p, protected_globs)]
    if protected:
        score += 20; signals["protected_paths"] = {"points": 20, "files": protected}
        reasons.append("protected config/manifest: " + ", ".join(protected[:3]))
    if deleted:
        score += 15; signals["deleted_files"] = {"points": 15, "files": deleted}
        reasons.append("deleted or renamed: " + ", ".join(deleted[:3]))
    all_task_text = " ".join([order["objective"], *order["acceptance_criteria"], *(s["text"] for s in order["steps"]) ]).lower()
    tests_changed = [p for p in changed if re.search(r"(^|/)(tests?/|test_[^/]+|[^/]+_test\.|[^/]+\.test\.|[^/]+\.spec\.)", p, re.I)]
    if tests_changed and not cfg.get("allow_test_edits", False) and not re.search(r"\btests?\b", all_task_text):
        score += 12; signals["test_edits"] = {"points": 12, "files": tests_changed}
        reasons.append("test files changed although tests were not requested: " + ", ".join(tests_changed[:3]))
    if formatting_only:
        score += min(12, 4 + len(formatting_only)); signals["formatting_only"] = {"points": min(12, 4 + len(formatting_only)), "files": formatting_only}
        reasons.append("formatting/comment-only hunks: " + ", ".join(formatting_only[:3]))
    if len(changed) > order["max_files_changed"]:
        score += 15; signals["file_limit"] = {"points": 15, "count": len(changed), "limit": order["max_files_changed"]}
        reasons.append(f"{len(changed)} files changed (limit {order['max_files_changed']})")
    if diff_lines > order["max_diff_lines"]:
        score += 15; signals["diff_limit"] = {"points": 15, "lines": diff_lines, "limit": order["max_diff_lines"]}
        reasons.append(f"{diff_lines} diff lines (limit {order['max_diff_lines']})")
    state = _state(root)
    session_path = state / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8")) if session_path.exists() else {}
    step_path = state / "step.json"
    step = json.loads(step_path.read_text(encoding="utf-8")) if step_path.exists() else {"done": []}
    done = step.get("done", [])
    expected_done = [s["id"] for s in order["steps"][:len(done)]]
    if done != expected_done:
        score += 25; signals["step_order"] = {"points": 25, "done": done, "expected": expected_done}
        reasons.append("steps completed out of order or outside the work order")
    first_pending = next((s for s in order["steps"] if s["id"] not in done), None)
    history_rows = session.get("history", [])
    stall_calls = int(cfg.get("stall_calls", 12))
    step_index = int(step.get("history_index", 0))
    stalled_calls = max(0, len(history_rows) - step_index)
    if first_pending and stalled_calls >= stall_calls:
        score += 15; signals["stall"] = {"points": 15, "calls": stalled_calls, "limit": stall_calls}
        reasons.append(f"no step progress in {stalled_calls} TokGuard calls")
    repeated = [key for key in set(history_rows[-max(stall_calls, 6):]) if history_rows[-max(stall_calls, 6):].count(key) >= 3]
    if repeated:
        score += 12; signals["repeated_action"] = {"points": 12, "actions": repeated[:3]}
        reasons.append("same command or read repeated 3+ times: " + ", ".join(repeated[:3]))
    scope_path = state / "scope.json"
    scope_log = json.loads(scope_path.read_text(encoding="utf-8")) if scope_path.exists() else []
    if scope_log:
        scope_points = min(9, 2 * len(scope_log)); score += scope_points
        signals["scope_additions"] = {"points": scope_points, "changes": scope_log}
        reasons.append(f"scope expanded {len(scope_log)} time(s); review reasons")
    step_changes_path = state / "step-changes.json"
    step_changes = json.loads(step_changes_path.read_text(encoding="utf-8")) if step_changes_path.exists() else []
    if step_changes:
        points = min(9, 2 * len(step_changes)); score += points
        signals["step_additions"] = {"points": points, "changes": step_changes}
        reasons.append(f"plan steps expanded {len(step_changes)} time(s); review reasons")
    recent_unrelated = []
    expected_files = _step_file_paths(order)
    known_paths = set(_git(root, "ls-files").splitlines()) | set(changed) | baseline_dirty
    recent = history_rows[-stall_calls:]
    for action in recent:
        touched = [p for p in known_paths if p and p in action]
        for path in touched:
            if not _matches(path, order["in_scope"]) or (expected_files and path not in expected_files and not _matches(path, order["in_scope"])):
                recent_unrelated.append({"action": action, "path": path})
    if recent_unrelated:
        score += min(15, 5 * len(recent_unrelated)); signals["unrelated_activity"] = {"points": min(15, 5 * len(recent_unrelated)), "items": recent_unrelated[:5]}
        reasons.append("recent reads/commands touched unrelated paths: " + ", ".join(x["path"] for x in recent_unrelated[:3]))
    result = {"score": min(100, score), "changed": changed, "outside_scope": outside, "diff_lines": diff_lines,
              "reasons": reasons or ["no measurable drift"], "signals": signals, "step": first_pending,
              "completed_steps": done, "stalled_calls": stalled_calls, "formatting_only": formatting_only,
              "deleted": deleted, "thresholds": cfg.get("drift_thresholds", {})}
    thresholds = cfg.get("drift_thresholds", {"minor": 21, "major": 46, "off": 71})
    s = result["score"]
    result["level"] = "OFF TRACK" if s >= thresholds.get("off", 71) else "MAJOR DRIFT" if s >= thresholds.get("major", 46) else "MINOR DRIFT" if s >= thresholds.get("minor", 21) else "ON TRACK"
    if history:
        histp = state / "drift.json"
        hist = json.loads(histp.read_text(encoding="utf-8")) if histp.exists() else []
        hist.append({"at": datetime.now(timezone.utc).isoformat(), "score": s, "level": result["level"]})
        histp.write_text(json.dumps(hist[-200:]) + "\n", encoding="utf-8")
    return result


def print_drift(result: dict[str, Any], json_output: bool = False, quiet: bool = False) -> None:
    if json_output:
        print(json.dumps(result, indent=2)); return
    step = result.get("step")
    corrective = f"Return to step {step['id']}: {step['text']}" if step else "Run tg verify to finish."
    if result["level"] == "MINOR DRIFT":
        objective = read_lock().get("prompt", "").replace("\n", " ").strip()
        print("Objective: " + (objective[:220] + ("…" if len(objective) > 220 else "")))
        corrective = "Re-read the objective above. " + corrective
    if result["level"] == "MAJOR DRIFT": corrective = "Stop new work. Revert or justify out-of-scope changes with tg scope add. " + corrective
    if result["level"] == "OFF TRACK": corrective = "STOP. Run tg revert-plan, then write a handoff and ask the user."
    if quiet and result["score"] < 21: return
    print(f"DRIFT {result['score']} {result['level']}: " + "; ".join(result["reasons"][:3]))
    if not quiet: print("Do: " + corrective)


def _checkpoint_instruction(result: dict[str, Any], root: Path) -> str:
    step = result.get("step")
    next_step = f"step {step['id']}: {step['text']}" if step else "run tg verify"
    if result["level"] == "MINOR DRIFT":
        objective = read_lock(root).get("prompt", "").replace("\n", " ").strip()
        objective = objective[:160] + ("…" if len(objective) > 160 else "")
        return f"Objective: {objective}\nRe-read the objective above. Return to {next_step}."
    if result["level"] == "MAJOR DRIFT":
        return f"Stop new work. Revert or justify out-of-scope changes using `tg scope add <path> --reason '<why>'`, then continue at {next_step}."
    if result["level"] == "OFF TRACK":
        return "STOP. Run `tg revert-plan` to see revert commands, then write a handoff and ask the user."
    return ""


def checkpoint(root: Path, action_key: str, call_count: int) -> dict[str, Any] | None:
    state = _state(root)
    if not (state / "task.json").exists() or not (state / "task.lock.json").exists():
        return None
    cfg_path = state / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    cadence = max(1, int(cfg.get("check_every_n_calls", 8)))
    session_path = state / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8")) if session_path.exists() else {}
    result = check_drift(root, history=False)
    signature = hashlib.sha256(("\0".join(result["changed"]) + f"\0{result['diff_lines']}").encode()).hexdigest()
    is_run = action_key.startswith("mcp:run:") or action_key.startswith("cmd:")
    run_after_edits = is_run and bool(result["changed"]) and signature != session.get("last_run_drift_signature")
    if call_count % cadence and not run_after_edits:
        return None
    result = check_drift(root, history=True)
    notice = _checkpoint_instruction(result, root)
    session["last_checkpoint_call"] = call_count
    if run_after_edits:
        session["last_run_drift_signature"] = signature
    if notice:
        session["checkpoint_notice"] = notice
    session_path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    result["instruction"] = notice
    return result


def consume_checkpoint_notice(root: Path = Path(".")) -> str:
    path = root / ".tokguard" / "session.json"
    if not path.exists():
        return ""
    session = json.loads(path.read_text(encoding="utf-8"))
    notice = str(session.pop("checkpoint_notice", ""))
    if notice:
        path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")
    return notice


def lockout_message(root: Path = Path(".")) -> str:
    try:
        result = check_drift(root, history=False)
    except (ValueError, OSError, json.JSONDecodeError):
        return ""
    return "STOP. Run `tg revert-plan` to see the revert commands for out-of-scope changes, then write a handoff and ask the user." if result["level"] == "OFF TRACK" else ""


def step_done(step_id: str, root: Path = Path("."), note: str = "") -> None:
    order = _load_order(root)
    ids = [s["id"] for s in order["steps"]]
    if step_id not in ids: raise ValueError(f"unknown step id: {step_id}")
    path = _state(root) / "step.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"done": [], "notes": {}}
    expected = next(x for x in ids if x not in data["done"]) if any(x not in data["done"] for x in ids) else None
    if step_id != expected: raise ValueError(f"steps must complete in order; current step is {expected}")
    data["done"].append(step_id)
    if note: data.setdefault("notes", {})[step_id] = note
    session_path = root / ".tokguard" / "session.json"
    session = json.loads(session_path.read_text(encoding="utf-8")) if session_path.exists() else {}
    data["history_index"] = len(session.get("history", []))
    data["last_progress_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Step {step_id} done ({len(data['done'])}/{len(ids)})")


def scope_add(path: str, reason: str, root: Path = Path(".")) -> None:
    if not reason.strip(): raise ValueError("scope additions require --reason")
    state = _state(root); order = _load_order(root); order["in_scope"].append(path)
    rendered = _render_order(order)
    if len(rendered) > 40: raise ValueError("scope change would make the work order exceed 40 lines")
    (state / "task.json").write_text(json.dumps(order, indent=2) + "\n", encoding="utf-8")
    (state / "task.md").write_text("\n".join(rendered) + "\n", encoding="utf-8")
    p = state / "scope.json"; log = json.loads(p.read_text()) if p.exists() else []
    log.append({"path": path, "reason": reason, "at": datetime.now(timezone.utc).isoformat()})
    p.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8"); print(f"Scope added: {path}")


def add_step(text: str, reason: str, root: Path = Path(".")) -> None:
    if not reason.strip(): raise ValueError("adding a step requires --reason")
    order = _load_order(root); order["steps"].append({"id": f"s{len(order['steps']) + 1}", "text": text, "expected": "as specified"})
    if len(order["steps"]) > 8: raise ValueError("work orders are limited to 8 steps")
    state = _state(root); rendered = _render_order(order)
    if len(rendered) > 40: raise ValueError("step change would make the work order exceed 40 lines")
    (state / "task.json").write_text(json.dumps(order, indent=2) + "\n", encoding="utf-8")
    (state / "task.md").write_text("\n".join(rendered) + "\n", encoding="utf-8")
    p = state / "step-changes.json"; log = json.loads(p.read_text()) if p.exists() else []
    log.append({"step": text, "reason": reason, "at": datetime.now(timezone.utc).isoformat()})
    p.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8"); print(f"Step added: {text}")


def show_step(root: Path = Path(".")) -> None:
    order = _load_order(root); state = root / ".tokguard" / "step.json"
    done = json.loads(state.read_text()).get("done", []) if state.exists() else []
    current = next((s for s in order["steps"] if s["id"] not in done), None)
    if current:
        print(f"Step {current['id']}: {current['text']}\nExpected: {current['expected']}\nProgress: {len(done)}/{len(order['steps'])}")
    else: print(f"All {len(order['steps'])} steps complete")


def revert_plan(root: Path = Path("."), execute: bool = False) -> int:
    result = check_drift(root, history=False)
    if not result["outside_scope"]:
        print("No out-of-scope changes to revert."); return 0
    lock = read_lock(root)
    baseline = lock.get("baseline_head") or "HEAD"
    for path in result["outside_scope"]:
        command = f'git checkout {baseline} -- "{path}"'
        print(command)
        if execute: subprocess.run(["git", "checkout", baseline, "--", path], cwd=root, check=False)
    return 0


def verify(root: Path = Path(".")) -> int:
    order = _load_order(root); ok = True
    try:
        from tg.run import execute_and_compress
        from tg.budget import record_action
        code, output = execute_and_compress(order["verify_command"], cwd=root, max_lines=80, max_chars=4000)
        record_action(f"cmd:verify:{order['verify_command']}", output, root=root)
        print(f"{'PASS' if code == 0 else 'FAIL'} verify command: {order['verify_command']}")
        ok &= code == 0
    except (OSError, ValueError) as exc:
        print(f"FAIL verify command: {exc}"); ok = False
    for item in order["acceptance_criteria"]:
        prefix, _, detail = item.partition(":")
        passed = False
        try:
            if prefix == "command passes":
                from tg.run import execute_and_compress
                from tg.budget import record_action
                command = detail.strip()
                code, output = execute_and_compress(command, cwd=root, max_lines=80, max_chars=4000)
                record_action(f"cmd:criterion:{command}", output, root=root)
                passed = code == 0
            elif prefix == "file exists":
                passed = (root / detail.strip().split()[0]).is_file()
            elif prefix == "file contains":
                path_text, separator, needle = detail.strip().partition(":")
                passed = bool(separator and needle.strip() in (root / path_text.strip()).read_text(encoding="utf-8"))
            elif prefix == "line count <=":
                path_text, separator, limit_text = detail.strip().partition(":")
                passed = bool(separator and len((root / path_text.strip()).read_text(encoding="utf-8").splitlines()) <= int(limit_text.strip()))
        except (OSError, ValueError, IndexError):
            passed = False
        print(f"{'PASS' if passed else 'FAIL'} criterion: {item}")
        ok &= passed
    drift = check_drift(root, history=False); print(f"{'PASS' if drift['score'] < 21 else 'FAIL'} drift: {drift['score']} {drift['level']}")
    if drift["outside_scope"]:
        print("FAIL out-of-scope leftovers: " + ", ".join(drift["outside_scope"][:8]))
        ok = False
    state = _state(root); steps = json.loads((state / "step.json").read_text()) if (state / "step.json").exists() else {"done": []}
    if len(steps["done"]) != len(order["steps"]): print("FAIL steps: incomplete"); ok = False
    return 0 if ok else 1


def handoff_context(root: Path = Path(".")) -> str:
    state = root / ".tokguard"; lock = read_lock(root); order = _load_order(root)
    step = json.loads((state / "step.json").read_text()) if (state / "step.json").exists() else {"done": []}
    drift = json.loads((state / "drift.json").read_text()) if (state / "drift.json").exists() else []
    scopes = json.loads((state / "scope.json").read_text()) if (state / "scope.json").exists() else []
    return (f"\n## Task manager\nLocked prompt: {lock['prompt']}\nWork order: {order['objective']}\nSteps: {', '.join(step['done'])}/{len(order['steps'])} done\n"
            f"Drift scores: {', '.join(str(x['score']) for x in drift[-8:]) or 'none'}\nScope changes: {json.dumps(scopes[-5:])}\n")
