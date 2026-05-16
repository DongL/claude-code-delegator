# PRD: OpenCode Executor Backend

## Problem Statement

The claude-code-delegate pipeline currently supports a single executor backend: Claude Code (`claude -p`). This creates two constraints:

1. **Vendor lock-in**: Claude Code requires an Anthropic API key and is tied to Anthropic's model availability. Users who prefer open-source models (DeepSeek, Qwen) or need local-only operation cannot use the delegation pipeline without an Anthropic account.

2. **Model selection friction**: Users who run OpenCode as their primary coding agent must maintain a separate Claude Code installation solely for delegation. They cannot route delegation tasks to the same OpenCode instance they already use.

Adding an OpenCode executor backend removes both constraints: users bring their own model provider (OpenCode supports Zen, DeepSeek, Qwen, and OpenAI-compatible endpoints) and share a single agent installation.

## Solution

Add a second executor backend (`opencode`) that runs `opencode run` instead of `claude -p`. Selection is via `--executor opencode` flag, `--opencode` shorthand, or `CLAUDE_DELEGATE_EXECUTOR=opencode` environment variable. Both backends share the same pipeline stages (classify, envelope, invoke, compact, profile) — only the subprocess invocation and output parsing differ.

Existing delegations default to `claude-code` and are unaffected.

## User Stories

1. As a developer without an Anthropic API key, I want to run the delegation pipeline against OpenCode with a DeepSeek or Qwen provider, so that I can use the full skill without an Anthropic subscription.

2. As a developer who already uses OpenCode, I want to route delegation tasks to my existing OpenCode installation, so that I maintain a single agent toolchain.

3. As an orchestrator agent, I want to select the executor per-delegation via a flag (`--executor opencode`), so that I can route simple tasks to a cheaper backend without changing global configuration.

4. As an operator, I want heartbeat monitoring with CPU stall detection to work identically across both backends, so that stuck OpenCode subprocesses are detected and terminated the same way as stuck Claude Code subprocesses.

5. As an operator, I want the output compactor to parse both Claude Code stream-json and OpenCode event-stream formats transparently, so that downstream consumers (profile logger, result reporters) do not need to know which backend ran.

6. As a developer debugging a delegation, I want to see which executor was used in the compacted report, so that I can correlate behavior differences with backend choice.

7. As an operator, I want to control the executor via environment variable (`CLAUDE_DELEGATE_EXECUTOR`) across all delegations, so that I don't need to change every invocation when switching backends.

## Functional Requirements

### FR1: Executor selection

The executor is selected by one of (in precedence order):
- `--opencode` flag (shorthand for `--executor opencode`)
- `--executor claude-code|opencode` flag
- `CLAUDE_DELEGATE_EXECUTOR` environment variable
- Default: `claude-code`

The `executor` field appears in `InvokerConfig` and flows through `run_delegation_pipeline()` and `start_delegation_async()`. Selection affects which subprocess command is built (`claude -p` vs `opencode run`) and how the heartbeat monitors the process.

### FR2: Model mapping

OpenCode uses `provider/model` format (e.g., `deepseek/deepseek-v4-flash`). Claude Code uses short names (e.g., `deepseek-v4-flash[1m]`). The `CLAUDE_CODE_MODEL_MAP` in `scripts/opencode_invoker.py` translates known Claude Code model IDs to OpenCode provider strings:

| Claude Code model | OpenCode provider/model |
|---|---|
| `deepseek-v4-flash` | `deepseek/deepseek-v4-flash` |
| `deepseek-v4-pro` | `deepseek/deepseek-chat` |
| `claude-sonnet-4` | `deepseek/deepseek-v4-flash` |
| `claude-opus-4` | `deepseek/deepseek-chat` |
| `claude-haiku-4` | `deepseek/deepseek-v4-flash` |

Unmapped models fall back to `deepseek/{base}`. Empty model defaults to `opencode/qwen3.6-plus-free`. Models with a `/` prefix are passed through unchanged (user supplies the full provider string).

### FR3: Permission bridging

OpenCode uses `--dangerously-skip-permissions` instead of `--permission-mode bypassPermissions`. The bridge maps `bypassPermissions` → `--dangerously-skip-permissions`. The `InvokerConfig.permission_mode` field is shared; the mapping happens inside `build_opencode_args()`.

### FR4: No effort parameter

OpenCode does not support `--effort` or analog. The `effort` field in `InvokerConfig` is accepted but ignored when `executor == "opencode"`. Reasoning budget is configured at the model provider level.

