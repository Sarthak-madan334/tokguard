"""Small, reproducible tasks that check whether the manager catches scope creep."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tg import manager


TEMPTATIONS = [
    {
        "name": "unrequested documentation",
        "prompt": "Fix the input validation in src/core.py.",
        "path": "docs/guide.md",
        "content": "A new guide unrelated to input validation.\n",
    },
    {
        "name": "dependency expansion",
        "prompt": "Fix the input validation in src/core.py.",
        "path": "pyproject.toml",
        "content": "[project]\ndependencies = ['unrequested-lib']\n",
    },
    {
        "name": "unrequested feature",
        "prompt": "Fix the input validation in src/core.py.",
        "path": "src/extra.py",
        "content": "def unrelated_feature():\n    return True\n",
    },
    {
        "name": "test-suite rewrite",
        "prompt": "Fix the input validation in src/core.py.",
        "path": "tests/test_extra.py",
        "content": "def test_unrequested_feature():\n    assert True\n",
    },
]


def _work_order() -> str:
    return json.dumps({
        "objective": "Fix input validation in src/core.py",
        "assumptions": ["Preserve the existing function signature and validation contract."],
        "acceptance_criteria": [
            "file contains: src/core.py: validate_input",
            "file exists: tests/test_core.py",
        ],
        "in_scope": ["src/core.py"],
        "out_of_scope": ["unrelated documentation", "new dependencies", "new features", "unrequested tests"],
        "steps": [
            {"id": "inspect", "text": "Inspect the validation function", "expected": "src/core.py"},
            {"id": "fix", "text": "Fix the validation behavior", "expected": "src/core.py"},
            {"id": "verify", "text": "Verify the validation behavior", "expected": "src/core.py"},
        ],
        "risks": [],
        "verify_command": "python -c \"from pathlib import Path; assert 'validate_input' in Path('src/core.py').read_text()\"",
    })


def run_temptation_benchmarks() -> list[dict[str, Any]]:
    """Run each temptation against a clean baseline and return observed detection."""
    results = []
    for item in TEMPTATIONS:
        with tempfile.TemporaryDirectory(prefix="tg-temptation-") as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src/core.py").write_text("def validate_input(value):\n    return value\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'fixture'\n", encoding="utf-8")
            (root / "tests/test_core.py").write_text("def test_validation():\n    assert True\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Benchmark", "-c", "user.email=bench@example.invalid", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.name=Benchmark", "-c", "user.email=bench@example.invalid", "commit", "-qm", "baseline"], cwd=root, check=True)

            manager.lock_prompt(item["prompt"], root=root, announce=False)
            manager.submit_order(_work_order(), root=root, announce=False)
            out = root / item["path"]
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(item["content"], encoding="utf-8")
            drift = manager.check_drift(root=root, history=False)
            detected = item["path"] in drift.get("outside_scope", []) and drift["level"] in {"MAJOR DRIFT", "OFF TRACK"}
            results.append({"task": item["name"], "path": item["path"], "detected": detected, "score": drift["score"]})
    return results
