#!/usr/bin/env python3
"""Shadow Executor — ADR-0001 M2.

ExecutionPlan/plan_hash → Shadow (dry-run|describe|simulate) → redacted
evidence under audit-results/shadow/. No mutating AWS APIs. Tests inject
a runner stub or use mode='simulate' (local expected_diff only).
Accepts ExecutionPlan / PlanLike / mapping / explicit plan_hash.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Protocol, runtime_checkable

REPO = Path(__file__).resolve().parents[1]
SHADOW_DIR = REPO / "audit-results" / "shadow"

ShadowMode = Literal["dry-run", "describe", "simulate"]
VALID_MODES: frozenset[str] = frozenset({"dry-run", "describe", "simulate"})

# A9-aligned secret keys (gcl_runner.redact_sensitive + EC2/IAM/KMS names).
_SECRET_KEYS = re.compile(
    r"(?:access.?key|secret|password|passwd|session.?token|keymaterial|"
    r"passworddata|userdata|plaintext|ciphertextblob|private.?key|"
    r"secretaccesskey|masteruserpassword)",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(\b(?:aws_secret_access_key|aws_session_token|sessiontoken|password|"
    r"passwd|token|keymaterial|passworddata|userdata|plaintext|"
    r"ciphertextblob|secretaccesskey)\s*[:=]\s*)"
    r"(['\"]?)([^\s,'\"}]+)",
    re.IGNORECASE,
)

# Ops known to support native AWS dry-run (allowlist; extend in later waves).
DRY_RUN_ALLOWLIST: frozenset[str] = frozenset({
    "ec2 terminate-instances",
    "ec2 stop-instances",
    "ec2 start-instances",
    "ec2 run-instances",
    "ec2 create-volume",
    "ec2 delete-volume",
    "ec2 create-snapshot",
    "ec2 delete-snapshot",
})


@runtime_checkable
class PlanLike(Protocol):
    """Duck-type for objects exposing ``plan_hash`` (e.g. ExecutionPlan)."""

    @property
    def plan_hash(self) -> str: ...


@dataclass
class ShadowResult:
    """Persisted shadow evidence (ok/error + redacted payload)."""

    plan_hash: str
    mode: ShadowMode
    ok: bool
    evidence: dict[str, Any] | str
    timestamp: str
    error: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Runner = Callable[[Mapping[str, Any], ShadowMode], dict[str, Any]]


def _resolve_plan_hash(
    plan: PlanLike | Mapping[str, Any] | None,
    plan_hash: str | None,
) -> str:
    if plan_hash:
        return str(plan_hash)
    if plan is None:
        raise ValueError("plan_hash required when plan is None")
    if isinstance(plan, Mapping):
        h = plan.get("plan_hash")
        if not h:
            raise ValueError("plan mapping missing plan_hash")
        return str(h)
    h = getattr(plan, "plan_hash", None)
    if not h:
        raise ValueError("plan missing plan_hash")
    return str(h)


def _plan_as_mapping(plan: PlanLike | Mapping[str, Any] | None) -> dict[str, Any]:
    if plan is None:
        return {}
    if isinstance(plan, Mapping):
        return dict(plan)
    out: dict[str, Any] = {}
    for key in (
        "plan_id", "skill", "operation", "resource_ids", "region", "risk",
        "preconditions", "expected_diff", "confirmation_op", "verify",
        "compensation", "plan_hash",
    ):
        if hasattr(plan, key):
            out[key] = getattr(plan, key)
    return out


def redact_evidence(payload: Any) -> Any:
    """Recursively mask A9-sensitive keys and credential assignments."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, item in payload.items():
            if _SECRET_KEYS.search(str(key)):
                out[key] = f"***<len={len(str(item))}>" if item is not None else "***"
            else:
                out[key] = redact_evidence(item)
        return out
    if isinstance(payload, list):
        return [redact_evidence(item) for item in payload]
    if isinstance(payload, str):
        return _SECRET_ASSIGNMENT.sub(r"\1\2***", payload)
    return payload


def _simulate_payload(plan_map: Mapping[str, Any]) -> dict[str, Any]:
    """Local simulate — expected_diff only; no AWS."""
    return {
        "strategy": "simulate",
        "operation": plan_map.get("operation") or "",
        "resource_ids": list(plan_map.get("resource_ids") or []),
        "region": plan_map.get("region") or "",
        "expected_diff": plan_map.get("expected_diff") or {},
        "note": "local simulate; no AWS call",
    }


