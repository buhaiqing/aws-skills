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
  version: "1.0.0"
  last_updated: "2026-06-07"
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

```
# Recorder:      .ConfigurationRecorders[0].{name,roleARN,recordingGroup.{allSupported,includeGlobalResourceTypes,resourceTypes}}
# Recording:     .RecordingStatus.{lastStatus,lastStartTime,lastStopTime}
# Delivery:      .DeliveryChannels[0].{name,s3BucketName,s3KeyPrefix,snsTopicARN,snapshotDeliveryProperties.{deliveryFrequency}}
# Rules:         .ConfigRules[].{ConfigRuleName,ConfigRuleId,ConfigRuleState,Source.{Owner,SourceIdentifier},Scope.{ComplianceResourceTypes},MaximumExecutionFrequency}
# Rule Status:   .ConfigRuleEvaluationStatus[].{ConfigRuleName,FirstActivatedTime,LastSuccessfulEvaluationTime,LastFailedEvaluationTime,LastErrorCode}
# Compliance:    .EvaluationResults[].{ComplianceResourceType,ComplianceResourceId,ComplianceType,ConfigRuleInvokedBy,ResultRecordedTime,Annotation}
# Aggregator:    .ConfigurationAggregators[].{ConfigurationAggregatorName,ConfigurationAggregatorArn,AccountAggregationSources[],OrganizationAggregationSource}
# Conformance Packs: .ConformancePackDetails[].{ConformancePackName,ConformancePackId,ConformancePackArn,TemplateSSMUri,LastUpdateRequestedTime}
# Org Rules:     .OrganizationConfigRules[].{OrganizationConfigRuleName,OrganizationConfigRuleId,OrganizationCustomRuleMetadata}
```

## Overview

AWS Config records resource configurations and evaluates compliance against rules.
Operational runbook with pre-flight → execute → validate → recover.

## Trigger & Scope

### SHOULD Use When
- User mentions "AWS Config", "config rule", "compliance", "configuration recorder"
- Task involves setting up or modifying **Configuration Recorders** or **Delivery Channels**
- Task involves **managed/custom Config rules** (create, evaluate, delete)
- Task involves **Conformance Packs** or **Organization Config Rules**
- Task involves multi-account **Aggregator** setup
- Task involves **compliance evaluation** or resource drift detection
- Keywords: config, compliance, configuration-recorder, delivery-channel, conformance-pack, aggregator, resource-compliance, drift

### SHOULD NOT Use When
- IAM only → delegate to: `aws-iam-ops`
- Lambda function for custom rule → delegate to: `aws-lambda-ops`
- S3 bucket for delivery → delegate to: `aws-s3-ops`
- SNS topic for notifications → delegate to: `aws-sns-ops`
- CloudTrail for API audit → delegate to: `aws-cloudtrail-ops`
- Standalone resource tagging → use `aws resourcegroupstaggingapi` CLI directly

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
| `{{user.delivery_frequency}}` | User input | OneHour | ThreeHours | SixHours | TwelveHours | TwentyFourHours |
| `{{user.rule_name}}` | User input | Config rule name |
| `{{user.rule_identifier}}` | User input | Managed rule identifier (e.g., `S3_BUCKET_PUBLIC_READ_PROHIBITED`) |
| `{{user.pack_name}}` | User input | Conformance pack name |
| `{{user.pack_template_uri}}` | User input | Template S3 URI or body |
| `{{user.aggregator_name}}` | User input | Aggregator name |
| `{{user.aggregator_source}}` | User input | Account IDs or organization |
| `{{output.rule_arn}}` | API response | Parse: `.ConfigRuleArn` |
| `{{output.aggregator_arn}}` | API response | Parse: `.ConfigurationAggregatorArn` |

## Execution Flow Pattern

Every operation: **Pre-flight** → **Execute** (CLI, boto3 fallback) → **Validate** → **Recover**.
Shared pre-flight steps below apply to all operations.

### Common Pre-flight Steps (all ops)

```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] AWS CLI v2.x` and `[OK] Identity: arn:aws:iam::...`.
For Setup Recorder, also verify service-linked role:
```bash
aws iam get-role --role-name AWSServiceRoleForConfig --output json \
  || aws iam create-service-linked-role --aws-service-name config.amazonaws.com --output json
```

### Operation: Setup Configuration Recorder

