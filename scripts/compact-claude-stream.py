#!/usr/bin/env python3
"""Compact Claude Code stream-json into a reviewable final report."""

from __future__ import annotations

import json
import os
import sys
from typing import Any


def _fmt_usage(usage: dict[str, Any]) -> str:
    parts = []
    for key in ("input_tokens", "cache_read_input_tokens", "output_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            parts.append(f"{key}={value}")
    return ", ".join(parts)


def main() -> int:
    init: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    errors: list[str] = []
    raw = sys.stdin.read()

    events: list[dict[str, Any]] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            events.append(parsed)
        elif isinstance(parsed, list):
            events.extend(item for item in parsed if isinstance(item, dict))
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                errors.append(line[:500])
                continue
            if isinstance(event, dict):
                events.append(event)

    for event in events:
        event_type = event.get("type")
        if event_type == "system" and event.get("subtype") == "init":
            init = event
        elif event_type == "result":
            result = event
        elif "result" in event or "usage" in event:
            result = event
        elif event.get("is_error") is True:
            errors.append(json.dumps(event, ensure_ascii=False)[:1000])

    model = (init or {}).get("model") or os.environ.get("CLAUDE_DELEGATOR_OBSERVED_MODEL")
    permission_mode = (init or {}).get("permissionMode") or os.environ.get(
        "CLAUDE_DELEGATOR_OBSERVED_PERMISSION_MODE"
    )
    cwd = (init or {}).get("cwd") or os.environ.get("CLAUDE_DELEGATOR_OBSERVED_CWD")

    if model or permission_mode or cwd:
        print("Claude Code")
        if model:
            print(f"- model: {model}")
        if permission_mode:
            print(f"- permissionMode: {permission_mode}")
        if cwd:
            print(f"- cwd: {cwd}")

    if result:
        if model or permission_mode or cwd:
            print()
        print("Result")
        print(result.get("result") or "")

        usage = result.get("usage")
        if isinstance(usage, dict):
            usage_text = _fmt_usage(usage)
            if usage_text:
                print()
                print("Usage")
                print(f"- {usage_text}")

        cost = result.get("total_cost_usd")
        if isinstance(cost, (int, float)):
            print(f"- total_cost_usd={cost:.6f}")

        terminal_reason = result.get("terminal_reason")
        if terminal_reason:
            print(f"- terminal_reason={terminal_reason}")

    if errors:
        if init or result:
            print()
        print("Stream Warnings")
        for error in errors[:5]:
            print(f"- {error}")
        if len(errors) > 5:
            print(f"- ... {len(errors) - 5} more")

    if not init and not result and not errors:
        return 1
    if result and result.get("is_error") is True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
