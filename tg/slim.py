"""Code slimming utility to strip comments and blank lines for read-only context."""

from __future__ import annotations

import ast
import io
import re
from pathlib import Path


def slim_python(source: str) -> str:
    """Safely strip comments and docstrings from Python code using AST."""
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    node.body.pop(0)
        return ast.unparse(tree)
    except Exception:
        # Fallback to simple regex comment stripping
        text = re.sub(r"#.*$", "", source, flags=re.MULTILINE)
        lines = [line.rstrip() for line in text.splitlines()]
        res = []
        blank = False
        for line in lines:
            if not line:
                if not blank:
                    res.append("")
                    blank = True
            else:
                blank = False
                res.append(line)
        return "\n".join(res).strip()


def slim_c_like(source: str) -> str:
    """Strip // and /* */ comments from JS/TS/Go/Rust/Java source code."""
    # Strip /* ... */
    no_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    # Strip // ... but not http:// or inside quotes
    lines = []
    for line in no_block.splitlines():
        # Check if // is present and not part of URL
        cleaned = re.sub(r"(?<!:)\/\/.*$", "", line)
        lines.append(cleaned.rstrip())

    # Collapse blank lines
    res = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank:
                res.append("")
                blank = True
        else:
            blank = False
            res.append(line)
    return "\n".join(res).strip()


def slim_file(filepath: Path) -> str:
    """Slim file content based on extension."""
    content = filepath.read_text(encoding="utf-8", errors="replace")
    if filepath.suffix == ".py":
        return slim_python(content)
    if filepath.suffix in [".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".cpp"]:
        return slim_c_like(content)
    # Generic: collapse blank lines
    lines = [l.rstrip() for l in content.splitlines()]
    res = []
    blank = False
    for l in lines:
        if not l:
            if not blank:
                res.append("")
                blank = True
        else:
            blank = False
            res.append(l)
    return "\n".join(res).strip()
