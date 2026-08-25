#!/usr/bin/env python3
"""
GCL Runner — Phase 2 reusable Orchestrator.

Implements the loop defined in `aws-skill-generator/references/gcl-spec.md`:

  §4 Loop Flow        Pre-flight → Generate → Critique → Decide
  §5 Termination      PASS / MAX_ITER / SAFETY_FAIL / BLOCKED / COMPENSATED
  §6 Trace schema     ./audit-results/gcl-trace-YYYYMMDD-HHMMSS-<run-id>.json
  §7.1 Placeholders   inject {{output.*}} from {{user.*}} before Critic
  §9 Anti-patterns    abort visibly on Safety=0; never silently downgrade
  §10 Phase 2         runtime-agnostic Orchestrator

Usage:

    # Dry-run on a single request (no AWS calls; prints the loop trace):
    python3 scripts/gcl_runner.py --skill aws-s3-ops --request "delete bucket X" \\
        --user-region us-east-1 --self-test

    # Live mode (real AWS calls; sub-agents must be configured separately):
    python3 scripts/gcl_runner.py --skill aws-s3-ops --request "..." \\
        --generator-cmd "agent run --skill aws-s3-ops" \\
        --critic-cmd    "agent run --role critic"

Design note: this script is *runtime-agnostic*. By default it runs in
`--self-test` mode that fakes Generator/Critic output from the rubric file,
so the loop control, trace persistence, and termination rules can be
exercised without an LLM agent attached. To wire to a real agent runtime,
supply `--generator-cmd` and `--critic-cmd` (they will be invoked with the
JSON-serialized iteration context on stdin).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

REPO = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO / "audit-results"
REFLEXION_PATTERNS_PATH = REPO / "docs" / "failure-patterns.md"

# Global state — lazily populated by _load_reflexion()
_REFLEXION = None
DEFAULT_COMMAND_TIMEOUT = 60.0
_RUBRIC_DIMENSIONS = (
    "correctness", "safety", "idempotency", "traceability", "spec_compliance",
)
VALID_OUTCOMES = frozenset({
    "PASS", "SAFETY_FAIL", "MAX_ITER", "BLOCKED", "COMPENSATED",
})

# ---------------------------------------------------------------------------
# Structured output schemas (L1 agentic maturity: contract validation)
# ---------------------------------------------------------------------------

# Re-export status constants for consumers
PASS = "PASS"
MAX_ITER = "MAX_ITER"
SAFETY_FAIL = "SAFETY_FAIL"


@dataclass
class GeneratorOutput:
    """Contract: what a Generator callable must return."""
    command: str
    args: dict
    exit_code: int
    result_excerpt: str
    safety_confirm_token: str = ""
    operation_risk: str = ""  # "" = unknown, "destructive" = destructive

    def __post_init__(self):
        if not isinstance(self.command, str):
            raise CommandContractError(f"Generator.command must be str, got {type(self.command).__name__}")
        if not isinstance(self.args, dict):
            raise CommandContractError(f"Generator.args must be dict, got {type(self.args).__name__}")
        if not isinstance(self.exit_code, int):
            raise CommandContractError(f"Generator.exit_code must be int, got {type(self.exit_code).__name__}")
        if not isinstance(self.result_excerpt, str):
            raise CommandContractError(f"Generator.result_excerpt must be str, got {type(self.result_excerpt).__name__}")


@dataclass
class CriticScores:
    """Contract: 5-dimension rubric scores."""
    correctness: float
    safety: float
    idempotency: float
    traceability: float
    spec_compliance: float

    def __post_init__(self):
        for dim, score in [("correctness", self.correctness), ("safety", self.safety),
                            ("idempotency", self.idempotency), ("traceability", self.traceability),
                            ("spec_compliance", self.spec_compliance)]:
            if score not in (0, 0.5, 1):
                raise CommandContractError(f"Critic score [{dim}] must be 0|0.5|1, got {score}")


@dataclass
class CriticOutput:
    """Contract: what a Critic callable must return."""
    scores: CriticScores
    suggestions: list[str] = field(default_factory=list)
    blocking: bool = False

    def __post_init__(self):
        if isinstance(self.scores, dict):
            self.scores = CriticScores(**self.scores)
        if not isinstance(self.scores, CriticScores):
            raise CommandContractError(f"Critic.scores must be CriticScores, got {type(self.scores).__name__}")
        if not isinstance(self.suggestions, list):
            raise CommandContractError(f"Critic.suggestions must be list, got {type(self.suggestions).__name__}")
        if len(self.suggestions) > 3:
            raise CommandContractError(f"Critic.suggestions max 3 items, got {len(self.suggestions)}")
        if not all(isinstance(s, str) for s in self.suggestions):
            raise CommandContractError("Critic.suggestions must contain only strings")
        if not isinstance(self.blocking, bool):
            raise CommandContractError(f"Critic.blocking must be bool, got {type(self.blocking).__name__}")


def validate_generator_output(result: dict) -> GeneratorOutput:
    """Validate Generator output contract. Only rejects type errors; missing optional fields use defaults.

    Required: command (str), args (dict), exit_code (int).
    Optional with defaults: result_excerpt (str), safety_confirm_token (str), operation_risk (str).
    Matches original _validate_generator contract exactly.
    """
    if not isinstance(result, dict):
        raise CommandContractError("Generator output must be an object")
    for fname, expected in [("command", str), ("args", dict), ("exit_code", int)]:
        val = result.get(fname)
        if not isinstance(val, expected):
            raise CommandContractError(f"Generator.{fname} must be {expected.__name__}, got {type(val).__name__ if val is not None else 'None'}")
    defaults = {"result_excerpt": "", "safety_confirm_token": "", "operation_risk": ""}
    merged = {**defaults, **{k: v for k, v in result.items()}}
    return GeneratorOutput(
        command=merged["command"],
        args=merged["args"],
        exit_code=merged["exit_code"],
        result_excerpt=merged["result_excerpt"],
        safety_confirm_token=merged["safety_confirm_token"],
        operation_risk=merged["operation_risk"],
    )


def validate_critic_output(result: dict) -> CriticOutput:
    """Validate Critic output contract. Only rejects type errors; missing optional fields use defaults.

    Required: scores (dict with 5 rubric dimensions, each 0|0.5|1).
    Optional with defaults: suggestions (list[str], max 3), blocking (bool).
    """
    if not isinstance(result, dict):
        raise CommandContractError("Critic output must be an object")
    scores_raw = result.get("scores", {})
    if not isinstance(scores_raw, dict):
        raise CommandContractError(f"Critic.scores must be dict, got {type(scores_raw).__name__}")
    for dim in ("correctness", "safety", "idempotency", "traceability", "spec_compliance"):
        score = scores_raw.get(dim)
        if score not in (0, 0.5, 1):
            raise CommandContractError(f"Critic.scores[{dim}] must be 0|0.5|1, got {score}")
    suggestions = result.get("suggestions", [])
    if not isinstance(suggestions, list):
        raise CommandContractError(f"Critic.suggestions must be list, got {type(suggestions).__name__}")
    if len(suggestions) > 3:
        raise CommandContractError(f"Critic.suggestions max 3 items, got {len(suggestions)}")
    for s in suggestions:
        if not isinstance(s, str):
            raise CommandContractError(f"Critic.suggestions must contain strings, got {type(s).__name__}")
    blocking = result.get("blocking", False)
    if not isinstance(blocking, bool):
        raise CommandContractError(f"Critic.blocking must be bool, got {type(blocking).__name__}")
    # Build validated struct
    scores = CriticScores(
        correctness=scores_raw.get("correctness", 1),
        safety=scores_raw.get("safety", 1),
        idempotency=scores_raw.get("idempotency", 1),
        traceability=scores_raw.get("traceability", 1),
        spec_compliance=scores_raw.get("spec_compliance", 1),
    )
    return CriticOutput(scores=scores, suggestions=list(suggestions), blocking=blocking)




def normalize_outcome(status: str) -> str:
    """Return a canonical trace outcome (ADR M1 unified enum).

    Mapping:
    - ``PASS`` / ``SAFETY_FAIL`` / ``MAX_ITER`` — GCL termination (§5).
    - ``BLOCKED`` — ``runtime_safety`` pre-tool BLOCK *before* GCL runs
      (no GCL Safety=0 semantics). Not emitted by ``--self-test`` stubs.
    - ``COMPENSATED`` — M3 compensation completed (schema-only until M3).

    ``--self-test`` destructive-without-confirm stays ``SAFETY_FAIL``.
    """
    normalized = status.upper().strip()
    if normalized not in VALID_OUTCOMES:
        raise ValueError(
            f"unknown outcome {status!r}; expected one of {sorted(VALID_OUTCOMES)}"
        )
    return normalized
_SECRET_KEYS = re.compile(
    r"(?:access.?key|secret|password|passwd|session.?token|keymaterial|"
    r"plaintext|ciphertextblob|private.?key)", re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(\b(?:aws_secret_access_key|aws_session_token|sessiontoken|password|"
    r"passwd|token|keymaterial|plaintext|ciphertextblob)\s*[:=]\s*)"
    r"(['\"]?)([^\s,'\"}]+)", re.IGNORECASE,
)


class CommandTimeout(RuntimeError):
    """An external Generator/Critic exceeded its execution budget."""


class CommandContractError(RuntimeError):
    """An external Generator/Critic returned an invalid JSON contract."""


def redact_sensitive(value: Any, blocked_text: str = "") -> Any:
    """Recursively redact secret-like keys and credential assignments."""
    if isinstance(value, dict):
        return {
            key: "***" if _SECRET_KEYS.search(str(key)) else redact_sensitive(item, blocked_text)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item, blocked_text) for item in value]
    if isinstance(value, str):
        if blocked_text and blocked_text in value:
            value = value.replace(blocked_text, "<redacted-request>")
        return _SECRET_ASSIGNMENT.sub(r"\1\2***", value)
    return value


def sanitize_request(request: str) -> str:
    """Persist only a stable identifier for the raw user request."""
    digest = hashlib.sha256(request.encode("utf-8")).hexdigest()
    return f"<request-sha256:{digest}>"


def _trace_safe_generator_result(result: Any, request: str) -> Any:
    safe = redact_sensitive(result, request)
    if isinstance(safe, dict):
        safe.pop("safety_confirm_token", None)
    return safe


def invoke_json_command(
    cmd: list[str], payload: dict[str, Any], timeout: float = DEFAULT_COMMAND_TIMEOUT,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Invoke an isolated JSON subprocess with timeout and object validation."""
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(json.dumps(payload), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        raise CommandTimeout(f"command exceeded {timeout}s: {cmd[0]}") from exc
    if proc.returncode != 0:
        raise RuntimeError(f"external command failed: {stderr.strip()[:500]}")
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CommandContractError("external command returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise CommandContractError("external command must return a JSON object")
    return result


def critic_environment() -> dict[str, str]:
    """Return a least-privilege environment without AWS credential sources."""
    allowed = {
        "PATH", "TMPDIR", "LANG", "LC_ALL", "HTTPS_PROXY", "NO_PROXY",
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
    }
    env = {
        key: value for key, value in os.environ.items()
        if key in allowed or key.startswith("LC_")
    }
    env.update({
        "HOME": "/nonexistent",
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
        "AWS_CONFIG_FILE": os.devnull,
    })
    return env


def _validate_generator(result: dict[str, Any]) -> dict[str, Any]:
    """Validate Generator contract. Returns validated dict for backward compat."""
    if not isinstance(result, dict):
        raise CommandContractError("Generator output must be an object")
    validate_generator_output(result)
    return result


def _validate_critic(result: dict[str, Any]) -> dict[str, Any]:
    """Validate Critic contract. Raises CommandContractError on violation."""
    if not isinstance(result, dict):
        raise CommandContractError("Critic output must be an object")
    validate_critic_output(result)
    return result


# ---------------------------------------------------------------------------
# Skill loading
# ---------------------------------------------------------------------------


def _load_yaml_frontmatter(path: Path) -> dict[str, Any]:
    txt = path.read_text()
    if not txt.startswith("---"):
        return {}
    parts = txt.split("---", 2)
    if len(parts) < 3:
        return {}
    # Per F-007 (2026-07-26): _yaml_lite fallback removed — it incorrectly
    # flattened nested dicts. PyYAML is a required dep; let exceptions
    # surface rather than silently returning garbage.
    import yaml  # PyYAML is a required dep
    return yaml.safe_load(parts[1]) or {}



@lru_cache(maxsize=32)
def load_skill(skill_name: str) -> dict[str, Any]:
    """Load SKILL.md + rubric.md + prompt-templates.md into one dict.
    Results cached by skill_name for the lifetime of the process."""
    skill_dir = REPO / skill_name
    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"skill not found: {skill_dir / 'SKILL.md'}")
    fm = _load_yaml_frontmatter(skill_dir / "SKILL.md")
    gcl = fm.get("metadata", {}).get("gcl", {}) if isinstance(fm, dict) else {}
    rubric_path = skill_dir / "references" / "rubric.md"
    prompts_path = skill_dir / "references" / "prompt-templates.md"
    skeleton_path = REPO / "aws-skill-generator" / "references" / "prompt-skeletons.md"
    return {
        "name": skill_name,
        "frontmatter": fm,
        "gcl": gcl,
        "max_iter": int(gcl.get("max_iter", 2)),
        "gcl_class": gcl.get("class", "required"),
        "rubric": rubric_path.read_text() if rubric_path.is_file() else "",
        "prompts": prompts_path.read_text() if prompts_path.is_file() else "",
        "skeleton": skeleton_path.read_text() if skeleton_path.is_file() else "",
    }


def render_critic_prompt(skill: dict[str, Any]) -> str:
    """Resolve the Critic prompt by inlining the shared skeleton with the
    skill-specific Hard rules block.

    Per the O3 migration (scripts/_sync_prompt_skeletons.py), each skill's
    `prompt-templates.md` is now a thin delta. The skeleton contains the
    canonical Generator/Critic/Orchestrator templates. We splice the
    skill's Hard rules into the Critic template's `{{skill.hard_rules}}`
    slot so the rendered prompt is complete and self-contained.
    """
    skeleton = skill.get("skeleton", "")
    prompts = skill.get("prompts", "")
    if not skeleton:
        return ""  # backward compat: caller falls back to skill["prompts"]
    # Extract Hard rules from the skill's delta file
    m = re.search(
        r"## Hard rules \(Critic template injection\)\s*.*?```text\n(.*?)\n```",
        prompts, re.DOTALL,
    )
    hard_rules = m.group(1).rstrip() if m else "(no service-specific hard rules)"
    # Extract the Critic template from the skeleton (between §2 and §3)
    crit = re.search(
        r"## 2\. Critic Prompt \(C\)\s*```text\n(.*?)\n```", skeleton, re.DOTALL
    )
    if not crit:
        return prompts  # old-style skill, return raw
    rendered = crit.group(1)
    rendered = rendered.replace("{{skill.name}}", skill["name"])
    rendered = rendered.replace("{{skill.hard_rules}}", hard_rules)
    return rendered


# ---------------------------------------------------------------------------
# Orchestrator core (§4)
# ---------------------------------------------------------------------------


def _trace_path() -> Path:
    AUDIT_DIR.mkdir(exist_ok=True)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    return AUDIT_DIR / f"gcl-trace-{ts}-{uuid.uuid4().hex[:8]}.json"


def _prune_old_traces(retention_days: int = 30) -> None:
    """§10 Phase 2 retention: prune traces older than `retention_days`."""
    if not AUDIT_DIR.is_dir():
        return
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=retention_days)
    for p in AUDIT_DIR.glob("gcl-trace-*.json"):
        try:
            mt = _dt.datetime.fromtimestamp(p.stat().st_mtime, _dt.timezone.utc)
            if mt < cutoff:
                p.unlink()
        except OSError:
            pass


