"""Repository mapping, symbol extraction, search, and targeted read for tokguard."""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

DEFAULT_IGNORES = {
    ".git",
    ".tokguard",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "*.pyc",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.log",
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}

MAX_SCAN_FILE_BYTES = 1_000_000
SYMBOL_SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".go", ".rs", ".java"}

REGEX_PATTERNS = {
    # JS/TS
    r"\.(js|jsx|ts|tsx|mjs)$": [
        re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)"),
        re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\("),
        re.compile(r"^\s*(?:export\s+)?class\s+([a-zA-Z0-9_$]+)"),
    ],
    # Go
    r"\.go$": [
        re.compile(r"^\s*func\s+(?:\([^\)]+\)\s+)?([a-zA-Z0-9_]+)\("),
        re.compile(r"^\s*type\s+([a-zA-Z0-9_]+)\s+struct"),
    ],
    # Rust
    r"\.rs$": [
        re.compile(r"^\s*(?:pub(?:\([^\)]+\))?\s+)?fn\s+([a-zA-Z0-9_]+)"),
        re.compile(r"^\s*(?:pub(?:\([^\)]+\))?\s+)?(?:struct|enum|trait)\s+([a-zA-Z0-9_]+)"),
    ],
    # Java
    r"\.java$": [
        re.compile(r"^\s*(?:public|protected|private)?\s*(?:static\s+)?(?:final\s+)?class\s+([a-zA-Z0-9_]+)"),
        re.compile(r"^\s*(?:public|protected|private)?\s*(?:static\s+)?[a-zA-Z0-9_<>\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^\)]*\)\s*(?:throws\s+[^{]+)?\{"),
    ],
}


def load_ignore_patterns(root: Path) -> Set[str]:
    """Load ignore patterns from .gitignore, .tgignore and defaults."""
    patterns = set(DEFAULT_IGNORES)
    for fname in [".gitignore", ".tgignore"]:
        fpath = root / fname
        if fpath.exists():
            for line in fpath.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip().rstrip("/\\")
                if line and not line.startswith("#"):
                    patterns.add(line)
    return patterns


def is_ignored(rel_path: str, patterns: Set[str]) -> bool:
    """Check if a relative path matches any ignore pattern."""
    parts = Path(rel_path).parts
    for part in parts:
        if part in patterns:
            return True
        for pat in patterns:
            if fnmatch.fnmatch(part, pat) or fnmatch.fnmatch(rel_path, pat):
                return True
    return False


def _read_scan_text(fpath: Path) -> Optional[str]:
    """Read a small text file for scanning; skip oversized and binary files."""
    try:
        if fpath.stat().st_size > MAX_SCAN_FILE_BYTES:
            return None
        content = fpath.read_bytes()
    except OSError:
        return None
    if b"\0" in content:
        return None
    return content.decode("utf-8", errors="ignore")


def extract_python_symbols(source: str) -> List[str]:
    """Extract classes and functions from Python source using AST."""
    try:
        tree = ast.parse(source)
    except Exception:
        # Fallback to simple regex if syntax error
        funcs = re.findall(r"^\s*def\s+([a-zA-Z0-9_]+)", source, re.M)
        classes = re.findall(r"^\s*class\s+([a-zA-Z0-9_]+)", source, re.M)
        return [f"class {c}" for c in classes] + [f"{f}()" for f in funcs]

    symbols: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(f"{node.name}()")
        elif isinstance(node, ast.ClassDef):
            methods = [
                n.name
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith("__")
            ]
            if methods:
                symbols.append(f"class {node.name}[{', '.join(methods[:4])}{'...' if len(methods) > 4 else ''}]")
            else:
                symbols.append(f"class {node.name}")
    return symbols


