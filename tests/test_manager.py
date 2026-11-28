"""Regression tests for TokGuard task locks and manager orders."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tg import manager
from tg.cli import main as cli_main


PROMPT = "Extend TokGuard with a task manager that locks the user's prompt and validates its work order."


def make_order() -> dict:
    return {
        "objective": "Extend TokGuard with a task manager that locks the user's prompt and validates its work order.",
        "acceptance_criteria": [
            "command passes: python -m pytest -q",
            "file exists: tg/manager.py",
        ],
        "in_scope": ["tg/", "tests/"],
        "out_of_scope": ["no dependency changes", "no unrelated refactors"],
        "steps": [
            {"id": "one", "text": "Validate the prompt lock and work order", "expected": "tg/manager.py"},
            {"id": "two", "text": "Measure scope drift", "expected": "tg/manager.py"},
            {"id": "three", "text": "Verify the task", "expected": "python -m pytest -q"},
        ],
        "risks": ["A vague objective could accept an unrelated plan"],
        "verify_command": "python -c \"print('verified')\"",
    }


def git_repo(root):
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "TokGuard Test"], cwd=root, check=True)
    (root / ".gitignore").write_text(".tokguard/\n", encoding="utf-8")
    (root / "README.md").write_text("baseline\n", encoding="utf-8")
    (root / "tg").mkdir()
    (root / "tg" / "core.py").write_text("VALUE = 1\n# baseline note\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "irrelevant.py").write_text("VALUE = 0\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "README.md", "tg/core.py", "docs/irrelevant.py"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)


def prepared_repo(root, order=None):
    git_repo(root)
    manager.lock_prompt(PROMPT, root)
    manager.submit_order(json.dumps(order or make_order()), root)
    return root


def test_prompt_lock_is_verbatim_immutable_and_archivable(tmp_path):
    git_repo(tmp_path)
    lock = manager.lock_prompt(PROMPT, tmp_path)
    data = json.loads(lock.read_text(encoding="utf-8"))
    assert data["prompt"] == PROMPT
    assert data["sha256"]
    assert data["baseline_head"]
    assert data["baseline_dirty"] == []
    assert data["immutable"] is True
    assert manager.lock_prompt(PROMPT, tmp_path, announce=False) == lock
    assert not (tmp_path / ".tokguard" / "archive").exists()
    lock.chmod(0o666)
    changed = json.loads(lock.read_text(encoding="utf-8"))
    changed["prompt"] = "tampered"
    lock.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        manager.read_lock(tmp_path)
    manager.lock_prompt(PROMPT, tmp_path, new=True)
    assert list((tmp_path / ".tokguard" / "archive").glob("task.lock.*.json"))


def test_new_prompt_archives_and_resets_previous_work_order_state(tmp_path):
    git_repo(tmp_path)
    manager.lock_prompt(PROMPT, tmp_path, announce=False)
    manager.submit_order(json.dumps(make_order()), tmp_path, announce=False)
    state = tmp_path / ".tokguard"
    (state / "step.json").write_text(json.dumps({"done": ["one"]}), encoding="utf-8")
    (state / "scope.json").write_text(json.dumps([{"path": "src/", "reason": "approved"}]), encoding="utf-8")
    (state / "step-changes.json").write_text(json.dumps([{"step": "old step"}]), encoding="utf-8")
    (state / "drift.json").write_text(json.dumps([{"score": 35}]), encoding="utf-8")
    (state / "session.json").write_text(json.dumps({
        "cumulative_tokens": 1234,
        "history": ["old-task-action"],
        "checkpoint_notice": "STOP: previous task is off track",
        "last_run_drift_signature": "old-signature",
        "last_checkpoint_call": 8,
    }), encoding="utf-8")

    new_prompt = "Start a different task in the same conversation and prepare a fresh task scope."
    manager.lock_prompt(new_prompt, tmp_path, announce=False)

    assert not any((state / name).exists() for name in ("task.json", "task.md", "step.json", "scope.json", "step-changes.json", "drift.json"))
    assert manager.read_lock(tmp_path)["prompt"] == new_prompt
    session = json.loads((state / "session.json").read_text(encoding="utf-8"))
    assert session["cumulative_tokens"] == 1234
    assert session["history"] == ["old-task-action"]
    assert "checkpoint_notice" not in session
    assert "last_run_drift_signature" not in session
    assert "last_checkpoint_call" not in session
    archive = state / "archive"
    assert list(archive.glob("task.*.json"))
    assert list(archive.glob("step.*.json"))
    assert list(archive.glob("scope.*.json"))
    assert list(archive.glob("drift.*.json"))
    assert list(archive.glob("step-changes.*.json"))


def test_cli_accepts_new_prompt_when_previous_task_is_off_track(tmp_path, monkeypatch):
    prepared_repo(tmp_path)
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "outside.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_extra.py").write_text("def test_extra(): pass\n", encoding="utf-8")
    (tmp_path / "README.md").unlink()
    assert manager.check_drift(tmp_path, history=False)["level"] == "OFF TRACK"

    monkeypatch.chdir(tmp_path)
    new_prompt = "Handle a separate request in this same chat with a new scope and verification plan."
    assert cli_main(["plan", "--prompt", new_prompt]) == 0
    assert manager.read_lock(tmp_path)["prompt"] == new_prompt
    assert not (tmp_path / ".tokguard" / "task.json").exists()
    new_order = make_order()
    new_order["objective"] = new_prompt
    manager.submit_order(json.dumps(new_order), tmp_path, announce=False)
    assert manager.check_drift(tmp_path, history=False)["level"] == "ON TRACK"


def test_new_work_order_ignores_prior_task_actions_for_stall_and_repeat_signals(tmp_path):
    git_repo(tmp_path)
    manager.lock_prompt(PROMPT, tmp_path, announce=False)
    state = tmp_path / ".tokguard"
    old_actions = ["mcp:step:done"] * 20
    (state / "session.json").write_text(json.dumps({"history": old_actions}), encoding="utf-8")
    manager.submit_order(json.dumps(make_order()), tmp_path, announce=False)

    step = json.loads((state / "step.json").read_text(encoding="utf-8"))
    result = manager.check_drift(tmp_path, history=False)

    assert step["history_index"] == len(old_actions)
    assert "stall" not in result["signals"]
    assert "repeated_action" not in result["signals"]


def test_submit_rejects_vague_or_uncheckable_orders(tmp_path):
    manager.lock_prompt(PROMPT, tmp_path)
    vague = make_order()
    vague["objective"] = "Make it better."
    with pytest.raises(ValueError, match="vague"):
        manager.submit_order(json.dumps(vague), tmp_path)
    vague = make_order()
    vague["acceptance_criteria"] = ["Looks good when finished.", "Seems more useful now."]
    with pytest.raises(ValueError, match="checkable"):
        manager.submit_order(json.dumps(vague), tmp_path)


@pytest.mark.parametrize("field,value,match", [
    ("acceptance_criteria", ["command passes: x"], "2-6"),
    ("in_scope", [], "in_scope"),
    ("out_of_scope", [], "out_of_scope"),
    ("steps", [], "3-8"),
    ("risks", ["a", "b", "c", "d"], "at most 3"),
    ("verify_command", "", "verify_command"),
])
def test_schema_validation_errors_are_specific(tmp_path, field, value, match):
    manager.lock_prompt(PROMPT, tmp_path)
    order = make_order()
    order[field] = value
    with pytest.raises(ValueError, match=match):
        manager.submit_order(json.dumps(order), tmp_path)


def test_dirty_git_baseline_is_recorded(tmp_path):
    git_repo(tmp_path)
    (tmp_path / "README.md").write_text("pre-existing edit\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("already untracked\n", encoding="utf-8")
    lock = manager.lock_prompt(PROMPT, tmp_path)
    data = json.loads(lock.read_text(encoding="utf-8"))
    assert "README.md" in data["baseline_dirty"]
    assert "notes.txt" in data["baseline_dirty"]
    assert "notes.txt" in data["baseline_untracked"]
    assert data["baseline_dirty_content"]["README.md"]


def test_non_git_baseline_hashes_repository_files(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    monkeypatch.setattr(manager, "_git", lambda root, *args: "")
    lock = manager.lock_prompt(PROMPT, tmp_path)
    data = json.loads(lock.read_text(encoding="utf-8"))
    assert "src/main.py" in data["baseline_snapshot"]
    assert ".tokguard/task.lock.json" not in data["baseline_snapshot"]


def test_planning_fallback_snapshot_prunes_generated_directories(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    generated = tmp_path / "node_modules" / "large-package" / "dist"
    generated.mkdir(parents=True)
    (generated / "bundle.js").write_text("generated\n", encoding="utf-8")

    visited = []
    original_walk = manager.os.walk

    def recording_walk(*args, **kwargs):
        for directory, dirs, files in original_walk(*args, **kwargs):
            visited.append(Path(directory).relative_to(tmp_path).as_posix())
            yield directory, dirs, files

    monkeypatch.setattr(manager.os, "walk", recording_walk)
    snapshot = manager._fallback_snapshot(tmp_path)

    assert "src/main.py" in snapshot
    assert not any(name.startswith("node_modules") for name in snapshot)
    assert not any(name.startswith("node_modules") for name in visited)


def test_ambiguous_prompt_requires_explicit_assumptions(tmp_path):
    manager.lock_prompt("Fix it.", tmp_path)
    order = make_order()
    order["objective"] = "Fix it."
    with pytest.raises(ValueError, match="assumptions"):
        manager.submit_order(json.dumps(order), tmp_path)
    order["assumptions"] = ["The request refers to the current repository's main package."]
    assert manager.submit_order(json.dumps(order), tmp_path).exists()


def test_out_of_scope_change_scores_major_signal_and_level(tmp_path):
    prepared_repo(tmp_path)
    (tmp_path / "outside.py").write_text("print('scope creep')\n", encoding="utf-8")
    result = manager.check_drift(tmp_path, history=False)
    assert result["outside_scope"] == ["outside.py"]
    assert result["signals"]["outside_scope"]["points"] >= 30
    assert result["level"] == "MINOR DRIFT"
    assert "outside.py" in result["reasons"][0]


def test_expected_step_file_is_in_scope_when_scope_text_is_not_a_glob(tmp_path):
    order = make_order()
    order["in_scope"] = ["the files explicitly named in the implementation steps"]
    order["steps"][1]["expected"] = "src/authorized.py updated"
    prepared_repo(tmp_path, order)
    target = tmp_path / "src" / "authorized.py"
    target.parent.mkdir()
    target.write_text("print('authorized')\n", encoding="utf-8")

    result = manager.check_drift(tmp_path, history=False)

    assert result["outside_scope"] == []
    assert "outside_scope" not in result["signals"]


def test_protected_paths_and_file_and_diff_limits_score(tmp_path):
    order = make_order()
    order["max_files_changed"] = 1
    order["max_diff_lines"] = 2
    prepared_repo(tmp_path, order)
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "another.py").write_text("\n".join("x = 1" for _ in range(8)), encoding="utf-8")
    result = manager.check_drift(tmp_path, history=False)
    assert result["signals"]["protected_paths"]["files"] == ["package.json"]
    assert "file_limit" in result["signals"]
    assert "diff_limit" in result["signals"]
    assert result["level"] == "OFF TRACK"


def test_test_edits_are_flagged_only_when_unrequested(tmp_path):
    prepared_repo(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_extra.py").write_text("def test_extra(): pass\n", encoding="utf-8")
    result = manager.check_drift(tmp_path, history=False)
    assert result["signals"]["test_edits"]["files"] == ["tests/test_extra.py"]
    order = json.loads((tmp_path / ".tokguard" / "task.json").read_text())
    order["steps"][0]["text"] = "Add tests for the request"
    (tmp_path / ".tokguard" / "task.json").write_text(json.dumps(order), encoding="utf-8")
    result = manager.check_drift(tmp_path, history=False)
    assert "test_edits" not in result["signals"]


def test_comment_only_hunks_and_deleted_files_are_detected(tmp_path):
    prepared_repo(tmp_path)
    (tmp_path / "tg" / "core.py").write_text("VALUE = 1\n# updated note\n", encoding="utf-8")
    result = manager.check_drift(tmp_path, history=False)
    assert result["formatting_only"] == ["tg/core.py"]
    (tmp_path / "tg" / "core.py").unlink()
    result = manager.check_drift(tmp_path, history=False)
    assert "tg/core.py" in result["deleted"]
    assert "deleted_files" in result["signals"]


def test_stall_repeat_step_order_and_scope_add_signals(tmp_path):
    prepared_repo(tmp_path)
    state = tmp_path / ".tokguard"
    (state / "session.json").write_text(json.dumps({"history": ["read:tg/core.py:1-20"] * 12}), encoding="utf-8")
    (state / "step.json").write_text(json.dumps({"done": ["two"], "history_index": 0}), encoding="utf-8")
    result = manager.check_drift(tmp_path, history=False)
    assert {"stall", "repeated_action", "step_order"} <= set(result["signals"])
    with pytest.raises(ValueError, match="reason"):
        manager.scope_add("extra/", "", tmp_path)
    manager.scope_add("extra/", "A required generated output belongs to this task.", tmp_path)
    result = manager.check_drift(tmp_path, history=False)
    assert "scope_additions" in result["signals"]
    assert "extra/" in json.loads((state / "task.json").read_text())["in_scope"]


def test_unrelated_recent_read_is_reported_without_file_drift(tmp_path):
    prepared_repo(tmp_path)
    (tmp_path / ".tokguard" / "session.json").write_text(
        json.dumps({"history": ["read:docs/irrelevant.py:1-20"]}), encoding="utf-8"
    )
    result = manager.check_drift(tmp_path, history=False)
    assert "unrelated_activity" in result["signals"]
    assert result["changed"] == []


def test_steps_complete_in_order_and_step_add_requires_reason(tmp_path):
    prepared_repo(tmp_path)
    with pytest.raises(ValueError, match="in order"):
        manager.step_done("two", tmp_path)
    manager.step_done("one", tmp_path, note="lock verified")
    with pytest.raises(ValueError, match="reason"):
        manager.add_step("Review generated docs", "", tmp_path)
    manager.add_step("Review generated docs", "The docs need a final explicit review.", tmp_path)
    order = json.loads((tmp_path / ".tokguard" / "task.json").read_text())
    assert order["steps"][-1]["id"] == "s4"
    assert "Review generated docs" in (tmp_path / ".tokguard" / "task.md").read_text(encoding="utf-8")


def test_verify_runs_commands_and_checks_file_state(tmp_path, capsys):
    order = make_order()
    order["verify_command"] = "python --version"
    order["acceptance_criteria"] = [
        "command passes: python --version",
        "file exists: tg/core.py",
        "file contains: README.md: baseline",
        "line count <=: README.md: 1",
    ]
    prepared_repo(tmp_path, order)
    for step in order["steps"]:
        manager.step_done(step["id"], tmp_path)
    assert manager.verify(tmp_path) == 0
    output = capsys.readouterr().out
    assert output.count("PASS criterion:") == len(order["acceptance_criteria"])
    assert "PASS drift: 0 ON TRACK" in output


def test_checkpoint_runs_every_configured_call_and_appends_status(tmp_path):
    from tg.budget import get_status_line, record_action

    prepared_repo(tmp_path)
    state = tmp_path / ".tokguard"
    (state / "config.json").write_text(json.dumps({"check_every_n_calls": 2}), encoding="utf-8")
    record_action("read:tg/core.py:1-10", "small", root=tmp_path)
    assert not (state / "drift.json").exists()
    record_action("read:tg/core.py:1-10", "small", root=tmp_path)
    history = json.loads((state / "drift.json").read_text(encoding="utf-8"))
    assert len(history) == 1
    assert "drift 0 OK" in get_status_line(tmp_path)
    assert "step 0/3" in get_status_line(tmp_path)


def test_run_after_file_edit_triggers_immediate_checkpoint(tmp_path):
    from tg.budget import record_action

    prepared_repo(tmp_path)
    changed = tmp_path / "tg" / "core.py"
    changed.write_text("VALUE = 2\n# baseline note\n", encoding="utf-8")
    record_action("cmd:python --version", "Python 3", root=tmp_path)
    history = json.loads((tmp_path / ".tokguard" / "drift.json").read_text(encoding="utf-8"))
    assert len(history) == 1


def test_off_track_blocks_tools_but_allows_recovery_and_override(tmp_path):
    from tg.budget import check_guard

    order = make_order()
    order["max_files_changed"] = 1
    prepared_repo(tmp_path, order)
    for name in ("one.py", "two.py", "three.py"):
        (tmp_path / name).write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}\n", encoding="utf-8")
    blocked, message = check_guard("mcp:map", root=tmp_path)
    assert blocked is False
    assert "STOP." in message
    assert check_guard("mcp:check", root=tmp_path)[0] is True
    assert check_guard("mcp:revert-plan", root=tmp_path)[0] is True
    assert check_guard("mcp:map", override=True, root=tmp_path)[0] is True


def test_handoff_includes_locked_prompt_order_steps_drift_and_scope(tmp_path):
    from tg.budget import generate_handoff

    prepared_repo(tmp_path)
    manager.step_done("one", tmp_path, note="schema passed")
    state = tmp_path / ".tokguard"
    (state / "drift.json").write_text(json.dumps([{"score": 0}, {"score": 4}]), encoding="utf-8")
    manager.scope_add("generated/", "The requested output requires a generated directory.", tmp_path)
    handoff = generate_handoff("Resume manager feature", root=tmp_path)
    text = handoff.read_text(encoding="utf-8")
    assert PROMPT in text
    assert make_order()["objective"] in text
    assert "Steps: one/3 done" in text
    assert "Drift scores: 0, 4" in text
    assert "generated/" in text
