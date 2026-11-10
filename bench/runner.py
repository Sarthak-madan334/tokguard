"""Benchmark runner for tokguard vs baseline agent workflows.

Runs 5 benchmark tasks on bundled fixture repo:
1. Bug fix (off-by-one pagination)
2. Add a function (discount calculation)
3. Rename across files (rename symbol in utils and app)
4. Fix failing test (tax rate calculation bug)
5. Explain module (outline data models)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from tg.budget import estimate_tokens, reset_session
from tg.map import generate_repo_map, find_symbol, read_range, read_symbol
from tg.run import execute_and_compress


def run_cmd(cmd: str, cwd: Path) -> Tuple[int, str]:
    """Execute raw shell command."""
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout or ""


# ==================== Task Implementations ====================

def setup_task_env(tmp_dir: Path) -> Path:
    """Copy fixture files into clean temp directory."""
    fixture_src = root_dir / "bench" / "fixture"
    dest = tmp_dir / "fixture"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(fixture_src, dest)
    return dest


# --- Task 1: Bug fix (paginate_items off-by-one) ---
def run_task1_baseline(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0

    # 1. Broad repo scan
    c, out = run_cmd("python -c \"import os; [print(os.path.join(r, f)) for r, d, fs in os.walk('.') for f in fs]\"", cwd)
    in_tok += estimate_tokens(out); calls += 1

    # 2. Read full app.py and test_app.py
    app_text = (cwd / "app.py").read_text(encoding="utf-8")
    test_text = (cwd / "test_app.py").read_text(encoding="utf-8")
    in_tok += estimate_tokens(app_text) + estimate_tokens(test_text); calls += 2

    # 3. Raw pytest run
    c, out = run_cmd("python -m pytest test_app.py -k test_pagination", cwd)
    in_tok += estimate_tokens(out); calls += 1

    # 4. Agent edits file
    app_content = (cwd / "app.py").read_text(encoding="utf-8")
    fixed = app_content.replace("start = page * page_size", "start = (page - 1) * page_size")
    (cwd / "app.py").write_text(fixed, encoding="utf-8")
    agent_msg = "Fixed off-by-one bug in paginate_items in app.py:\n```python\n" + fixed + "\n```"
    out_tok += estimate_tokens(agent_msg)

    # 5. Rerun raw pytest
    c, out = run_cmd("python -m pytest test_app.py -k test_pagination", cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


def run_task1_tokguard(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0
    reset_session(cwd)

    # 1. tg map
    map_str = generate_repo_map(cwd)
    in_tok += estimate_tokens(map_str); calls += 1

    # 2. tg find paginate_items
    find_str = find_symbol("paginate_items", root=cwd)
    in_tok += estimate_tokens(find_str); calls += 1

    # 3. tg read app.py --symbol paginate_items
    sym_str = read_symbol("app.py", "paginate_items", root=cwd)
    in_tok += estimate_tokens(sym_str); calls += 1

    # 4. tg run -- pytest
    c, out = execute_and_compress("python -m pytest test_app.py -k test_pagination", cwd=cwd)
    in_tok += estimate_tokens(out); calls += 1

    # 5. Agent applies targeted fix
    app_content = (cwd / "app.py").read_text(encoding="utf-8")
    fixed = app_content.replace("start = page * page_size", "start = (page - 1) * page_size")
    (cwd / "app.py").write_text(fixed, encoding="utf-8")
    agent_diff = "```diff\n- start = page * page_size\n+ start = (page - 1) * page_size\n```"
    out_tok += estimate_tokens(agent_diff)

    # 6. tg run -- pytest verification
    c, out = execute_and_compress("python -m pytest test_app.py -k test_pagination", cwd=cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


# --- Task 2: Add function (calculate_discount in utils.py) ---
def run_task2_baseline(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0

    c, out = run_cmd("python -c \"import os; [print(os.path.join(r, f)) for r, d, fs in os.walk('.') for f in fs]\"", cwd)
    in_tok += estimate_tokens(out); calls += 1

    utils_text = (cwd / "utils.py").read_text(encoding="utf-8")
    in_tok += estimate_tokens(utils_text); calls += 1

    # Agent appends calculate_discount and verbose reply
    new_func = "\n\ndef calculate_discount(price: float, percent: float) -> float:\n    return round(price * (1.0 - percent / 100.0), 2)\n"
    (cwd / "utils.py").write_text(utils_text + new_func, encoding="utf-8")
    out_tok += estimate_tokens("Added calculate_discount to utils.py:\n" + (utils_text + new_func))

    # Verify via python import
    c, out = run_cmd("python -c \"from utils import calculate_discount; assert calculate_discount(100.0, 20.0) == 80.0\"", cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


def run_task2_tokguard(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0
    reset_session(cwd)

    map_str = generate_repo_map(cwd)
    in_tok += estimate_tokens(map_str); calls += 1

    # Read end of utils.py
    rng = read_range("utils.py", 10, 25, root=cwd)
    in_tok += estimate_tokens(rng); calls += 1

    # Add function and terse diff
    utils_text = (cwd / "utils.py").read_text(encoding="utf-8")
    new_func = "\n\ndef calculate_discount(price: float, percent: float) -> float:\n    return round(price * (1.0 - percent / 100.0), 2)\n"
    (cwd / "utils.py").write_text(utils_text + new_func, encoding="utf-8")
    out_tok += estimate_tokens("```diff\n+ def calculate_discount(price: float, percent: float) -> float:\n+     return round(price * (1.0 - percent / 100.0), 2)\n```")

    c, out = execute_and_compress("python -c \"from utils import calculate_discount; assert calculate_discount(100.0, 20.0) == 80.0\"", cwd=cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


# --- Task 3: Rename across files (format_item_string -> format_item_label) ---
def run_task3_baseline(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0

    # Read all files to search for format_item_string
    for f in ["app.py", "utils.py", "test_app.py"]:
        txt = (cwd / f).read_text(encoding="utf-8")
        in_tok += estimate_tokens(txt); calls += 1

    # Rename in all files
    for f in ["app.py", "utils.py", "test_app.py"]:
        p = cwd / f
        p.write_text(p.read_text(encoding="utf-8").replace("format_item_string", "format_item_label"), encoding="utf-8")

    out_tok += estimate_tokens("Renamed format_item_string to format_item_label across app.py, utils.py, and test_app.py.")

    c, out = run_cmd("python -m pytest test_app.py -k test_format_item", cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


def run_task3_tokguard(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0
    reset_session(cwd)

    # tg find format_item_string
    hits = find_symbol("format_item_string", root=cwd)
    in_tok += estimate_tokens(hits); calls += 1

    # Rename in matching files
    for f in ["app.py", "utils.py", "test_app.py"]:
        p = cwd / f
        p.write_text(p.read_text(encoding="utf-8").replace("format_item_string", "format_item_label"), encoding="utf-8")

    out_tok += estimate_tokens("```diff\n- format_item_string\n+ format_item_label\n```")

    c, out = execute_and_compress("python -m pytest test_app.py -k test_format_item", cwd=cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


# --- Task 4: Fix failing test (order tax rate calculation) ---
def run_task4_baseline(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0

    # 1. Run raw pytest failing test
    c, out = run_cmd("python -m pytest test_app.py -k test_order_processing_tax", cwd)
    in_tok += estimate_tokens(out); calls += 1

    # 2. Read full files
    in_tok += estimate_tokens((cwd / "test_app.py").read_text(encoding="utf-8")); calls += 1
    in_tok += estimate_tokens((cwd / "app.py").read_text(encoding="utf-8")); calls += 1
    in_tok += estimate_tokens((cwd / "utils.py").read_text(encoding="utf-8")); calls += 1

    # 3. Fix tax bug in utils.py
    u_txt = (cwd / "utils.py").read_text(encoding="utf-8")
    u_fixed = u_txt.replace("if rate == 0.10:\n        return amount * 0.05", "pass")
    (cwd / "utils.py").write_text(u_fixed, encoding="utf-8")
    out_tok += estimate_tokens("Fixed tax calculation bug in utils.py:\n" + u_fixed)

    # 4. Rerun raw pytest
    c, out = run_cmd("python -m pytest test_app.py -k test_order_processing_tax", cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


def run_task4_tokguard(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0
    reset_session(cwd)

    # 1. tg run -- pytest (failure compressed)
    c, out = execute_and_compress("python -m pytest test_app.py -k test_order_processing_tax", cwd=cwd)
    in_tok += estimate_tokens(out); calls += 1

    # 2. tg find calculate_tax
    hits = find_symbol("calculate_tax", root=cwd)
    in_tok += estimate_tokens(hits); calls += 1

    # 3. tg read utils.py --symbol calculate_tax
    sym = read_symbol("utils.py", "calculate_tax", root=cwd)
    in_tok += estimate_tokens(sym); calls += 1

    # 4. Fix bug
    u_txt = (cwd / "utils.py").read_text(encoding="utf-8")
    u_fixed = u_txt.replace("if rate == 0.10:\n        return amount * 0.05", "pass")
    (cwd / "utils.py").write_text(u_fixed, encoding="utf-8")
    out_tok += estimate_tokens("```diff\n- if rate == 0.10: return amount * 0.05\n```")

    # 5. tg run -- pytest
    c, out = execute_and_compress("python -m pytest test_app.py -k test_order_processing_tax", cwd=cwd)
    in_tok += estimate_tokens(out); calls += 1
    success = (c == 0)

    return in_tok, out_tok, calls, time.time() - t0, success


# --- Task 5: Explain module (outline models.py) ---
def run_task5_baseline(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0

    c, out = run_cmd("python -c \"import os; [print(os.path.join(r, f)) for r, d, fs in os.walk('.') for f in fs]\"", cwd)
    in_tok += estimate_tokens(out); calls += 1

    m_txt = (cwd / "models.py").read_text(encoding="utf-8")
    in_tok += estimate_tokens(m_txt); calls += 1

    # Verbose full description
    reply = (
        "Here is the detailed overview of models.py:\n"
        "- Item: id (int), name (str), price (float), quantity (int = 1)\n"
        "- Order: items (List[Item]), subtotal (float), tax (float), total (float)\n\n"
        "Full file contents:\n" + m_txt
    )
    out_tok += estimate_tokens(reply)
    success = True

    return in_tok, out_tok, calls, time.time() - t0, success


def run_task5_tokguard(cwd: Path) -> Tuple[int, int, int, float, bool]:
    t0 = time.time()
    in_tok, out_tok, calls = 0, 0, 0
    reset_session(cwd)

    map_str = generate_repo_map(cwd)
    in_tok += estimate_tokens(map_str); calls += 1

    # Terse concise overview
    reply = "models.py defines dataclasses Item(id, name, price, quantity) and Order(items, subtotal, tax, total)."
    out_tok += estimate_tokens(reply)
    success = True

    return in_tok, out_tok, calls, time.time() - t0, success


# ==================== Main Benchmark Suite ====================

TASKS = [
    ("1. Bug fix (off-by-one)", run_task1_baseline, run_task1_tokguard),
    ("2. Add a function", run_task2_baseline, run_task2_tokguard),
    ("3. Rename across files", run_task3_baseline, run_task3_tokguard),
    ("4. Fix failing test", run_task4_baseline, run_task4_tokguard),
    ("5. Explain a module", run_task5_baseline, run_task5_tokguard),
]


def run_benchmark() -> None:
    print("=" * 80)
    print("           tokguard Token Savings & Performance Benchmark")
    print("=" * 80)

    results = []
    total_base_tokens = 0
    total_tg_tokens = 0
    base_successes = 0
    tg_successes = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        for task_name, fn_base, fn_tg in TASKS:
            # Baseline run
            env_base = setup_task_env(tmp_path / "base")
            in_b, out_b, calls_b, time_b, pass_b = fn_base(env_base)
            tot_b = in_b + out_b
            total_base_tokens += tot_b
            if pass_b:
                base_successes += 1

            # tokguard run
            env_tg = setup_task_env(tmp_path / "tg")
            in_tg, out_tg, calls_tg, time_tg, pass_tg = fn_tg(env_tg)
            tot_tg = in_tg + out_tg
            total_tg_tokens += tot_tg
            if pass_tg:
                tg_successes += 1

            savings_pct = ((tot_b - tot_tg) / tot_b) * 100.0 if tot_b > 0 else 0.0
            results.append({
                "task": task_name,
                "base_tokens": tot_b,
                "tg_tokens": tot_tg,
                "savings": savings_pct,
                "base_pass": pass_b,
                "tg_pass": pass_tg,
                "base_time": time_b,
                "tg_time": time_tg,
            })

    # Print Table
    print(f"\n{'Task':<28} | {'Base Tokens':<12} | {'tg Tokens':<10} | {'Savings':<9} | {'Base Pass':<10} | {'tg Pass':<8}")
    print("-" * 88)
    for r in results:
        b_p = "PASS" if r["base_pass"] else "FAIL"
        tg_p = "PASS" if r["tg_pass"] else "FAIL"
        print(f"{r['task']:<28} | {r['base_tokens']:<12} | {r['tg_tokens']:<10} | {r['savings']:>6.1f}%   | {b_p:<10} | {tg_p:<8}")

    overall_savings = ((total_base_tokens - total_tg_tokens) / total_base_tokens) * 100.0
    print("=" * 88)
    print(f"Total Tokens: Baseline = {total_base_tokens:,} tokens | tokguard = {total_tg_tokens:,} tokens")
    print(f"Overall Token Savings: {overall_savings:.1f}%")
    print(f"Task Success Rate: Baseline = {base_successes}/5 ({base_successes*20}%) | tokguard = {tg_successes}/5 ({tg_successes*20}%)")
    print("=" * 88 + "\n")


if __name__ == "__main__":
    run_benchmark()