def extract_regex_symbols(source: str, filename: str) -> List[str]:
    """Extract symbols from non-Python files using regex."""
    for pattern, regex_list in REGEX_PATTERNS.items():
        if re.search(pattern, filename, re.IGNORECASE):
            symbols: List[str] = []
            for line in source.splitlines():
                for r in regex_list:
                    m = r.search(line)
                    if m:
                        name = m.group(1)
                        if "class" in r.pattern or "struct" in r.pattern:
                            symbols.append(f"class {name}")
                        else:
                            symbols.append(f"{name}()")
                        break
            return symbols
    return []


def extract_symbols(fpath: Path) -> List[str]:
    """Extract top symbols from a given file."""
    suffix = fpath.suffix.lower()
    if suffix not in SYMBOL_SOURCE_SUFFIXES:
        return []
    content = _read_scan_text(fpath)
    if content is None:
        return []

    if suffix == ".py":
        return extract_python_symbols(content)
    return extract_regex_symbols(content, fpath.name)


def generate_repo_map(root: Path = Path(".")) -> str:
    """Generate compact repo tree with symbol outlines, capped at ~1500 tokens (6000 chars)."""
    patterns = load_ignore_patterns(root)
    cache_path = root / ".tokguard" / "map.json"
    cache: dict = {"files": {}}

    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {"files": {}}

    updated_cache: dict = {"files": {}}
    map_lines: List[str] = []

    # Walk repository
    all_files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != "." and is_ignored(rel_dir, patterns):
            dirnames[:] = []  # Don't recurse
            continue

        # Filter out ignored directories
        dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(rel_dir if rel_dir != "." else "", d), patterns)]

        for fname in sorted(filenames):
            rel_file = os.path.normpath(os.path.join(rel_dir, fname)) if rel_dir != "." else fname
            rel_file = rel_file.replace("\\", "/")
            if not is_ignored(rel_file, patterns):
                all_files.append(Path(dirpath) / fname)

    for fpath in sorted(all_files):
        rel_str = fpath.relative_to(root).as_posix()
        try:
            stat = fpath.stat()
            mtime = stat.st_mtime
        except Exception:
            continue

        cached_entry = cache.get("files", {}).get(rel_str)
        if cached_entry and cached_entry.get("mtime") == mtime:
            symbols = cached_entry.get("symbols", [])
        else:
            symbols = extract_symbols(fpath)

        updated_cache["files"][rel_str] = {"mtime": mtime, "symbols": symbols}

        if symbols:
            map_lines.append(f"{rel_str}: {', '.join(symbols)}")
        else:
            map_lines.append(rel_str)

    # Save incremental cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(updated_cache, indent=2), encoding="utf-8")

    # Check budget (~6000 chars / ~1500 tokens)
    full_text = "\n".join(map_lines)
    if len(full_text) <= 6000:
        return full_text

    # Cap intelligently: keep file paths, drop symbol details if needed
    compacted: List[str] = []
    cur_len = 0
    for line in map_lines:
        if cur_len + len(line) > 5800:
            compacted.append(f"... [{len(map_lines) - len(compacted)} more files omitted; use 'tg find <symbol>']")
            break
        compacted.append(line)
        cur_len += len(line) + 1

    return "\n".join(compacted)


