---
name: aws-config-ops
description: >-
  Use when the user needs to manage AWS Config resources — configuration
  recorders, delivery channels, config rules (managed/custom), conformance
  packs, aggregators, or compliance evaluations; user mentions "AWS Config",
  "config rule", "compliance", "configuration recorder", "conformance pack",
  "resource compliance", or "config aggregation".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS Config endpoints.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-07-19"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  cross_skill_deps:
    - aws-iam-ops              # Config service-linked role / custom rule Lambda role
    - aws-s3-ops               # Delivery channel S3 bucket
    - aws-sns-ops              # Delivery channel SNS topic
    - aws-cloudtrail-ops       # Multi-account aggregator trail setup
    - aws-lambda-ops           # Custom config rule Lambda function
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['compliance-scan', 'change-impact']
    produces_facts: ['config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Config Operations Skill

## Common JSON Paths (Centralized)

Recorder: `.ConfigurationRecorders[0].{name,roleARN,recordingGroup}` | Channel: `.DeliveryChannels[0].{name,s3BucketName,s3KeyPrefix,snsTopicARN}` | Rules: `.ConfigRules[].{ConfigRuleName,ConfigRuleState,Source.{Owner,SourceIdentifier}}` | Compliance: `.EvaluationResults[].{ComplianceType,ConfigRuleInvokedBy}` | Aggregator: `.ConfigurationAggregators[].{ConfigurationAggregatorName,ConfigurationStatus}` | Packs: `.ConformancePackDetails[].{ConformancePackName,ConformancePackStatus}` | Full paths: [`references/operations.md`](references/operations.md)

## Overview & Scope

AWS Config records resource configurations and evaluates compliance against rules.
Pattern: **Pre-flight → Execute (CLI, boto3 fallback after 3 failures) → Validate → Recover**. All CLI uses `--output json`.

**Use for**: Configuration Recorders, Delivery Channels, Config rules (managed/custom), Conformance Packs, Aggregators, Organization Config Rules, compliance evaluation.
**Delegate**: IAM→`aws-iam-ops` | Lambda→`aws-lambda-ops` | S3 delivery→`aws-s3-ops` | SNS→`aws-sns-ops` | CloudTrail→`aws-cloudtrail-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default `us-east-1` if unset |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile over explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.recorder_name}}` | User input | Configuration recorder name (default: `default`) |
| `{{user.channel_name}}` | User input | Delivery channel name (default: `default`) |
| `{{user.s3_bucket}}` | User input | S3 bucket for delivery |
| `{{user.s3_prefix}}` | User input | S3 key prefix for config snapshots |
| `{{user.sns_topic_arn}}` | User input | SNS topic ARN for notifications |
| `{{user.delivery_frequency}}` | User input | OneHour \| ThreeHours \| SixHours \| TwelveHours \| TwentyFourHours |
| `{{user.rule_name}}` | User input | Config rule name |
| `{{user.rule_identifier}}` | User input | Managed rule identifier (e.g., `S3_BUCKET_PUBLIC_READ_PROHIBITED`) |
| `{{user.pack_name}}` | User input | Conformance pack name |
| `{{user.pack_template_uri}}` | User input | Template S3 URI or body |
| `{{user.aggregator_name}}` | User input | Aggregator name |
| `{{user.aggregator_source}}` | User input | Account IDs or organization |
| `{{output.rule_arn}}` | API response | Parse: `.ConfigRuleArn` |
| `{{output.aggregator_arn}}` | API response | Parse: `.ConfigurationAggregatorArn` |

## Execution Flow Pattern

Every op: **Pre-flight → Execute (CLI, boto3 fallback after 3 failures) → Validate → Recover**. Pre-flight: `aws --version && aws sts get-caller-identity`. For recorder setup: verify `AWSServiceRoleForConfig` exists. Full flows: [`references/operations.md`](references/operations.md).

## Reference Files

- [`references/operations.md`](references/operations.md) — all CLI commands, validation, recovery
- [`references/aws-cli-usage.md`](references/aws-cli-usage.md) | [`references/boto3-sdk-usage.md`](references/boto3-sdk-usage.md)
- [`references/core-concepts.md`](references/core-concepts.md) | [`references/troubleshooting.md`](references/troubleshooting.md)
- [`references/security-baseline-rules.md`](references/security-baseline-rules.md) | [`references/cis-checklist.md`](references/cis-checklist.md)
- [`references/auto-remediation.md`](references/auto-remediation.md) | [`references/delegate-contract.md`](references/delegate-contract.md)
- [`references/integration.md`](references/integration.md) | [`references/rubric.md`](references/rubric.md) | [`references/prompt-templates.md`](references/prompt-templates.md)

## Quality Gate (GCL)

Full spec: [`aws-skill-generator/references/gcl-spec.md`](../../aws-skill-generator/references/gcl-spec.md).
5-dimension rubric (Safety=0→ABORT) in [`references/rubric.md`](references/rubric.md).

Destructive ops (all require GCL): `delete-config-rule`, `delete-configuration-recorder` (stop first), `delete-delivery-channel`, `delete-conformance-pack`, `delete-configuration-aggregator`, `delete-organization-config-rule`, `delete-aggregation-authorization`, `delete-retention-configuration`, `stop-configuration-recorder`. Safety tokens: `confirm=DELETE_<OP> <name>` / `confirm=STOP_RECORDER <name>`. Full rubric: [`references/rubric.md`](references/rubric.md), prompts: [`references/prompt-templates.md`](references/prompt-templates.md), spec: [`gcl-spec.md`](../../aws-skill-generator/references/gcl-spec.md).

Prompt templates: [`references/prompt-templates.md`](references/prompt-templates.md)

## Token Efficiency (C6 MUST PASS)

TE-1: No hardcoded rule IDs (use `describe-config-rules`). TE-2: boto3 inline comments only. TE-3: compact error tables → operations.md. TE-4: JSON paths centralized above. TE-5: YAML anchors → `assets/example-config.yaml`. TE-6: flows only in SKILL.md + operations.md.

> After completing a task, review and distill reusable assets per the root AGENTS.md "Compound-Asset Distillation Loop (CADL)".
