# tokguard (tg)

A lightweight token-saving toolkit for Codex, Claude Code, Antigravity, and other MCP-compatible coding agents.

---

## One-command setup for Codex, Claude Code, and Antigravity

In PowerShell, run either:

```powershell
npx -y tokguard setup
```

Or install the command once, then configure the assistants:

```powershell
npm install -g tokguard
tokguard setup
```

`setup` registers TokGuard's MCP server in each assistant's user-level settings and adds a small managed instruction block so the assistants know when to use it. Existing settings are preserved. Restart the assistants after setup. The setup works across projects on that machine; use `tg init` below when you also want project-local TokGuard guidance and settings.

### Update TokGuard in PowerShell

For a global installation, update TokGuard and refresh assistant settings with:

```powershell
npm install -g tokguard@latest
tokguard setup
```

For a one-time `npx` setup, use the latest release directly:

```powershell
npx -y tokguard@latest setup
```

## Project-local setup

`tg init` adds repository-specific instructions, `.tgignore`, and `.tokguard/config.json` without replacing existing files.

Optional Codex command with an external budget hard-stop:

```powershell
python -m scripts.codex_guarded "Refactor user authentication service"
```

---

## How Each Saving Works

### 1. Input Token Reduction (What enters the context)
- **`tg map`**: Generates a compact AST/regex repo outline (~300 tokens vs 2,500+ for broad directory crawls).
- **`tg find <symbol|regex>`**: Fast grep returning up to 20 hits with exactly 1 line of context.
- **`tg read <file> <start>-<end>`**: Reads only requested line ranges with line numbers.
- **Unchanged File Detection**: Automatically hashes read files in `.tokguard/session.json`. Repeated reads output `[unchanged since last read: lines X-Y]` instead of re-injecting hundreds of lines.
- **`tg slim <file>`**: Safely removes comments, docstrings, and blank lines for read-only references.
- **Default `.tgignore`**: Excludes build artifacts, locks, bundles, minified assets, and binary files.

### 2. Output Token Reduction (What commands and agent emit)
- **`tg run -- <cmd>`**: Executes shell commands and strips ANSI escapes, progress spinners, repeated output lines, and blank runs.
- **Domain Profiles**: Pytest/Jest/Cargo/Go (failures + final summary only), npm/pip (installation summary only), git (compact status/log/diff), linters (grouped by file).
- **Head & Tail Hard Caps**: Default 120 lines / 6,000 chars, always preserving error/exception/panic tracebacks with 2 context lines.
- **Raw Log grep**: Full uncompressed output is saved to `.tokguard/raw/<timestamp>.log` so agents can grep specific lines rather than rerunning commands.
- **Terse Rules**: `AGENTS.md` instructs models to emit concise diffs rather than entire updated files.

### 3. Budget Guard & Circuit Breaker
- **Session Tracking**: Tracks cumulative tokens in `.tokguard/session.json`, appending `[tg: 84k/150k tokens used]` to every command.
- **Warning Threshold (`warn_at: 0.7`)**: Alerts agent to wrap up in <=10 lines when budget reaches 70%.
- **Hard Stop (`hard_stop_at: 1.0`)**: Refuses command execution once budget is exhausted (bypassable only via `--override`).
- **Loop Detection**: Blocks commands or identical file ranges requested 3+ times consecutively.
- **`tg handoff`**: Automatically generates `.tokguard/handoff.md` (<=30 lines) containing touched files and remaining steps so a fresh session can resume cheaply.

---

## Measured Benchmark Results

Measured across 5 real coding tasks (bug fix, add function, cross-file rename, fix failing test, module explanation):
- **Overall Token Reduction**: **62.5%** (5,227 -> 1,962 tokens)
- **Task Success Rate**: **100%** (5/5 tasks passed)

Run the benchmark anytime:
```bash
python bench/runner.py
```

---

## Known Limits

- **Internal Model Reasoning**: Tokguard cannot intercept or compress hidden chain-of-thought or reasoning tokens generated natively inside models.
- **Agent Compliance**: In non-MCP environments, token savings depend on the agent respecting instructions in `AGENTS.md` / `CLAUDE.md`.
- **Session Boundaries**: Sessions are local to `.tokguard/session.json`; run `tg budget --reset` when starting a completely unrelated project task.