def _default_aws_runner(plan_map: Mapping[str, Any], mode: ShadowMode) -> dict[str, Any]:
    raise RuntimeError(
        f"live AWS {mode} runner not configured; pass runner=... or use mode='simulate'"
    )


def find_shadow_evidence(
    plan_hash: str,
    *,
    audit_dir: Path | None = None,
) -> Path | None:
    """Return newest ok ShadowEvidence JSON whose plan_hash matches, or None."""
    if not plan_hash:
        return None
    base = Path(audit_dir) if audit_dir is not None else SHADOW_DIR
    if not base.is_dir():
        return None
    hash16 = plan_hash[:16]
    candidates = sorted(base.glob(f"shadow-*-{hash16}.json"), reverse=True)
    if not candidates:
        candidates = sorted(base.glob("shadow-*.json"), reverse=True)
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("plan_hash") == plan_hash and data.get("ok") is True:
            return path
    return None


def persist_shadow(
    result: ShadowResult,
    *,
    audit_dir: Path | None = None,
) -> Path:
    """Write ``shadow-<timestamp>-<plan_hash16>.json`` under audit-results/shadow/."""
    base = Path(audit_dir) if audit_dir is not None else SHADOW_DIR
    base.mkdir(parents=True, exist_ok=True)
    ts_compact = re.sub(r"[^0-9TZ]", "", result.timestamp)[:15] or "unknown"
    path = base / f"shadow-{ts_compact}-{result.plan_hash[:16]}.json"
    result.path = str(path)
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def run_shadow(
    plan: PlanLike | Mapping[str, Any] | None = None,
    mode: ShadowMode = "simulate",
    *,
    plan_hash: str | None = None,
    runner: Runner | None = None,
    audit_dir: Path | None = None,
    persist: bool = True,
) -> ShadowResult:
    """Run shadow strategy; optionally persist redacted evidence (no live AWS by default)."""
    if mode not in VALID_MODES:
        raise ValueError(f"invalid shadow mode {mode!r}; expected one of {sorted(VALID_MODES)}")

    resolved_hash = _resolve_plan_hash(plan, plan_hash)
    plan_map = _plan_as_mapping(plan)
    plan_map.setdefault("plan_hash", resolved_hash)

    timestamp = _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    error: str | None = None
    ok = False
    raw: dict[str, Any] | str = {}

    try:
        if mode == "simulate":
            raw = _simulate_payload(plan_map)
            ok = True
        else:
            exec_runner = runner if runner is not None else _default_aws_runner
            if mode == "dry-run":
                op = str(plan_map.get("operation") or "").strip().lower()
                if op.startswith("aws "):
                    op = op[4:]
                if op and op not in DRY_RUN_ALLOWLIST and runner is None:
                    raise RuntimeError(
                        f"operation {op!r} not in dry-run allowlist; "
                        "use mode='simulate' or mode='describe'"
                    )
            raw = exec_runner(plan_map, mode)
            if not isinstance(raw, (dict, str)):
                raw = {"payload": raw}
            ok = True
    except Exception as exc:  # noqa: BLE001 — surface as ShadowResult.error
        error = str(exc)
        ok = False
        raw = {"error": error}

    result = ShadowResult(
        plan_hash=resolved_hash,
        mode=mode,
        ok=ok,
        evidence=redact_evidence(raw),
        timestamp=timestamp,
        error=error,
    )
    if persist:
        persist_shadow(result, audit_dir=audit_dir)
    return result


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python3 scripts/shadow_exec.py --plan-hash H --mode simulate``."""
    import argparse

    parser = argparse.ArgumentParser(prog="shadow_exec")
    parser.add_argument("--plan-hash", required=True)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="simulate")
    parser.add_argument("--operation", default="")
    parser.add_argument("--region", default="")
    parser.add_argument("--resource-id", action="append", default=[])
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args(argv)

    result = run_shadow(
        {
            "plan_hash": args.plan_hash,
            "operation": args.operation,
            "region": args.region,
            "resource_ids": args.resource_id,
            "expected_diff": {},
        },
        mode=args.mode,  # type: ignore[arg-type]
        persist=not args.no_persist,
    )
    sys.stdout.write(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
