#!/usr/bin/env python3
"""
Apply the AIOps Delegate Adapter Patch to a list of aws-*-ops SKILL.md files.

For each skill:
  1. Add orchestrator_aware / orchestrator_compat / delegate keys to the
     YAML frontmatter metadata block.
  2. Insert (or replace) a '## AIOps Delegate Contract' section near the
     end of the file.

Both edits are idempotent: re-running on an already-patched skill is a
no-op (presence check on the section title).
"""

import sys
from pathlib import Path
import re


# Per-skill delegate block. Keyed by skill directory name.
DELEGATE_CONFIG = {
    "aws-elb-ops": {
        "accepts": ["health-check", "rca", "self-heal", "change-impact"],
        "produces_facts": ["metric", "log", "event", "state"],
    },
    "aws-cloudwatch-ops": {
        "accepts": ["health-check", "rca", "capacity-forecast"],
        "produces_facts": ["metric", "log"],
    },
    "aws-ec2-ops": {
        "accepts": ["health-check", "rca", "self-heal", "change-impact"],
        "produces_facts": ["metric", "state", "event"],
    },
    "aws-rds-ops": {
        "accepts": ["health-check", "rca", "self-heal", "change-impact"],
        "produces_facts": ["metric", "state", "event"],
    },
    "aws-vpc-ops": {
        "accepts": ["health-check", "rca", "change-impact"],
        "produces_facts": ["metric", "log", "config"],
    },
    "aws-acm-ops": {
        "accepts": ["health-check", "self-heal"],
        "produces_facts": ["state", "event"],
    },
    "aws-route53-ops": {
        "accepts": ["health-check", "self-heal", "change-impact"],
        "produces_facts": ["state"],
    },
    "aws-waf-ops": {
        "accepts": ["health-check", "rca", "self-heal"],
        "produces_facts": ["metric", "log", "config"],
    },
    "aws-autoscaling-ops": {
        "accepts": ["self-heal", "capacity-forecast"],
        "produces_facts": ["state", "metric"],
    },
    "aws-kms-ops": {
        "accepts": ["compliance-scan", "change-impact"],
        "produces_facts": ["state", "event"],
    },
    "aws-iam-ops": {
        "accepts": ["compliance-scan", "change-impact"],
        "produces_facts": ["state", "event"],
    },
    "aws-guardduty-ops": {
        "accepts": ["health-check", "compliance-scan"],
        "produces_facts": ["finding"],
    },
    "aws-securityhub-ops": {
        "accepts": ["health-check", "compliance-scan"],
        "produces_facts": ["finding"],
    },
    "aws-cloudtrail-ops": {
        "accepts": ["rca", "change-impact", "forensic"],
        "produces_facts": ["event"],
    },
    "aws-s3-ops": {
        "accepts": ["compliance-scan", "change-impact", "cost-forecast"],
        "produces_facts": ["config", "state", "cost"],
    },
    "aws-config-ops": {
        "accepts": ["compliance-scan", "change-impact"],
        "produces_facts": ["config"],
    },
    "aws-athena-ops": {
        "accepts": ["health-check", "cost-forecast"],
        "produces_facts": ["metric", "cost", "state"],
    },
    "aws-cloudfront-ops": {
        "accepts": ["health-check", "self-heal", "change-impact"],
        "produces_facts": ["metric", "config", "state"],
    },
    "aws-ecr-ops": {
        "accepts": ["health-check", "self-heal", "change-impact"],
        "produces_facts": ["state", "config"],
    },
    "aws-efs-ops": {
        "accepts": ["health-check", "self-heal", "change-impact"],
        "produces_facts": ["state", "metric"],
    },
    "aws-eks-ops": {
        "accepts": ["health-check", "rca", "self-heal", "change-impact"],
        "produces_facts": ["metric", "state", "event"],
    },
    "aws-elasticache-ops": {
        "accepts": ["health-check", "rca", "self-heal", "change-impact", "capacity-forecast"],
        "produces_facts": ["metric", "state"],
    },
    "aws-eventbridge-ops": {
        "accepts": ["health-check", "rca", "change-impact"],
        "produces_facts": ["event", "config"],
    },
    "aws-lambda-ops": {
        "accepts": ["health-check", "rca", "self-heal", "capacity-forecast"],
        "produces_facts": ["metric", "state"],
    },
    "aws-opensearch-ops": {
        "accepts": ["health-check", "rca", "self-heal", "change-impact"],
        "produces_facts": ["metric", "state", "finding"],
    },
    "aws-ram-ops": {
        "accepts": ["compliance-scan", "change-impact"],
        "produces_facts": ["config", "state"],
    },
    "aws-secretsmanager-ops": {
        "accepts": ["compliance-scan", "change-impact", "self-heal"],
        "produces_facts": ["state", "config"],
    },
    "aws-sns-ops": {
        "accepts": ["health-check", "rca"],
        "produces_facts": ["metric", "event"],
    },
    "aws-sqs-ops": {
        "accepts": ["health-check", "rca"],
        "produces_facts": ["metric", "event", "state"],
    },
    "aws-ssm-ops": {
        "accepts": ["health-check", "self-heal", "compliance-scan", "change-impact"],
        "produces_facts": ["state", "event", "config"],
    },
    "aws-stepfunctions-ops": {
        "accepts": ["health-check", "rca", "change-impact"],
        "produces_facts": ["state", "event"],
    },
}