def _invoke_generator(ctx: dict[str, Any], cmd: list[str] | None) -> dict[str, Any]:
    """Call the Generator (sub-agent) or return self-test stub."""
    if cmd is None:
        # Self-test stub: produces a synthetic generator_output that surfaces
        # the user-supplied safety_confirm once it's present in the trace.
        request = (ctx.get("user", {}).get("request") or "").lower()
        # Align with runtime_safety.DESTRUCTIVE_VERBS (incl. deregister/purge/reject).
        destructive_kw = (
            "delete", "terminate", "detach", "revoke", "disable", "drop",
            "deregister", "purge", "reject", "destroy",
        )
        return {
            "command": "aws --self-test",
            "args": {},
            "exit_code": 0,
            "operation_risk": "destructive" if any(k in request for k in destructive_kw) else "read-only",
            "result_excerpt": json.dumps(
                {"stub": "self-test", "iter": ctx["iter"]}
            ),
            "safety_confirm_token": ctx.get("user", {}).get("safety_confirm", ""),
        }
    return invoke_json_command(cmd, ctx)


def _invoke_critic(
    ctx: dict[str, Any], cmd: list[str] | None, rubric: str
) -> dict[str, Any]:
    """Call the Critic (sub-agent, isolated context) or return self-test stub."""
    if cmd is None:
        # Self-test stub: Critic scores Safety=0 unless the request is for a
        # destructive operation AND a confirmation token was produced. Read-only
        # requests (no destructive keyword in request) pass Safety=1 by default
        # to verify the read path works end-to-end.
        # When `flaky_critic=True` is passed in ctx (via --flaky-critic CLI flag),
        # idempotency is scored 0 to exercise the MAX_ITER termination path.
        gen_out = ctx.get("generator_output", {})
        is_destructive = gen_out.get("operation_risk") == "destructive"
        has_confirm = bool(gen_out.get("safety_confirm_token"))
        safety = 1 if not is_destructive or has_confirm else 0
        idempotency = 0.0 if ctx.get("_flaky_critic") else 1.0
        scores = {
            "correctness": 1.0,
            "safety": float(safety),
            "idempotency": float(idempotency),
            "traceability": 1.0,
            "spec_compliance": 1.0,
        }
        return {
            "scores": scores,
            "suggestions": [],
            "blocking": safety == 0,
        }
    return invoke_json_command(cmd, ctx, env=critic_environment())


