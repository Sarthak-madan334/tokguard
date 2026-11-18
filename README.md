# tokguard (tg)

A lightweight token-saving toolkit for Codex, Claude Code, Antigravity, and other MCP-compatible coding agents.

The TokGuard product site lives in [`website/`](website/README.md). It is a Next.js and React app styled with Tailwind CSS.

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

### Uninstall TokGuard

Remove a global npm installation with:

```powershell
tg uninstall
```

This removes the global npm package and leaves project files created by `tg init`, `.tokguard` data, and assistant settings from `tg setup` untouched. For a project-local install, run `npm uninstall tokguard` from that project.

### Automatic updates

A global `tg` or `tokguard` command checks npm at startup, installs a newer release when available, then reruns the original command. If npm is offline or the install lacks permission, TokGuard continues with the installed version. The configured MCP launch also uses `tokguard@latest`, so it picks up releases when the assistant starts the server again. To disable the global CLI update check for a PowerShell session:

```powershell
$env:TOKGUARD_AUTO_UPDATE = "0"
```

## Project-local setup

`tg init` adds repository-specific instructions, `.tgignore`, and `.tokguard/config.json` without replacing existing files.

Optional Codex command with task-drift monitoring (token thresholds are not enforced):

```powershell
python -m scripts.codex_guarded "Refactor user authentication service"
```

This runner never terminates a command for token usage; it retains the separate task-drift monitor.

## Task manager and drift checks

Lock the original request, submit a JSON work order, and follow its ordered steps:

```bash
tg plan --prompt "Fix input validation in src/core.py"
tg plan --submit .tokguard/work-order.json
tg check
tg step show
tg verify
```

The manager records a baseline, checks changed paths and work-order limits, reports drift with a correction, and blocks guarded tools when the task is off track. Log a justified expansion with `tg scope add <path> --reason "..."`; use `tg revert-plan` to see suggested recovery commands. `tg verify` runs the declared verification command and acceptance checks. Post-tool drift checks are advisory because Claude's `PostToolUse` event runs after the tool call.

### Claude Code PostToolUse Claude Code settings.json hook snippet

Add this to `~/.claude/settings.json` (Windows: `%USERPROFILE%\.claude\settings.json`) to check after edits, writes, and shell commands. Merge the `PostToolUse` entry with any hooks already configured:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|Bash",
        "hooks": [
          { "type": "command", "command": "tg check --quiet" }
        ]
      }
    ]
  }
}
```

The hook uses the installed `tg` command. Install globally with `npm install -g tokguard`, then restart Claude Code or confirm the settings reload. It does nothing when no task is locked.

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

### 3. Session Usage & Loop Detection
- **Usage Tracking**: Tracks estimated token use and action history in `.tokguard/session.json`; status shows usage without a token threshold.
- **No Token Stops**: Token usage never warns, resets the ledger, or terminates a command.
- **Loop Detection**: Reports repeated actions so the agent can choose a different approach.
- **`tg handoff`**: Manually generates `.tokguard/handoff.md` (<=30 lines) containing touched files and remaining steps for session continuation.

---

## Measured Benchmark Results

Measured with TokGuard's token estimator across 5 benchmark task fixtures (bug fix, add function, cross-file rename, failing test, module explanation):
- **Overall Token Reduction**: **63.2%** (5,402 -> 1,988 estimated tokens in the latest run)
- **Task Success Rate**: **100%** (5/5 tasks passed)
- **Scope-creep checks**: **4/4 detected** (docs, dependency, feature, and test expansion)

Run the benchmark anytime:
```bash
python bench/runner.py
```

---

## Known Limits

- **Internal Model Reasoning**: Tokguard cannot intercept or compress hidden chain-of-thought or reasoning tokens generated natively inside models.
- **Agent Compliance**: In non-MCP environments, token savings depend on the agent respecting instructions in `AGENTS.md` / `CLAUDE.md`.
- **Session Boundaries**: Usage history is local to `.tokguard/session.json`; run `tg budget --reset` when starting a completely unrelated project task.