#### Execute — CLI (Primary)
```bash
aws configservice put-configuration-recorder \
  --configuration-recorder "name={{user.recorder_name}},roleARN=arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig" \
  --recording-group "allSupported=true,includeGlobalResourceTypes=true" \
  --region "{{user.region}}" \
  --output json
```

#### Validate
`aws configservice describe-configuration-recorders` → check name and roleARN match.

#### Recover
| Error | Action |
|-------|--------|
| InvalidConfigurationRecorderName / InvalidRole | Fix name or role ARN; retry |
| Throttling | Backoff; retry 3x |

### Setup Delivery Channel
Pre-flight: `aws s3api head-bucket --bucket {{user.s3_bucket}}` (verify bucket exists)
```bash
aws configservice put-delivery-channel \
  --delivery-channel "name={{user.channel_name}},s3BucketName={{user.s3_bucket}},s3KeyPrefix={{user.s3_prefix}},snsTopicARN={{user.sns_topic_arn}}" \
  --region "{{user.region}}" \
  --output json
```

### Start/Stop Recorder
```bash
aws configservice start-configuration-recorder --configuration-recorder-name "{{user.recorder_name}}" --region "{{user.region}}" --output json
aws configservice stop-configuration-recorder --configuration-recorder-name "{{user.recorder_name}}" --region "{{user.region}}" --output json
```

### Add Managed Config Rule
```bash
aws configservice put-config-rule \
  --config-rule "ConfigRuleName={{user.rule_name}},Source={Owner=AWS,SourceIdentifier={{user.rule_identifier}}},Scope={ComplianceResourceTypes=[\"AWS::S3::Bucket\"]}" \
  --region "{{user.region}}" \
  --output json
```
Validate: `aws configservice describe-config-rules --config-rule-names "{{user.rule_name}}"`

### Run Compliance Evaluation
```bash
aws configservice start-config-rules-evaluation --config-rule-names "{{user.rule_name}}" --region "{{user.region}}" --output json
# Query results: aws configservice get-compliance-details-by-config-rule --config-rule-name "{{user.rule_name}}" --compliance-types NON_COMPLIANT
```

### Delete Config Rule
**Safety Gate**: `confirm=DELETE_RULE {{user.rule_name}}`
```bash
aws configservice delete-config-rule --config-rule-name "{{user.rule_name}}" --region "{{user.region}}" --output json
```
Validate: `describe-config-rules` returns empty for {{user.rule_name}}.

### Set Up Aggregator
```bash
# Single account source
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name "{{user.aggregator_name}}" \
  --account-aggregation-sources "[{\"AccountIds\":[\"123456789012\"],\"AllAwsRegions\":true}]" \
  --region "{{user.region}}" --output json
# Organization source (requires Organizations + Trusted Access)
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name "{{user.aggregator_name}}" \
  --organization-aggregation-source "RoleArn=arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig,AllAwsRegions=true" \
  --region "{{user.region}}" --output json
```

### Deploy Conformance Pack
```bash
aws configservice put-conformance-pack \
  --conformance-pack-name "{{user.pack_name}}" \
  --template-s3-uri "{{user.pack_template_uri}}" \
  --region "{{user.region}}" --output json
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## Quality Gate (GCL)

Full spec: [`aws-skill-generator/references/gcl-spec.md`](../../aws-skill-generator/references/gcl-spec.md).
5-dimension rubric (Safety=0→ABORT) in [`references/rubric.md`](references/rubric.md).

| Operation | GCL | Notes |
|---|---|---|
| `delete-config-rule` | required | `confirm=DELETE_RULE <name>` |
| `delete-configuration-recorder` | required | Must stop first; `confirm=DELETE_RECORDER <name>` |
| `delete-delivery-channel` | required | `confirm=DELETE_CHANNEL <name>` |
| `delete-aggregation-authorization` | required | `confirm=DELETE_AUTH <id>` |
| `stop-configuration-recorder` | required | Pauses all compliance evaluations |
| `put-configuration-recorder` (modify) | recommended | Can impact recording scope/cost |
| `put-delivery-channel` (modify) | recommended | Can break existing delivery |
| All other operations | not required | Create, describe, list, evaluate |

Prompt templates: [`references/prompt-templates.md`](references/prompt-templates.md)

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md). Key points:
- TE-1: No hardcoded rule identifiers — use `describe-config-rules`
- TE-2: Inline comments only in boto3 code
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized above
- TE-5: YAML anchors in `assets/example-config.yaml`
- TE-6: Flows only in SKILL.md (no duplicate in references)

## AIOps Delegate Contract

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

