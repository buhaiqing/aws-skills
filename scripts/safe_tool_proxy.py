#!/usr/bin/env python3
"""Execute structured tool calls only after Runtime Safety allows them."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from runtime_safety import ToolCall, check_tool_call, load_failure_patterns


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _tool_call_from_payload(command: list[str], payload: dict) -> ToolCall:
    if len(command) >= 3 and Path(command[0]).name.lower() == "aws":
        tool_name = " ".join(command[:3])
        call_args = {"argv": command[3:]}
        if payload.get("account"):
            call_args["account"] = str(payload["account"])
    else:
        tool_name = str(payload.get("tool_name") or " ".join(command[:3]))
        call_args = dict(payload.get("args") or {})
    return ToolCall(
        tool_name=tool_name,
        args=call_args,
        is_destructive=payload.get("is_destructive"),
        safety_confirm=str(payload.get("safety_confirm") or ""),
    )


def _safe_environment() -> dict[str, str]:
    allowed = {"HOME", "PATH", "TMPDIR", "LANG", "LC_ALL", "HTTPS_PROXY", "NO_PROXY"}
    return {
        key: value for key, value in os.environ.items()
        if key in allowed or key.startswith("AWS_") or key.startswith("LC_")
    }


def _is_trusted_aws_executable(command_name: str) -> bool:
    trusted = shutil.which("aws")
    if trusted is None:
        return False
    requested = shutil.which(command_name) if Path(command_name).parent == Path(".") else command_name
    if requested is None:
        return False
    try:
        return Path(requested).resolve(strict=True).samefile(Path(trusted).resolve(strict=True))
    except OSError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="safe_tool_proxy")
    parser.add_argument("--patterns", action="append", required=True)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    raw = sys.stdin.read().strip()
    if not raw:
        _emit({"decision": "BLOCK", "executed": False, "reason": "empty JSON input"})
        return 1
    try:
        payload = json.loads(raw)
        command = payload["command"]
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            raise ValueError("command must be a non-empty string list")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _emit({"decision": "BLOCK", "executed": False, "reason": f"invalid input: {exc}"})
        return 1

    if Path(command[0]).name.lower() != "aws" or not _is_trusted_aws_executable(command[0]):
        _emit({
            "decision": "BLOCK", "executed": False,
            "reason": "safe_tool_proxy allows only the trusted aws executable from PATH",
        })
        return 1

    call = _tool_call_from_payload(command, payload)
    patterns = []
    for pattern_path in args.patterns:
        patterns.extend(load_failure_patterns(Path(pattern_path)))
    result = check_tool_call(call, patterns)
    if result.decision != "ALLOW":
        _emit({
            "decision": result.decision,
            "executed": False,
            "reason": result.reason,
            "matched_patterns": result.matched_patterns,
        })
        return 1
    if args.dry_run:
        _emit({
            "decision": "ALLOW", "executed": False, "would_execute": True,
            "command": command,
        })
        return 0

    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=args.timeout, check=False,
            env=_safe_environment(),
        )
    except subprocess.TimeoutExpired:
        _emit({
            "decision": "BLOCK", "executed": True, "exit_code": 124,
            "reason": f"command exceeded {args.timeout}s",
        })
        return 1
    _emit({
        "decision": "ALLOW",
        "executed": True,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    })
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