def _load_reflexion():
    """Lazily load _reflexion.py from the scripts/ directory via exec().

    Mirrors runtime_safety._load_reflexion(): direct execution so no
    __init__.py is required; None when absent or unimportable.
    """
    global _REFLEXION
    if _REFLEXION is not None:
        return _REFLEXION
    rx_path = Path(__file__).parent / "_reflexion.py"
    if not rx_path.exists():
        return None
    try:
        import sys as _sys
        import types as _types

        ns: dict[str, object] = {"__name__": "_reflexion"}
        ns.update(globals())
        ns["__name__"] = "_reflexion"
        rx_code = rx_path.read_text(encoding="utf-8")
        _rx_module = _types.ModuleType("_reflexion")
        _sys.modules["_reflexion"] = _rx_module
        exec(rx_code, ns)
        # Expose the executed namespace on the registered module so later
        # `from _reflexion import X` in the same process resolves attributes
        # instead of hitting an empty module shell.
        _rx_module.__dict__.update(ns)
        _REFLEXION = _types.SimpleNamespace(
            FailurePattern=ns.get("FailurePattern"),
            derive_from_error=ns.get("derive_from_error"),
            append_or_increment=ns.get("append_or_increment"),
        )
    except Exception:  # pragma: no cover
        return None
    return _REFLEXION


