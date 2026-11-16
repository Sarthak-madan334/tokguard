# Agent Context & Token Guard Rules
- Map first: start repository exploration from `tg map`; do not crawl files broadly.
- Search before reading: use `tg find <symbol>` or `rg` first, then read only needed line ranges with `tg read <file> <start>-<end>` (never whole files over 200 lines).
- Unchanged cache: never re-read an unchanged file; trust `tg read` unchanged notices.
- Compress output: run all shell commands through `tg run -- <cmd>` to strip noise and cap length. If truncated, grep `.tokguard/raw/<log>`.
- Batch calls: combine independent shell commands into a single execution step.
- Replies: terse. No restating code just written, no recaps of diffs, no pleasantries. Show unified diffs, never full files. Ask no unnecessary confirmation questions.
- Budget Warning: keep TokGuard output compact and continue the active task.
- Budget Rollover: TokGuard saves a handoff, archives the old ledger, and starts a fresh session automatically; continue from the handoff. `tg handoff` and `tg budget --reset` remain available at all times.