def find_symbol(query: str, root: Path = Path("."), max_results: int = 20) -> str:
    """Search for symbol or regex pattern across files with 1 line of context."""
    max_results = max(1, max_results)
    patterns = load_ignore_patterns(root)
    try:
        regex = re.compile(query, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(query), re.IGNORECASE)

    matches: List[str] = []
    skipped_large = 0
    stopped_early = False

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir != "." and is_ignored(rel_dir, patterns):
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(rel_dir if rel_dir != "." else "", d), patterns)]

        for fname in sorted(filenames):
            rel_file = (os.path.normpath(os.path.join(rel_dir, fname)) if rel_dir != "." else fname).replace("\\", "/")
            if is_ignored(rel_file, patterns):
                continue

            fpath = Path(dirpath) / fname
            try:
                if fpath.stat().st_size > MAX_SCAN_FILE_BYTES:
                    skipped_large += 1
                    continue
            except OSError:
                continue
            content = _read_scan_text(fpath)
            if content is None:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines):
                if regex.search(line):
                    if len(matches) < max_results:
                        line_num = idx + 1
                        # Format hit with 1 line context
                        ctx: List[str] = []
                        if idx > 0:
                            ctx.append(f"  {idx:4d} | {lines[idx-1]}")
                        ctx.append(f"> {line_num:4d} | {line}")
                        if idx + 1 < len(lines):
                            ctx.append(f"  {idx+2:4d} | {lines[idx+1]}")
                        matches.append(f"{rel_file}:{line_num}\n" + "\n".join(ctx))
                        if len(matches) >= max_results:
                            stopped_early = True
                            break
            if stopped_early:
                break
        if stopped_early:
            break

    if not matches:
        result = f"No matches found for '{query}'."
        if skipped_large:
            result += f"\n[Skipped {skipped_large} files larger than {MAX_SCAN_FILE_BYTES // 1_000_000} MB.]"
        return result

    res = "\n\n".join(matches)
    if stopped_early:
        res += f"\n\n[Stopped after {max_results} matches; refine query to search further.]"
    if skipped_large:
        res += f"\n\n[Skipped {skipped_large} files larger than {MAX_SCAN_FILE_BYTES // 1_000_000} MB.]"
    return res


def file_hash(content: str) -> str:
    """Calculate sha256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def track_session_read(filepath: str, content: str, root: Path = Path(".")) -> Tuple[bool, int]:
    """
    Track file reads in .tokguard/session.json.
    Returns (is_unchanged, total_lines).
    """
    session_path = root / ".tokguard" / "session.json"
    session: dict = {"file_hashes": {}, "cumulative_tokens": 0, "history": []}
    if session_path.exists():
        try:
            session = json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    file_hashes = session.setdefault("file_hashes", {})
    curr_hash = file_hash(content)
    total_lines = len(content.splitlines())

    if file_hashes.get(filepath) == curr_hash:
        return True, total_lines

    file_hashes[filepath] = curr_hash
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(session, indent=2), encoding="utf-8")
    return False, total_lines


def read_range(filepath: str, start: int, end: int, root: Path = Path(".")) -> str:
    """Read a specific 1-indexed line range from a file with line numbers."""
    fpath = root / filepath
    if not fpath.exists():
        return f"Error: File not found '{filepath}'"

    content = fpath.read_text(encoding="utf-8", errors="replace")
    rel_path = fpath.relative_to(root).as_posix()
    unchanged, total_lines = track_session_read(rel_path, content, root=root)

    lines = content.splitlines()
    start_idx = max(0, start - 1)
    end_idx = min(len(lines), end)

    if unchanged:
        return f"[unchanged since last read: lines {start}-{end} of {total_lines} in {rel_path}]"

    output_lines: List[str] = [f"--- {rel_path} ({start}-{end}/{total_lines}) ---"]
    for i in range(start_idx, end_idx):
        output_lines.append(f"{i + 1:4d} | {lines[i]}")
    return "\n".join(output_lines)


def read_symbol(filepath: str, symbol_name: str, root: Path = Path(".")) -> str:
    """Read full body of a symbol (class or function) from a file."""
    fpath = root / filepath
    if not fpath.exists():
        return f"Error: File not found '{filepath}'"

    content = fpath.read_text(encoding="utf-8", errors="replace")
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    if fpath.suffix == ".py":
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == symbol_name:
                        start_line = node.lineno
                        end_line = getattr(node, "end_lineno", start_line)
                        break
        except Exception:
            pass

    if start_line is None:
        lines = content.splitlines()
        for idx, l in enumerate(lines):
            if re.search(rf"\b(def|class|fn|func)\s+{re.escape(symbol_name)}\b", l):
                start_line = idx + 1
                end_line = min(len(lines), start_line + 50)
                break

    if start_line is None:
        return f"Symbol '{symbol_name}' not found in '{filepath}'."

    return read_range(filepath, start_line, end_line or start_line, root=root)