def _reflect_error(
    skill_name: str, command: str, exc: Exception, request: str,
) -> None:
    """L4 #3 全覆盖: persist non-GCL execution failures into failure-patterns.md.

    Never masks the original error — every reflexion failure is swallowed.
    """
    try:
        rx = _load_reflexion()
        if rx is None:
            return
        pattern = rx.derive_from_error(
            skill=skill_name,
            command=command,
            error=redact_sensitive(str(exc), request),
            source="gcl-runner",
        )
        rx.append_or_increment(REFLEXION_PATTERNS_PATH, pattern)
    except Exception:  # pragma: no cover — reflexion must never mask original
        pass


def _run_loop(
    skill_name: str,
    request: str,
    user_region: str,
    generator,
    critic,
    safety_confirm: str = "",
    flaky_critic: bool = False,
    plan_hash: str = "",
    shadow_path: str = "",
) -> dict[str, Any]:
    skill = load_skill(skill_name)
    trace: dict[str, Any] = {
        "skill": skill_name,
        "request": sanitize_request(request),
        "rubric_version": "v1",
        "iterations": [],
        "final": {"status": "MAX_ITER", "iter": 0, "output": None},
        # ADR-0001 M2: optional pre-GCL evidence pointers (empty when unused).
        "plan_hash": plan_hash or None,
        "shadow": {"path": shadow_path} if shadow_path else None,
    }
    best = None
    feedback: list[str] = []
    for it in range(1, skill["max_iter"] + 1):
        output_ns = {
            "requested_region": user_region or os.environ.get("AWS_DEFAULT_REGION", ""),
            "safety_confirm_token": safety_confirm,
            "critic_feedback": feedback,
        }
        gen_ctx = {
            "iter": it,
            "user": {"request": request, "region": user_region,
                     "safety_confirm": safety_confirm},
            "output": output_ns,
            "rubric": skill["rubric"],
            "_flaky_critic": flaky_critic,
            "_critic_prompt_rendered": render_critic_prompt(skill),
        }
        try:
            gen_result = _validate_generator(generator(gen_ctx))
            crit_ctx = {
                "iter": it,
                "output": {
                    "requested_region": output_ns["requested_region"],
                    "safety_confirm_token": str(
                        gen_result.get("safety_confirm_token") or ""
                    ),
                    "critic_feedback": feedback,
                },
                "rubric": skill["rubric"],
                "generator_output": redact_sensitive(gen_result, request),
                "trace": redact_sensitive(gen_result, request),
            }
            crit_result = _validate_critic(critic(crit_ctx))
        except (CommandTimeout, CommandContractError, RuntimeError) as exc:
            _reflect_error(skill_name, "gcl-loop", exc, request)
            trace["final"] = {
                "status": "SAFETY_FAIL", "iter": it, "output": None,
                "reason": redact_sensitive(f"trust boundary failure: {exc}", request),
            }
            break
        decision = _decide(
            crit_result["scores"], it, skill["max_iter"], crit_result.get("blocking", False)
        )
        feedback = crit_result.get("suggestions", [])[:3]
        trace["iterations"].append({
            "iter": it,
            "generator": redact_sensitive({
                "command": gen_result.get("command", ""),
                "args": gen_result.get("args", {}),
                "exit_code": gen_result.get("exit_code", 0),
                "result_excerpt": (gen_result.get("result_excerpt") or "")[:2048],
            }, request),
            "critic": redact_sensitive({
                "scores": crit_result["scores"],
                "suggestions": feedback,
                "blocking": crit_result.get("blocking", False),
            }),
            "decision": decision,
        })
        if decision == "ABORT":
            trace["final"] = {"status": "SAFETY_FAIL", "iter": it,
                              "output": None, "reason": "Safety=0 or blocking"}
            break
        if decision == "RETURN":
            trace["final"] = {"status": "PASS", "iter": it,
                              "output": _trace_safe_generator_result(gen_result, request)}
            best = gen_result
            break
        if decision == "RETURN_BEST":
            trace["final"] = {
                "status": "MAX_ITER", "iter": it,
                "output": _trace_safe_generator_result(best, request),
                "reason": "max_iter reached; some dimensions below threshold",
            }
            break
        best = gen_result
    return trace


