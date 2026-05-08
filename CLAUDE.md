# Claude Code Delegate

## What this is

A toolkit that lets an orchestrating AI (Codex, Cursor, etc.) delegate implementation plans to Claude Code for execution, then review the resulting diff.

## Key files

- `SKILL.md` — The orchestrator contract. This is what Codex/the orchestrator reads to understand the delegation workflow.
- `scripts/run-claude-code.sh` — The wrapper that invokes Claude Code with consistent flags.
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

- The wrapper defaults to `acceptEdits` permission mode. Override with `CLAUDE_DELEGATOR_PERMISSION_MODE=bypassPermissions` for fully non-interactive use.
- Model defaults (`deepseek-v4-pro[1m]`) reflect a custom provider setup. Override via `CLAUDE_DELEGATOR_MODEL`.
- When consumed by an orchestrator, set `CLAUDE_DELEGATOR_DIR` to this project's root before invoking.
