# Agent Context & Token Guard Rules
- Map first: start repository exploration from `tg map`; do not crawl files broadly.
- Search before reading: use `tg find <symbol>` or `rg` first, then read only needed line ranges with `tg read <file> <start>-<end>` (never whole files over 200 lines).
- Unchanged cache: never re-read an unchanged file; trust `tg read` unchanged notices.
- Compress output: run all shell commands through `tg run -- <cmd>` to strip noise and cap length. If truncated, grep `.tokguard/raw/<log>`.
- Batch calls: combine independent shell commands into a single execution step.
- Replies: terse. No restating code just written, no recaps of diffs, no pleasantries. Show unified diffs, never full files. Ask no unnecessary confirmation questions.
- Budget Warning: when `tg` outputs "BUDGET WARNING", wrap up, summarize state in <=10 lines, and ask user before continuing.
- Budget Exceeded: when `tg` outputs "BUDGET EXCEEDED", stop all tool use immediately, run `tg handoff`, and output the handoff summary.