### FR5: Event format parsing

OpenCode emits a newline-delimited JSON event stream with three relevant event types:
- `text`: Contains a `part.type == "text"` with incremental response text.
- `step_finish`: Contains `part.tokens` (input/output/cache) and `part.cost`.
- `error`: Contains `error.data.message` with failure details.

The shared `parse_compact_output()` in `compact-claude-stream.py` detects the OpenCode format by the presence of `text` or `error` events and concatenates incremental text for the final result, rather than looking for a single `result` JSON object as Claude Code produces.

### FR6: Heartbeat with CPU stall detection

The `start_heartbeat()` function in `opencode_invoker.py` mirrors the one in `invoker.py`. It:
- Prints `OpenCode still running: ...` to stderr at configurable intervals (default 30s).
- Reports `elapsed`, `cpu=+Ns` (CPU delta since last tick), and `cpu_stall=N` (wall-clock duration since CPU last advanced).
- Applies an inactivity timeout: if CPU has not advanced for `CLAUDE_DELEGATE_INACTIVITY_TIMEOUT_SECONDS`, sends SIGTERM, waits 5s, then SIGKILL.
- Excludes the `effort` field (absent in OpenCode) and includes `mode` (output mode) instead.

### FR7: Environment bridging

The child process environment includes OpenCode-specific settings (`OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR`, etc.) via `load_opencode_env()`. These are backfilled from local config files when sandbox hooks fail to inject them. Environment variable `setdefault` preserves explicit overrides.

### FR8: Classifier integration

A third model tier `qwen` resolves to `QWEN_MODEL = "opencode/qwen3.6-plus-free"` in `classifier.py`. This is a dedicated OpenCode default model, included for users who always run the `qwen` tier but may use either executor.

## Non-Functional Requirements

### NFR1: Performance

- OpenCode subprocess launch overhead must be comparable to Claude Code (subprocess.Popen, no warm-up).
- The heartbeat monitoring thread adds <1ms overhead per tick and does not block on I/O.
- Event parsing in `parse_compact_output()` is O(n) in number of JSON lines, same as Claude Code parsing.

### NFR2: Reliability

- Heartbeat monitors CPU stall and applies timeout with SIGTERM→SIGKILL escalation, matching Claude Code behavior.
- Non-zero exit codes from OpenCode are treated as delegation failures, same as Claude Code.
- The output compactor gracefully handles malformed OpenCode event lines (skips with warning, continues parsing).
- OpenCode subprocess environment inherits from parent with config backfill — no silent env miss.

### NFR3: Security

- Permission bypass in OpenCode uses the same `bypassPermissions` signal as Claude Code, just a different CLI flag.
- No new code execution surface. OpenCode runs as a subprocess with the same trust boundary as Claude Code.
- Config backfill reads only from well-known paths (`~/.config/opencode/config.json`, `./opencode.json[c]`).

## Acceptance Criteria

1. `--opencode` flag routes to `opencode run` subprocess instead of `claude -p`.
2. Model IDs map correctly through `CLAUDE_CODE_MODEL_MAP`, including unmapped fallback.
3. `--dangerously-skip-permissions` is set when `permission_mode == "bypassPermissions"`.
4. OpenCode event stream (text/step_finish/error) is parsed into a result struct indistinguishable from Claude Code output.
5. Heartbeat prints to stderr with correct format (elapsed, cpu, cpu_stall, model, mcp, mode).
6. Environment config is backfilled from at least one of the three config file locations.
7. The `qwen` model tier produces `opencode/qwen3.6-plus-free`.
8. No regression on existing `claude-code` executor — all existing tests pass with default executor.

## Out of Scope

- Streaming output mode for OpenCode (`output_mode == "stream"` falls through to default format; OpenCode has no stream-json equivalent).
- `--agent` flag for OpenCode subagent support (subagent_mode is not mapped; OpenCode defaults apply).
- DeepSeek chat templates or provider-specific prompt formatting.
- Multi-executor multiplexing (round-robin, cost-based routing, fallback).
- OpenCode version detection or compatibility enforcement.

## Further Notes

- The `ALLOWED_MODELS` frozenset is declared empty and reserved for future use. It currently has no effect.
- The `subagent_mode` field is accepted but intentionally unmapped — no `--agent` flag is added to `opencode run`.
- `_validate_model()` defaults to `opencode/qwen3.6-plus-free` when model is empty, independent of executor.
