# Agent Context & Token Guard Rules
- Map first: start repository exploration from `tg map`; do not crawl files broadly.
- Search before reading: use `tg find <symbol>` or `rg` first, then read only needed line ranges with `tg read <file> <start>-<end>` (never whole files over 200 lines).
- Unchanged cache: never re-read an unchanged file; trust `tg read` unchanged notices.
- Compress output: run all shell commands through `tg run -- <cmd>` to strip noise and cap length. If truncated, grep `.tokguard/raw/<log>`.
- First action: `tg plan --prompt "<original user prompt>"`, then write and submit the work order as a senior tech manager.
- A different user prompt in the same chat starts a fresh task and archives the previous work order; repeating the same prompt keeps the current task.
- Do only what the work order says. Obey every DRIFT message. Update scope only with a reason.
- Finish only after `tg verify` PASS.
- Batch calls: combine independent shell commands into a single execution step.
- Replies: terse. No restating code just written, no recaps of diffs, no pleasantries. Show unified diffs, never full files. Ask no unnecessary confirmation questions.