SECTION_TEMPLATE = """## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.
"""


def patch_skill(skill_dir: Path, repo_root: Path) -> bool:
    """Patch a single skill's SKILL.md. Returns True if any change."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"  SKIP {skill_dir.name}: SKILL.md not found", file=sys.stderr)
        return False

    skill_name = skill_dir.name
    if skill_name not in DELEGATE_CONFIG:
        print(f"  SKIP {skill_name}: not in DELEGATE_CONFIG", file=sys.stderr)
        return False

    cfg = DELEGATE_CONFIG[skill_name]
    text = skill_md.read_text(encoding="utf-8")
    original = text

    # --- 1. Frontmatter edit ---
    # Match the metadata: block; insert delegate keys at the end of it
    # (before the closing of metadata: ... either by dedent or by next
    # top-level key).
    delegate_yaml = (
        f"  orchestrator_aware: true\n"
        f"  orchestrator_compat: \">=0.1.0\"\n"
        f"  delegate:\n"
        f"    accepts: [{', '.join(repr(a) for a in cfg['accepts'])}]\n"
        f"    produces_facts: [{', '.join(repr(f) for f in cfg['produces_facts'])}]\n"
        f"    idempotency_ttl: \"PT24H\"\n"
        f"    destructive_ops_require_confirm: true\n"
    )

    # Idempotency check
    if "orchestrator_aware: true" in text:
        print(f"  SKIP {skill_name}: already patched (orchestrator_aware present)")
        return False

    # Insert delegate block right before the closing `---` of frontmatter.
    # Frontmatter is the first `---` ... `---` block at top of file.
    fm_pattern = re.compile(
        r"^---\n(.*?)\n---\n",
        re.DOTALL | re.MULTILINE,
    )
    m = fm_pattern.search(text)
    if not m:
        print(f"  ERROR {skill_name}: no frontmatter found", file=sys.stderr)
        return False

    fm_body = m.group(1)
    if "metadata:" not in fm_body:
        print(f"  ERROR {skill_name}: no metadata: key in frontmatter", file=sys.stderr)
        return False

    # Append delegate YAML at end of frontmatter block
    new_fm_body = fm_body.rstrip() + "\n" + delegate_yaml
    text = text[: m.start()] + "---\n" + new_fm_body + "\n---\n" + text[m.end():]

    # --- 2. Section insert ---
    if "## AIOps Delegate Contract" in text:
        print(f"  WARN {skill_name}: section header already present; not duplicating")
    else:
        # Insert before "## Reference Index" if present, else append at end.
        ref_idx = text.find("\n## Reference Index")
        if ref_idx != -1:
            insert_at = ref_idx
        else:
            # Append at end with two newlines for separation
            text = text.rstrip() + "\n\n"
            insert_at = len(text)
        text = text[:insert_at] + SECTION_TEMPLATE + "\n" + text[insert_at:]

    # Write back
    if text != original:
        skill_md.write_text(text, encoding="utf-8")
        print(f"  PATCHED {skill_name}")
        return True
    return False


def main():
    repo_root = Path(__file__).resolve().parents[1]
    skills = list(DELEGATE_CONFIG.keys())
    print(f"Patching {len(skills)} skills...")
    patched = 0
    for skill_name in skills:
        skill_dir = repo_root / skill_name
        if patch_skill(skill_dir, repo_root):
            patched += 1
    print(f"\nDone. {patched}/{len(skills)} patched.")


if __name__ == "__main__":
    main()