# Claude Code Delegate

## What this is

A toolkit that lets an orchestrating AI (Codex, Cursor, etc.) delegate implementation plans to Claude Code for execution, then review the resulting diff.

## Key files

- `SKILL.md` — The orchestrator contract. This is what Codex/the orchestrator reads to understand the delegation workflow.
- `scripts/run-claude-code.sh` — The wrapper that parses flags and delegates to the pipeline.
- `scripts/pipeline.py` — The delegation pipeline: classify → envelope → invoke → compact → profile.
- `scripts/run-pipeline.py` — Thin CLI entry point that the wrapper calls.
- `scripts/compact-claude-stream.py` — Compacts JSON stream output into a readable report.
- `scripts/aggregate-profile-log.py` — Aggregates CLAUDE_DELEGATE_PROFILE_LOG JSONL into a summary.
- `scripts/jira-safe-text.py` — Strips Markdown for Jira MCP plain-text comments.
- `tests/run_tests.sh` — Test runner (bash, no external deps).
- `CONTEXT.md` — Domain glossary for the project.

## Git workflow

- Never push directly to `main`.
- Create a feature branch for every change: `feat/<short-description>`, `fix/<short-description>`, or `doc/<short-description>`.
- After committing on the branch, push and open a pull request.
- Merge via PR only — even for solo work. This keeps a clean history and gives a checkpoint for review.

## Commands

```bash
# Run tests
bash tests/run_tests.sh

# Test the wrapper directly
bash scripts/run-claude-code.sh --flash "test prompt"
```

## Design notes

- The wrapper defaults to `bypassPermissions` for non-interactive delegation. Use `--interactive` flag (or `CLAUDE_DELEGATE_PERMISSION_MODE=acceptEdits`) for auto-accept edits with tool-command prompts. `--bypass` is kept as an explicit alias for the default.
- Unknown tasks fall back to `deepseek-v4-pro[1m]` and `max` effort. Classified tiny/routine tasks use flash, while debugging and architecture tasks use pro. Override via `--pro`, `--flash`, `--effort`, or the matching env vars.
- MCP defaults to `all`, preserving normal Claude Code project/user MCP discovery. Use `--mcp none` for a strict empty MCP config, or `--mcp jira|linear|sequential-thinking` to load only one server from `.mcp.json`.
- Prompt adaptation defaults to `auto`. Templates preserve the full original prompt; use `--full-context` or `CLAUDE_DELEGATE_CONTEXT_MODE=full` to bypass templates.
- Subagents default to `off`; the wrapper passes `--disallowedTools Task Agent` unless `--allow-subagents` or `CLAUDE_DELEGATE_SUBAGENTS=on` is set.
- Heartbeat runs as a daemon thread in the pipeline. Use `CLAUDE_DELEGATE_HEARTBEAT_SECONDS=0` to disable it.
- Compact output includes profiling metadata. Set `CLAUDE_DELEGATE_PROFILE_LOG` to append JSONL records.
- When consumed by an orchestrator, set `CLAUDE_DELEGATE_DIR` to this project's root before invoking.
