# Claude Code Delegate

## What this is

A toolkit that lets an orchestrating AI (Codex, Cursor, etc.) delegate implementation plans to Claude Code for execution, then review the resulting diff.

## Key files

- `SKILL.md` — The orchestrator contract. This is what Codex/the orchestrator reads to understand the delegation workflow.
- `scripts/run-claude-code.sh` — The wrapper that invokes Claude Code with consistent flags.
- `scripts/delegation-adapter.py` — Classifies tasks, compresses prompts, and writes metadata for the wrapper.
- `scripts/compact-claude-stream.py` — Compacts JSON stream output into a readable report.
- `scripts/jira-safe-text.py` — Strips Markdown for Jira MCP plain-text comments.
- `tests/run_tests.sh` — Test runner (bash, no external deps).
- `CONTEXT.md` — Domain glossary for the project.

## Commands

```bash
# Run tests
bash tests/run_tests.sh

# Test the wrapper directly
bash scripts/run-claude-code.sh --flash "test prompt"
```

## Design notes

- The wrapper defaults to `bypassPermissions` for non-interactive delegation. Use `--interactive` flag (or `CLAUDE_DELEGATOR_PERMISSION_MODE=acceptEdits`) for auto-accept edits with tool-command prompts. `--bypass` is kept as an explicit alias for the default.
- Unknown tasks fall back to `deepseek-v4-pro[1m]` and `max` effort. Classified tiny/routine tasks use flash, while debugging and architecture tasks use pro. Override via `--pro`, `--flash`, `--effort`, or the matching env vars.
- MCP defaults to `all`, preserving normal Claude Code project/user MCP discovery. Use `--mcp none` for a strict empty MCP config, or `--mcp jira|linear|sequential-thinking` to load only one server from `.mcp.json`.
- Prompt adaptation defaults to `auto`. Use `--full-context` or `CLAUDE_DELEGATOR_CONTEXT_MODE=full` to bypass templates.
- Compact output includes profiling metadata. Set `CLAUDE_DELEGATOR_PROFILE_LOG` to append JSONL records.
- When consumed by an orchestrator, set `CLAUDE_DELEGATOR_DIR` to this project's root before invoking.
