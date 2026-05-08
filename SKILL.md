---
name: claude-code-delegator
description: Delegate a Codex-authored implementation plan to Claude Code, then review the resulting diff and optionally send one correction pass. Use when the user asks Codex to plan while Claude Code executes, mentions "Claude Code 执行", "让 claude code 做", "one pass", or wants a plan-execute-review loop.
---

# Claude Code Delegator

## Contract

Use this workflow when the user wants Codex to own planning/review while Claude Code performs implementation.

Required loop:

1. Codex reads enough local context to make a concrete plan.
2. Codex shows the Codex-authored implementation plan to the user before invoking Claude Code.
3. Codex invokes Claude Code to execute that plan.
4. Codex shows Claude Code's output to the user, including its changed-file list and verification results.
5. Codex reviews Claude Code's diff and test output.
6. If needed, Codex shows the targeted correction plan and invokes Claude Code once more.
7. Codex shows the correction pass output, then gives the user a concise final review with changed files, tests, and residual risk.

## Invocation

Always invoke Claude Code through the bundled wrapper. By default it uses `deepseek-v4-pro[1m]`, `max` effort, `bypassPermissions`, and compact `quiet` output for non-interactive plan execution. Adaptive reasoning is controlled by `--effort` (default `max`); thinking tokens are only set when `CLAUDE_DELEGATOR_THINKING_TOKENS` is explicitly provided.

Prefer the bundled wrapper to avoid flag drift:

```bash
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh "$PROMPT"
```

### Delegation Suitability

Do not delegate tiny local inspection tasks unless the user explicitly asks to use Claude Code. If the task is read-only, deterministic, local to the current machine, and likely needs three or fewer shell commands, Codex should run it directly and report the result. Delegation has leverage for implementation, multi-file edits, independent execution, Jira/MCP work, or tasks where Claude Code is specifically requested.

### Model

Two models available. Default is **pro** for complex plans; use **flash** for simple/high-throughput tasks.

Prefer the wrapper flags when switching models for one invocation:

```bash
# Use flash for this invocation:
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh --flash "$PROMPT"

# Use pro explicitly:
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh --pro "$PROMPT"
```

| Env var | Pro (default) | Flash |
|---------|---------------|-------|
| `CLAUDE_DELEGATOR_MODEL` | `deepseek-v4-pro[1m]` | `deepseek-v4-flash[1m]` |

```bash
# Env override is also supported:
CLAUDE_DELEGATOR_MODEL='deepseek-v4-flash[1m]' \
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh "$PROMPT"
```

### Output Mode

Default output mode is `quiet`: the wrapper asks Claude Code for final JSON output, pipes it through `compact-claude-stream.py`, and returns only the final result plus model, permission mode, usage, cost, and terminal status. This is the preferred mode for normal delegation because Codex does not need to ingest every thinking or partial-message event.

Use `--stream` only when debugging Claude Code itself, diagnosing permission hangs, inspecting tool events, or preserving the raw stream is necessary:

```bash
# Compact output, default:
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh --flash "$PROMPT"

# Raw verbose stream-json output for debugging:
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh --flash --stream "$PROMPT"
```

### Other overrides

```bash
CLAUDE_DELEGATOR_EFFORT=medium \           # default: max
CLAUDE_DELEGATOR_PERMISSION_MODE=acceptEdits \  # default: bypassPermissions
CLAUDE_DELEGATOR_THINKING_TOKENS=0 \       # unset by default (--effort controls reasoning)
CLAUDE_DELEGATOR_OUTPUT_MODE=stream \      # default: quiet
/Users/dongliang/.codex/skills/claude-code-delegator/scripts/run-claude-code.sh "$PROMPT"
```

## Prompt Requirements

The prompt sent to Claude Code must include:

- The user's goal.
- The concrete plan to execute.
- Ownership boundaries: files/modules it may touch.
- A warning not to revert unrelated user changes.
- A requirement to apply `/andrej-karpathy-skills:karpathy-guidelines` before executing the plan.
- Verification commands to run.
- A request to report changed files and command results.

Before invoking Claude Code, show the user the concrete implementation plan that Codex authored. This should be concise but specific enough to make ownership boundaries and verification commands visible.

Invoke the wrapper directly without adding `timeout`. If Claude Code appears silent, re-run with `--stream` and inspect the wrapper's stream-json events before assuming it is stuck.

After Claude Code returns, show the user Claude Code's output. In quiet mode, show the compact final report. In stream mode, prefer the final result block when it is concise; if the stream output is noisy, summarize the key lines but preserve changed files, command results, errors, and any stated caveats.

## Review Requirements

After Claude Code returns:

1. Show Claude Code's output to the user before giving Codex's review.
2. Run `git diff --stat` and inspect relevant diffs.
3. Run focused tests or checks.
4. If the diff is wrong or incomplete, show the targeted correction plan, then send one targeted correction prompt using the same wrapper invocation.
5. Show the correction pass output before the final review.
6. Do not accept unreviewed changes just because Claude Code completed successfully.

## Issue Tracker Comment Formatting

When posting comments to Jira through MCP tools, use plain readable text without Markdown formatting syntax. The Jira MCP `add_comment` tool accepts a plain text body, not Markdown — Markdown control characters are displayed literally.

Rules:
- Do not use `**bold**`, `*italic*`, backticks, fenced code blocks, Markdown tables, or `[links](url)` syntax.
- Do not use task list syntax (`- [ ]`, `- [x]`).
- Use simple `-` bullet lists and indentation for structure (hyphen lists display cleanly as plain text).
- For inline code references, use plain quotes or parentheses instead of backticks.
- For emphasis, use natural language phrasing rather than bold/italic markers.
- Keep full Markdown formatting for responses to the user — this rule applies only to issue tracker comments.

The bundled `scripts/jira-safe-text.py` utility converts Markdown text to Jira-safe plain text. Pipe Markdown through it before posting to Jira:

```bash
echo "**bold** and *italic*" | /Users/dongliang/.codex/skills/claude-code-delegator/scripts/jira-safe-text.py
# Output: bold and italic
```

## Jira Duplicate Search Failure

When delegating Jira issue creation, the prompt must instruct Claude Code: if the Jira MCP search endpoint is deprecated, unavailable, or returns an error, the tool must report the failure explicitly and must not claim that duplicates were avoided. If issue creation proceeds despite the unavailable search, the output must label the issue's duplicate status as unverified.

## Known Failure Mode

Plain `claude -p` with default permissions can appear to hang because Claude Code is waiting on permission requests. `acceptEdits` only auto-accepts file edits and can still block Bash/tool commands such as `.venv/bin/python ...`; use the wrapper default `bypassPermissions` for trusted local repo delegation. If a safer mode is intentionally needed, override it with `CLAUDE_DELEGATOR_PERMISSION_MODE=acceptEdits` or another Claude Code permission mode and expect possible interactive approval.

Provider or org/auth access errors usually mean Claude Code is not currently switched to a provider that can serve `deepseek-v4-pro[1m]`, or the provider token in `~/.claude/settings.json` is malformed/expired. Confirm the configured `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, and model values without printing secret token contents.