def run_with_callables(
    skill_name: str,
    request: str,
    user_region: str,
    generator,
    critic,
    safety_confirm: str = "",
) -> dict[str, Any]:
    """Run GCL with injected callables for deterministic contract tests."""
    return _run_loop(
        skill_name, request, user_region, generator, critic, safety_confirm=safety_confirm
    )


def _decide(
    scores: dict[str, float], iter_: int, max_iter: int, blocking: bool
) -> str:
    """§5 Termination: first match wins (Safety=0 ABORT, all-pass RETURN, etc)."""
    if scores.get("safety", 1) == 0 or blocking:
        return "ABORT"
    dims_pass = all(scores.get(d, 0) >= 0.5 for d in (
        "correctness", "safety", "idempotency", "traceability", "spec_compliance"
    ))
    if dims_pass:
        return "RETURN"
    if iter_ < max_iter:
        return "RETRY"
    return "RETURN_BEST"


def run(
    skill_name: str,
    request: str,
    user_region: str,
    generator_cmd: list[str] | None = None,
    critic_cmd: list[str] | None = None,
    safety_confirm: str = "",
    flaky_critic: bool = False,
    plan_hash: str = "",
    shadow_path: str = "",
) -> dict[str, Any]:
    """Top-level Orchestrator entry point. Returns the trace object (§6)."""
    def gen(ctx: dict[str, Any]) -> dict[str, Any]:
        return _invoke_generator(ctx, generator_cmd)

    def crit(ctx: dict[str, Any]) -> dict[str, Any]:
        return _invoke_critic(ctx, critic_cmd, ctx.get("rubric", ""))

    return _run_loop(
        skill_name, request, user_region, gen, crit,
        safety_confirm=safety_confirm, flaky_critic=flaky_critic,
        plan_hash=plan_hash, shadow_path=shadow_path,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GCL Orchestrator (Phase 2)")
    ap.add_argument("--skill", required=True, help="e.g. aws-s3-ops")
    ap.add_argument("--request", required=False, default="(inspect-only)")
    ap.add_argument("--user-region", default=os.environ.get("AWS_DEFAULT_REGION", ""))
    ap.add_argument("--safety-confirm", default="")
    ap.add_argument("--plan-hash", default="", help="ADR-0001 M2: record plan_hash on trace")
    ap.add_argument("--shadow-path", default="", help="ADR-0001 M2: record shadow evidence path on trace")
    ap.add_argument("--generator-cmd", default=None,
                    help="Optional external command for the Generator agent")
    ap.add_argument("--critic-cmd", default=None,
                    help="Optional external command for the Critic agent")
    ap.add_argument("--self-test", action="store_true",
                    help="Run with synthetic G/C stubs (no external agent)")
    ap.add_argument("--flaky-critic", action="store_true",
                    help="(self-test) Force idempotency=0 to exercise MAX_ITER path")
    ap.add_argument("--print-critic", action="store_true",
                    help="Print the rendered Critic prompt (after skeleton merge) and exit")
    ap.add_argument("--on-fail", action="store_true", default=False,
                    help="Append failure pattern to docs/failure-patterns.md on SAFETY_FAIL/MAX_ITER")
    ap.add_argument("--failure-patterns", default=str(REPO / "docs" / "failure-patterns.md"),
                    help="Path to failure-patterns.md (default: docs/failure-patterns.md)")
    ap.add_argument("--no-prune", action="store_true",
                    help="Skip 30-day trace retention prune")
    args = ap.parse_args(argv)

    if args.print_critic:
        skill = load_skill(args.skill)
        rendered = render_critic_prompt(skill)
        if not rendered:
            print("(no skeleton available; legacy skill)", file=sys.stderr)
        print(rendered)
        return 0

    if not args.self_test and (args.generator_cmd is None or args.critic_cmd is None):
        ap.error("Provide --generator-cmd and --critic-cmd, or use --self-test")

    gen_cmd = args.generator_cmd.split() if args.generator_cmd else None
    crit_cmd = args.critic_cmd.split() if args.critic_cmd else None

    trace = run(
        skill_name=args.skill,
        request=args.request,
        user_region=args.user_region,
        generator_cmd=gen_cmd,
        critic_cmd=crit_cmd,
        safety_confirm=args.safety_confirm,
        flaky_critic=args.flaky_critic,
        plan_hash=args.plan_hash,
        shadow_path=args.shadow_path,
    )

    out_path = _trace_path()
    out_path.write_text(json.dumps(trace, indent=2))
    if not args.no_prune:
        _prune_old_traces()

    # Reflexion hook (L4 dim #3): auto-append failure pattern on FAIL
    if args.on_fail and trace["final"]["status"] in ("SAFETY_FAIL", "MAX_ITER"):
        try:
            from _reflexion import derive_from_trace, append_or_increment
        except Exception as e:
            print(f"reflexion: skipped ({e})", file=sys.stderr)
        else:
            for pat in derive_from_trace(trace):
                result = append_or_increment(Path(args.failure_patterns), pat)
                print(f"reflexion: {result} {pat.skill} | {pat.error}")

    # Governed Learning auto-promote hook (ADR-0001 M4)
    if args.on_fail and trace["final"]["status"] in ("SAFETY_FAIL", "MAX_ITER"):
        try:
            from governed_learning import (
                harvest_from_trace as _gl_harvest,
                evaluate_candidate as _gl_eval,
                auto_promote as _gl_promote,
            )
        except Exception as e:
            print(f"governed-learning: skipped ({e})", file=sys.stderr)
        else:
            fp = Path(args.failure_patterns)
            _gl_cands = _gl_harvest(trace, source=str(out_path))
            if _gl_cands:
                _gl_cands = [_gl_eval(c, patterns_path=fp) for c in _gl_cands]
                _gl_promoted = _gl_promote(_gl_cands, patterns_path=fp)
                if _gl_promoted:
                    for c in _gl_promoted:
                        print(f"governed-learning: auto-promoted {c.id} | {c.signature}")
                else:
                    print(f"governed-learning: {len(_gl_cands)} candidate(s) evaluated, 0 promoted")

    print(f"status: {trace['final']['status']}  iter: {trace['final']['iter']}")
    print(f"trace:  {out_path.relative_to(REPO)}")
    return 0 if trace["final"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
