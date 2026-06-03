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

<!-- TODO: list every operation in this skill and its required-dimensions=1.0 cells. -->

## Safety special cases (auto-fail)

<!-- TODO: list every AWS-API silent-failure / data-loss pattern this service can hit. -->

## Loop parameters

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


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    skill_dir, service = sys.argv[1:2] + [sys.argv[2]]
    # crude mapping
    aws_cli_svc = skill_dir.replace('aws-', '').replace('-ops', '')
    # ec2 / iam / kms / s3 special -> their actual service name
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
    aws_cli_svc = overrides.get(skill_dir, aws_cli_svc)
    max_iter = 3 if 'recommended' in sys.argv else 2
    out = Path(skill_dir) / 'references' / 'rubric.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.format(
        skill=skill_dir,
        service=service,
        aws_cli_svc=aws_cli_svc,
        max_iter=max_iter,
    ))
    print(f'OK  wrote {out} (TODO: fill in overrides + safety special cases)')


if __name__ == '__main__':
    main()
