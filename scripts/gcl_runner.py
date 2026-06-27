#!/usr/bin/env python3
"""
GCL Runner — Phase 2 reusable Orchestrator.

Implements the loop defined in `aws-skill-generator/references/gcl-spec.md`:

  §4 Loop Flow        Pre-flight → Generate → Critique → Decide
  §5 Termination      PASS / MAX_ITER / SAFETY_FAIL
  §6 Trace schema     ./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
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
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
AUDIT_DIR = REPO / "audit-results"


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
    try:
        import yaml  # PyYAML is already a dep of the other helpers
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        # Fallback: tiny parser for the `metadata.gcl.*` keys we need
        return _yaml_lite(parts[1])


def _yaml_lite(block: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    cur: dict[str, Any] | None = None
    indent = 0
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        spaces = len(line) - len(line.lstrip(" "))
        if spaces == 0 and ":" in line:
            k, _, v = line.partition(":")
            v = v.strip().strip('"').strip("'")
            if v == "":
                cur = {}
                out[k.strip()] = cur
                indent = spaces
            else:
                cur = None
                out[k.strip()] = _coerce(v)
        elif cur is not None and spaces > indent and ":" in line:
            k, _, v = line.strip().partition(":")
            v = v.strip().strip('"').strip("'")
            cur[k.strip()] = _coerce(v)
    return out


def _coerce(v: str) -> Any:
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        return v


def load_skill(skill_name: str) -> dict[str, Any]:
    """Load SKILL.md + rubric.md + prompt-templates.md into one dict."""
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
    return AUDIT_DIR / f"gcl-trace-{ts}.json"


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
        return {
            "command": "aws --self-test",
            "args": {},
            "exit_code": 0,
            "result_excerpt": json.dumps(
                {"stub": "self-test", "iter": ctx["iter"]}
            ),
            "safety_confirm_token": ctx.get("user", {}).get("safety_confirm", ""),
        }
    proc = subprocess.run(cmd, input=json.dumps(ctx), text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"generator cmd failed: {proc.stderr}")
    return json.loads(proc.stdout)


def _invoke_critic(
    ctx: dict[str, Any], cmd: list[str] | None, rubric: str
) -> dict[str, Any]:
    """Call the Critic (sub-agent, isolated context) or return self-test stub."""
    if cmd is None:
        # Self-test stub: Critic scores Safety=0 unless the request is for a
        # destructive operation AND a confirmation token was produced. Read-only
        # requests (no `delete`/`terminate`/`detach`/`revoke`/`disable` keyword)
        # pass Safety=1 by default to verify the read path works end-to-end.
        # When `flaky_critic=True` is passed in ctx (via --flaky-critic CLI flag),
        # idempotency is scored 0 to exercise the MAX_ITER termination path.
        gen_out = ctx.get("generator_output", {})
        req = (ctx.get("user", {}).get("request") or "").lower()
        destructive_kw = ("delete", "terminate", "detach", "revoke",
                          "disable-guardduty", "disable", "drop")
        is_destructive = any(k in req for k in destructive_kw)
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
    proc = subprocess.run(cmd, input=json.dumps(ctx), text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"critic cmd failed: {proc.stderr}")
    return json.loads(proc.stdout)


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
) -> dict[str, Any]:
    """Top-level Orchestrator entry point. Returns the trace object (§6)."""
    skill = load_skill(skill_name)
    trace: dict[str, Any] = {
        "skill": skill_name,
        "request": request,
        "rubric_version": "v1",
        "iterations": [],
        "final": {"status": "MAX_ITER", "iter": 0, "output": None},
    }

    best = None
    for it in range(1, skill["max_iter"] + 1):
        # §7.1 user→output placeholder mapping, populated by Orchestrator
        output_ns = {
            "requested_region": user_region or os.environ.get("AWS_DEFAULT_REGION", ""),
            "safety_confirm_token": safety_confirm,
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
        gen_result = _invoke_generator(gen_ctx, generator_cmd)
        crit_ctx = {
            **gen_ctx,
            "generator_output": gen_result,
            "trace": gen_result,
        }
        crit_result = _invoke_critic(crit_ctx, critic_cmd, skill["rubric"])
        decision = _decide(
            crit_result["scores"], it, skill["max_iter"], crit_result.get("blocking", False)
        )
        trace["iterations"].append({
            "iter": it,
            "generator": {
                "command": gen_result.get("command", ""),
                "args": gen_result.get("args", {}),
                "exit_code": gen_result.get("exit_code", 0),
                "result_excerpt": (gen_result.get("result_excerpt") or "")[:2048],
            },
            "critic": {
                "scores": crit_result["scores"],
                "suggestions": crit_result.get("suggestions", []),
                "blocking": crit_result.get("blocking", False),
            },
            "decision": decision,
        })
        # §5 termination rules
        if decision == "ABORT":
            trace["final"] = {"status": "SAFETY_FAIL", "iter": it,
                              "output": None, "reason": "Safety=0 or blocking"}
            break
        if decision == "RETURN":
            trace["final"] = {"status": "PASS", "iter": it, "output": gen_result}
            best = gen_result
            break
        if decision == "RETURN_BEST":
            trace["final"] = {
                "status": "MAX_ITER",
                "iter": it,
                "output": best,
                "reason": "max_iter reached; some dimensions below threshold",
            }
            break
        best = gen_result

    return trace


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GCL Orchestrator (Phase 2)")
    ap.add_argument("--skill", required=True, help="e.g. aws-s3-ops")
    ap.add_argument("--request", required=False, default="(inspect-only)")
    ap.add_argument("--user-region", default=os.environ.get("AWS_DEFAULT_REGION", ""))
    ap.add_argument("--safety-confirm", default="")
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
    )

    out_path = _trace_path()
    out_path.write_text(json.dumps(trace, indent=2))
    if not args.no_prune:
        _prune_old_traces()

    print(f"status: {trace['final']['status']}  iter: {trace['final']['iter']}")
    print(f"trace:  {out_path.relative_to(REPO)}")
    return 0 if trace["final"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
