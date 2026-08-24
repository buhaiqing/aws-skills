#!/usr/bin/env python3
"""
Helper: generate a rubric.md for an AWS skill from a structured spec.

Usage:
    python3 _gen_rubric.py <skill-dir> <service-name>

Reads SKILL.md to confirm the service, then writes a rubric.md with the
canonical 5-dimension structure. The rubric is then hand-edited to add
service-specific Safety special cases.

This is intentionally minimal — the value is in the **safety special
cases** for each service, not in the boilerplate.
"""
import sys
from pathlib import Path

TEMPLATE = '''# {service} Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `{skill}`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for destructive ops | 0 / 0.5 / 1 | Verifies the resource id / arn / name matches the user request. Read back via the matching `describe-*` / `get-*` / `list-*` call and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Service-specific: see per-op overrides below. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws {aws_cli_svc} <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-*` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: region supports the resource, IAM pre-reqs satisfied, quota within limits. |

## Operation-specific overrides

<!-- LLM_FILL_OPS -->

<!-- LLM_FILL_OPS is replaced with the ops table content from LLM.
     The LLM output must include the second section heading to enable splitting. -->

## Safety special cases (auto-fail)

<!-- LLM_FILL_SAFETY -->

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **{max_iter}** | `gcl-spec.md` §10 (Phase 1 default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `{skill}` GCL rollout (Phase 1) |
'''


def _aws_cli_svc(skill_dir: str) -> str:
    overrides = {
        'aws-ec2-ops': 'ec2',
        'aws-iam-ops': 'iam',
        'aws-kms-ops': 'kms',
        'aws-s3-ops': 's3',
        'aws-rds-ops': 'rds',
        'aws-dynamodb-ops': 'dynamodb',
        'aws-lambda-ops': 'lambda',
        'aws-elasticache-ops': 'elasticache',
        'aws-route53-ops': 'route53',
        'aws-sqs-ops': 'sqs',
        'aws-sns-ops': 'sns',
        'aws-cloudfront-ops': 'cloudfront',
        'aws-waf-ops': 'wafv2',
        'aws-secretsmanager-ops': 'secretsmanager',
        'aws-ssm-ops': 'ssm',
        'aws-stepfunctions-ops': 'stepfunctions',
        'aws-vpc-ops': 'ec2',
        'aws-acm-ops': 'acm',
        'aws-eks-ops': 'eks',
        'aws-elb-ops': 'elbv2',
        'aws-cloudwatch-ops': 'cloudwatch',
        'aws-cloudtrail-ops': 'cloudtrail',
    }
    base = skill_dir.replace('aws-', '').replace('-ops', '')
    return overrides.get(skill_dir, base)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate rubric.md for an AWS skill")
    ap.add_argument("skill_dir", help="Skill directory, e.g. aws-lambda-ops")
    ap.add_argument("service", help="Human-readable service name, e.g. AWS Lambda")
    ap.add_argument("--docs-url", default="", help="Official AWS docs URL")
    ap.add_argument("--llm-fill", action="store_true",
                    help="Call DashScope LLM to fill Operation-specific overrides + Safety special cases")
    ap.add_argument("--recommended", action="store_true",
                    help="Use max_iterations=3 instead of 2")
    args = ap.parse_args()

    skill_dir = args.skill_dir
    service = args.service
    docs_url = args.docs_url
    aws_cli_svc = _aws_cli_svc(skill_dir)
    max_iter = 3 if args.recommended else 2
    out = Path(skill_dir) / 'references' / 'rubric.md'
    out.parent.mkdir(parents=True, exist_ok=True)

    rubric = TEMPLATE.format(
        skill=skill_dir,
        service=service,
        aws_cli_svc=aws_cli_svc,
        max_iter=max_iter,
    )

    if args.llm_fill:
        try:
            from _llm_rubric_fill import fill_rubric as _llm_fill
            extra = _llm_fill(skill_dir, service, docs_url, aws_cli_svc)
            if extra:
                # LLM returns "## Operation-specific overrides\n...\n## Safety special cases (auto-fail)\n..."
                # Split at the second heading and replace each marker
                safety_idx = extra.find("## Safety special cases (auto-fail)")
                if safety_idx > 0:
                    ops_content = extra[:safety_idx].rstrip()
                    safety_content = extra[safety_idx:].rstrip()
                    # Template declares both section headings. Strip LLM's heading
                    # lines so only the template's pre-declared headings remain.
                    if ops_content.startswith("## "):
                        ops_content = ops_content.split("\n\n", 1)[-1].strip()
                    if safety_content.startswith("## "):
                        safety_content = safety_content.split("\n\n", 1)[-1].strip()
                    rubric = rubric.replace("<!-- LLM_FILL_OPS -->", ops_content)
                    rubric = rubric.replace("<!-- LLM_FILL_SAFETY -->", safety_content)
                    total = len(ops_content) + len(safety_content)
                    print(f"LLM filled rubric sections ({total} chars)", file=sys.stderr)
                else:
                    # Fallback: whole thing in ops slot
                    rubric = rubric.replace("<!-- LLM_FILL_OPS -->", extra)
                    rubric = rubric.replace("<!-- LLM_FILL_SAFETY -->", "")
                    print(f"LLM filled ops section only ({len(extra)} chars)", file=sys.stderr)
            else:
                print("WARNING: LLM fill returned empty (check API key)", file=sys.stderr)
        except Exception as e:
            print(f"WARNING: LLM fill skipped ({e})", file=sys.stderr)

    out.write_text(rubric)
    note = " (LLM-filled)" if args.llm_fill else " (TODO: fill overrides + safety special cases)"
    print(f"OK  wrote {out}{note}")


if __name__ == '__main__':
    main()
