#!/usr/bin/env python3
"""Runtime Safety Guardrail — pre-tool-use hook for L4 dim #6.

Decision table:
  is_destructive  safety_confirm  pattern(count≥3)  decision
  False           any             —                 ALLOW
  True            empty           —                 WARN
  True            non-empty       no                ALLOW
  True            non-empty       yes               BLOCK

Exit codes: ALLOW=0  BLOCK=1  WARN=2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import types as _stdlib_types
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

Decision = Literal["ALLOW", "WARN", "BLOCK"]

_HIGH_FREQ_THRESHOLD = 3

# Global state — lazily populated by _load_reflexion()
_REFLEXION: Optional[object] = None


def _load_reflexion() -> Optional[object]:
    """Lazily load _reflexion.py from the scripts/ directory via exec().

    Uses direct execution so no __init__.py is required in scripts/.
    Silently returns None if the file is absent or unimportable.
    """
    global _REFLEXION
    if _REFLEXION is not None:
        return _REFLEXION
    rx_path = Path(__file__).parent / "_reflexion.py"
    if not rx_path.exists():
        _REFLEXION = None
        return None
    try:
        ns: dict[str, object] = {"__name__": "_reflexion"}
        ns.update(globals())
        rx_code = rx_path.read_text(encoding="utf-8")
        exec(rx_code, ns)
        _REFLEXION = _stdlib_types.SimpleNamespace(
            FailurePattern=ns.get("FailurePattern"),
            append_or_increment=ns.get("append_or_increment"),
        )
    except Exception:  # pragma: no cover
        _REFLEXION = None
    return _REFLEXION


def _reflect_block(patterns_path: Path, call: ToolCall, matched: list[dict]) -> None:
    """L4 #6+#3闭环: BLOCK 决策时自动追加到 failure-patterns.md."""
    rx = _load_reflexion()
    if rx is None:
        return
    aws_match = re.match(r"^aws\s+([a-z][a-z0-9-]*)", call.tool_name, re.I)
    skill = f"{aws_match.group(1)}-ops" if aws_match else call.tool_name
    sample = next(
        (p for p in matched if p.get("count", 0) >= _HIGH_FREQ_THRESHOLD),
        matched[0] if matched else {},
    )
    pattern = rx.FailurePattern(
        skill=sample.get("skill", skill),
        command=sample.get("command", call.tool_name),
        error=f"BLOCK: high-freq pattern matched (count={sample.get('count', '?')})",
        root_cause=(
            f"runtime_safety BLOCK: '{call.tool_name}' matched failure pattern "
            f"(count={sample.get('count', '?')}); matched_patterns={len(matched)}"
        ),
        fix="Review failure-patterns.md for this command; inspect the blocking pattern",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    try:
        rx.append_or_increment(patterns_path, pattern)
    except Exception:  # pragma: no cover — never mask the BLOCK exit
        pass


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
    # 6 required cols: skill | command | error | root_cause | fix | count
    # col 7 (timestamp) is optional — §1 legacy entries omit it
    if len(cols) < 6:
        return None
    count_str = cols[5].lstrip("-")
    if not count_str.isdigit():
        return None
    return {
        "skill": cols[0].strip("`").lower(),
        "command": cols[1].strip("`").lower(),
        "error": cols[2].strip("`"),
        "root_cause": cols[3].strip("`"),
        "fix": cols[4].strip("`"),
        "count": int(count_str),
        "timestamp": cols[6] if len(cols) >= 7 else "",
    }


def load_failure_patterns(path: Path) -> list[dict]:
    """Parse a markdown table of failure patterns into a list of dicts."""
    patterns: list[dict] = []
    text = path.read_text(encoding="utf-8")
    in_table = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Case-insensitive header detection: normalize underscores/spaces
        normalized = line.lower().replace("_", " ")
        if "skill" in normalized and "command" in normalized and "root cause" in normalized:
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|---") or line.startswith("|-"):
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cols = _split_row(line)
        # Header bleed-through guard: skip separator-like rows
        if cols and cols[0].lstrip("-").isdigit():
            continue
        pat = _row_to_pattern(cols)
        if pat:
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
_AWS_CMD = re.compile(
    r"^aws\s+([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?", re.IGNORECASE
)


def _parse_aws_command(s: str) -> tuple[str | None, str | None]:
    """Return (service, op) lowercased; (None, None) if not an `aws <svc> ...` form."""
    m = _AWS_CMD.match(s.strip())
    if not m:
        return (None, None)
    op = m.group(2)
    if op:
        op = op.lower()
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


def check_tool_call(call: ToolCall, patterns: list[dict]) -> CheckResult:
    """Core decision function: ALLOW / WARN / BLOCK."""
    matched = match_patterns(call, patterns)
    has_confirm = bool(call.safety_confirm.strip())

    if not call.is_destructive:
        return CheckResult(
            decision="ALLOW",
            reason="non-destructive op, no guardrail needed",
            matched_patterns=matched,
        )

    if matched and any(p.get("count", 0) >= _HIGH_FREQ_THRESHOLD for p in matched):
        return CheckResult(
            decision="BLOCK",
            reason=(
                f"destructive op '{call.tool_name}' matched high-freq "
                f"failure pattern(s) (count >= {_HIGH_FREQ_THRESHOLD}); "
                f"refusing to proceed — use a known-safe confirmation token"
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
    parser.add_argument(
        "--reflect-on-block", action="store_true",
        help="L4 #6+#3闭环: reflexion-append to failure-patterns.md on BLOCK.",
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
    if args.reflect_on_block and result.decision == "BLOCK":
        _reflect_block(Path(args.patterns[0]), call, result.matched_patterns)
    return _decision_exit_code(result.decision)


if __name__ == "__main__":
    sys.exit(main())
