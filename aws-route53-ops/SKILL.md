---
name: aws-route53-ops
description: Use when the user needs to create, manage, or delete DNS records and
  hosted zones in AWS Route53; configure DNS routing policies including failover,
  latency-based, geolocation, or weighted routing for Route53 hosted zones; set up
  health checks for DNS failover; manage alias records pointing to AWS resources like
  ELB, S3, or CloudFront; troubleshoot DNS resolution issues; or delegate domain zones
  in Route53, even if they don't say "Route53" and instead say "set up DNS records",
  "configure DNS failover", "manage hosted zones", "set up health checks for my website",
  or "create alias records for AWS resources".
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network
  access to Route53 endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION
  - AWS_SESSION_TOKEN
  cross_skill_deps:
  - aws-elb-ops
  - aws-cloudwatch-ops
  - aws-acm-ops
  - aws-cloudfront-ops
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'self-heal', 'change-impact']
    produces_facts: ['state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Route 53 Operations Skill

Use for hosted zones, record sets, health checks, routing policies, resolver resources, delegation, DNS failover, and propagation monitoring. Detailed commands remain in references.

## Common JSON Paths

Zones: .HostedZones[].{Id,Name,Config,ResourceRecordSetCount}
Records: .ResourceRecordSets[].{Name,Type,TTL,ResourceRecords,AliasTarget,SetIdentifier,Failover,Weight}
HealthChecks: .HealthChecks[].{Id,HealthCheckConfig,HealthCheckVersion}
Changes: .ChangeInfo.{Id,Status,SubmittedAt}

## Trigger & Scope

### SHOULD Use When
Route53 zones/records, aliases, health checks, routing policies, DNS failover, delegation, resolver, or propagation.

### SHOULD NOT Use When
CloudFront distributions → `aws-cloudfront-ops`; ELB resources → `aws-elb-ops`; ACM certificates → `aws-acm-ops`; VPC networking → `aws-vpc-ops`.

### Delegation
ELB health/traffic → `aws-elb-ops`; CloudWatch metrics → `aws-cloudwatch-ops`; certificates → `aws-acm-ops`; orchestration → `aws-aiops-orchestrator`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.hosted_zone_id}}`, `{{user.record_name}}`, `{{user.record_type}}` | User input | DNS identity |
| `{{user.health_check_id}}`, `{{user.change_batch}}` | User input | Health/change payload |
| `{{output.*}}` | API response | Reuse change/zone/health IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify zone ownership/delegation, exact record identity, routing policy, aliases, health checks, current values, and production impact. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll `get-change` to `INSYNC` and resolve DNS externally; recover with bounded retries and halt on invalid batch, delegation, or ambiguous records. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update record | Diff exact name/type/set identifier and routing impact | Token for production/failover changes |
| Delete record | Fetch exact current value; DELETE payload must match | `confirm=DELETE_RECORD <zone>:<name>:<type>` |
| Delete hosted zone | Refuse while any non-NS/SOA record remains; inspect delegation | `confirm=DELETE_HOSTED_ZONE <zone-id>` |
| Delete health check | Inspect record associations and failover impact | `confirm=DELETE_HEALTH_CHECK <id>` |
| Automated failover | Correlate Route53 and ELB health; never switch on one noisy sample | Decision-tier/token authorization |

Never delete default NS/SOA records directly. Mask private endpoint/IP metadata when policy requires.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live records/health state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for DNS-routing/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits policy-approved failover only after multi-signal validation; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
