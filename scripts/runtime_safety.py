#!/usr/bin/env python3
"""Runtime Safety Guardrail — pre-tool-use hook for L4 dim #6.

Cross-references an in-flight tool call against the historical failure-pattern
library (failure-patterns.md, written by `_reflexion.py`) and returns a
decision: ALLOW / WARN / BLOCK.

Contract — see `docs/superpowers/specs/2026-07-25-runtime-safety-design.md`.

Decision rules:
    1. Non-destructive             -> ALLOW (no pattern lookup).
    2. Destructive + no confirm     -> WARN (require confirm).
    3. Destructive + confirm + no match            -> ALLOW.
    4. Destructive + match (count >= 3)            -> BLOCK (regardless of confirm).
    5. Destructive + confirm + match (count < 3)   -> WARN (suggest more confirm).

CLI:
    echo '{"tool_name":..., "args":..., "is_destructive":..., "safety_confirm":...}' \\
        | python3 scripts/runtime_safety.py --patterns docs/failure-patterns.md
    exit 0 = ALLOW, 1 = BLOCK, 2 = WARN.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Decision = Literal["ALLOW", "WARN", "BLOCK"]

_HIGH_FREQ_THRESHOLD = 3

_HEADER_COLS = (
    "skill", "command", "error", "root_cause", "fix", "count", "timestamp",
)


@dataclass
class ToolCall:
    tool_name: str
    args: dict
    is_destructive: bool
    safety_confirm: str = ""


@dataclass
class CheckResult:
    decision: Decision
    reason: str
    matched_patterns: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern loading
# ---------------------------------------------------------------------------

def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip("|").split("|")]


def _row_to_pattern(cols: list[str]) -> dict | None:
    if len(cols) < len(_HEADER_COLS):
        return None
    skill, command, error, root_cause, fix, count, timestamp = cols[:7]
    try:
        count_int = int(count)
    except (TypeError, ValueError):
        return None
    return {
        "skill": skill,
        "command": command,
        "error": error,
        "root_cause": root_cause,
        "fix": fix,
        "count": count_int,
        "timestamp": timestamp,
        "error_signature": f"{skill}|{command}|{error[:50]}",
    }


def load_failure_patterns(path: Path) -> list[dict]:
    """Parse a markdown table of failure patterns into a list of dicts.

    The expected schema is the 7-column table produced by `_reflexion.py`:
        `| skill | command | error | root_cause | fix | count | timestamp |`

    Returns an empty list if the file does not exist or has no data rows.
    Malformed rows are silently dropped (the file is hand-curated).
    """
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    patterns: list[dict] = []
    header_seen = False
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        if not header_seen:
            if "---" in line:
                header_seen = True
            continue
        cols = _split_row(line)
        pat = _row_to_pattern(cols)
        if pat is not None:
            patterns.append(pat)
    return patterns


# ---------------------------------------------------------------------------
# Pattern matching
# ---------------------------------------------------------------------------

# AWS CLI command token extractor: `aws <svc> <op> [args...]` -> (svc, op)
# Both groups must match for an op-level pattern to apply against a call.
# A service-only pattern (no op) intentionally does NOT match any op call,
# because doing so would over-match every operation on the service
# (defense vs F-3 over-matching risk).
_AWS_CMD = re.compile(r"^aws\s+([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?", re.IGNORECASE)


def _parse_aws_command(s: str) -> tuple[str | None, str | None]:
    """Return (service, op) lowercased; (None, None) if not an `aws <svc> ...` form."""
    s = (s or "").strip()
    if not s:
        return (None, None)
    m = _AWS_CMD.match(s)
    if not m:
        return (None, None)
    op = m.group(2).lower() if m.group(2) else None
    return (m.group(1).lower(), op)


def _match(call: ToolCall, pattern: dict) -> bool:
    """Token-level AWS CLI matching with bidirectional-substring fallback.

    AWS CLI commands (matches `^aws <svc> <op>`): require both `service` AND
    `op` tokens to be identical between pattern and call. A service-only
    pattern (no op) returns False on purpose (over-matching protection,
    see F-3 / session self-reflection).

    Non-AWS-CLI patterns (boto3 dotted methods, custom tool names) fall
    through to case-insensitive bidirectional substring matching.
    """
    cmd = (pattern.get("command") or "").strip()
    tool = (call.tool_name or "").strip()
    if not cmd or not tool:
        return False
    p_svc, p_op = _parse_aws_command(cmd)
    c_svc, c_op = _parse_aws_command(tool)
    if p_svc is None or c_svc is None:
        # Fallback path (boto3 / SDK / custom): legacy bidirectional substring.
        return cmd.lower() in tool.lower() or tool.lower() in cmd.lower()
    # AWS CLI: match requires same service AND same op (when both specify op).
    if p_svc != c_svc:
        return False
    if not p_op or not c_op:
        # Service-only pattern or call: never matches an op-level concrete call.
        return False
    return p_op == c_op


def match_patterns(call: ToolCall, patterns: list[dict]) -> list[dict]:
    """Return all patterns that match this tool call (file order preserved)."""
    return [p for p in patterns if _match(call, p)]


# ---------------------------------------------------------------------------
# Decision engine
# ---------------------------------------------------------------------------

def check_tool_call(call: ToolCall, patterns: list[dict]) -> CheckResult:
    """Core decision function: ALLOW / WARN / BLOCK.

    See module docstring for the 5-rule decision table.
    """
    matched = match_patterns(call, patterns)
    has_confirm = bool(call.safety_confirm.strip())

    if not call.is_destructive:
        return CheckResult(
            decision="ALLOW",
            reason="non-destructive op, no guardrail needed",
            matched_patterns=matched,
        )

    if matched and any(
        p.get("count", 0) >= _HIGH_FREQ_THRESHOLD for p in matched
    ):
        sample = next(
            p for p in matched if p.get("count", 0) >= _HIGH_FREQ_THRESHOLD
        )
        return CheckResult(
            decision="BLOCK",
            reason=(
                f"destructive op '{call.tool_name}' matches high-freq "
                f"failure pattern (count={sample['count']}); "
                f"refusing without dry-run"
            ),
            matched_patterns=matched,
        )

    if not has_confirm:
        return CheckResult(
            decision="WARN",
            reason=(
                f"destructive op '{call.tool_name}' requires "
                f"safety_confirm before execution"
            ),
            matched_patterns=matched,
        )

    if matched:
        # All matches low-freq (count < 3) — caller can re-confirm.
        return CheckResult(
            decision="WARN",
            reason=(
                f"destructive op '{call.tool_name}' matches low-freq "
                f"failure pattern(s); proceed only with explicit re-confirmation"
            ),
            matched_patterns=matched,
        )

    return CheckResult(
        decision="ALLOW",
        reason=(
            f"destructive op '{call.tool_name}' with confirm token, "
            f"no matched pattern"
        ),
        matched_patterns=matched,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _read_patterns_arg(paths: list[Path]) -> list[dict]:
    out: list[dict] = []
    for p in paths:
        out.extend(load_failure_patterns(p))
    return out


def _decision_exit_code(decision: Decision) -> int:
    return {"ALLOW": 0, "BLOCK": 1, "WARN": 2}[decision]


def _emit(result: CheckResult) -> None:
    payload = {
        "decision": result.decision,
        "reason": result.reason,
        "matched_patterns": result.matched_patterns,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="runtime_safety",
        description="Pre-tool-use safety guardrail (L4 dim #6).",
    )
    parser.add_argument(
        "--patterns", action="append", required=True,
        help="Path to a failure-patterns.md file (repeatable).",
    )
    args = parser.parse_args(argv)

    raw = sys.stdin.read().strip()
    if not raw:
        sys.stderr.write("error: empty stdin, expected JSON ToolCall\n")
        return 1
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"error: invalid JSON: {exc}\n")
        return 1

    call = ToolCall(
        tool_name=str(data.get("tool_name", "")),
        args=dict(data.get("args", {}) or {}),
        is_destructive=bool(data.get("is_destructive", False)),
        safety_confirm=str(data.get("safety_confirm", "") or ""),
    )
    patterns = _read_patterns_arg([Path(p) for p in args.patterns])
    result = check_tool_call(call, patterns)
    _emit(result)
    return _decision_exit_code(result.decision)


if __name__ == "__main__":
    sys.exit(main())
