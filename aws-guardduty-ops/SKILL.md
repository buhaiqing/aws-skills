---
name: aws-guardduty-ops
description: >-
  Use when operating AWS GuardDuty resources via AWS CLI or boto3 SDK;
  user mentions GuardDuty, GuardDuty detector, GuardDuty filter, GuardDuty IP set, GuardDuty threat intel set, or GuardDuty findings.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'compliance-scan']
    produces_facts: ['finding']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS GuardDuty Operations Skill

## Overview

AWS GuardDuty is a threat detection service that continuously monitors for malicious activity and unauthorized behavior to protect your AWS accounts, workloads, and data stored in Amazon S3. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "AWS GuardDuty" or "GuardDuty"
- Task involves CRUD on **GuardDuty resources** (detector, filter, IP set, threat intel set, publishing destination, findings, admin account, member account, organization configuration)
- Keywords: guardduty, detector, filter, ip-set, threat-intel-set, findings, admin, member, organization

### SHOULD NOT Use When
- IAM only → delegate to: `aws-iam-ops`
- Related service → delegate to: `aws-securityhub-ops`
- Cost/Billing analysis → delegate to AWS Cost Explorer (if a dedicated cost skill is available)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole); overrides explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.detector_id}}` | User input | Ask once; reuse |
| `{{user.resource_name}}` | User input | Ask once; reuse |
| `{{output.resource_id}}` | Last API response | Parse per AWS API docs |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.detector_id}}` | User input | Ask once; substitute |
| `{{user.resource_name}}` | User input | Ask once; substitute |

Before using `example-config.yaml`:
1. Load `.env` from project root (if present)
2. Substitute `{{env.*}}` placeholders with loaded values
3. Collect `{{user.*}}` values from user input
4. Use rendered config for CLI/SDK commands

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Describe Detector

#### Pre-flight
1. Verify CLI availability
2. Validate AWS credentials
3. Confirm region is specified

#### Execute — CLI (Primary)
```bash
guardduty list-detectors --region {{user.region}} --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('guardduty', region_name='{{user.region}}')
response = client.list_detectors()
```

#### Validate
Check response contains detector IDs.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | No detector found in region |
| AccessDeniedException | Check IAM permissions for guardduty:ListDetectors |

### Operation: Create Filter

#### Pre-flight
1. Verify CLI availability
2. Validate AWS credentials
3. Confirm region and detector ID
4. Check filter name doesn't already exist

#### Execute — CLI (Primary)
```bash
guardduty create-filter \
  --name {{user.resource_name}} \
  --detector-id {{user.detector_id}} \
  --description "Filter for GuardDuty findings" \
  --action ARCHIVE \
  --rank 1 \
  --region {{user.region}} \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('guardduty', region_name='{{user.region}}')
response = client.create_filter(
    DetectorId='{{user.detector_id}}',
    Name='{{user.resource_name}}',
    Description='Filter for GuardDuty findings',
    Action='ARCHIVE',
    Rank=1
)
```

#### Validate
Check response contains filter ARN/ID.

#### Recover
| Error | Action |
|-------|--------|
| InvalidInputException | Fix filter parameters |
| ResourceAlreadyExistsException | Filter with this name already exists |

### Operation: Delete Filter

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

#### Pre-flight
1. Verify CLI availability
2. Validate AWS credentials
3. Confirm region, detector ID, and filter name
4. Get explicit user confirmation: `confirm=DELETE_GUARDDUTY_FILTER {{user.resource_name}}`

#### Execute — CLI (Primary)
```bash
guardduty delete-filter \
  --name {{user.resource_name}} \
  --detector-id {{user.detector_id}} \
  --region {{user.region}} \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('guardduty', region_name='{{user.region}}')
response = client.delete_filter(
    DetectorId='{{user.detector_id}}',
    FilterName='{{user.resource_name}}'
)
```

#### Validate
Confirm filter no longer exists.

#### Recover
| Error | Action |
|-------|--------|
| ResourceNotFoundException | Filter doesn't exist |
| AccessDeniedException | Check IAM permissions for guardduty:DeleteFilter |

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## Quality Gate (GCL)

This skill uses the Generator-Critic-Loop (GCL) adversarial quality gate for destructive operations.

### Supported Operations & Gating
| Operation | GCL Class | Gating Required? |
|-----------|-----------|------------------|
| list-*, describe-*, get-* | read-only | no |
| create-*, update-*, enable-*, disable-* | mutate | yes |
| delete-*, revoke-*, detach-* | destructive | yes |

### Safety Rules
1. **A7**: `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
2. **A9**: Plaintext credentials/secret data must be masked in logs
3. **GuardDuty Specific**: Destructive operations (delete-filter, delete-detector, etc.) require explicit user confirmation

## Token Efficiency Guidelines (P0)

Generated skills MUST follow these 6 rules to minimize Token consumption:

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding version/port/limit tables.
```markdown
# DO: minimal table + API fallback
aws guardduty list-detectors --query "DetectorIds[]" --region {{user.region}}
```
### TE-2: No docstrings in boto3 SDK
```python
# DO: inline comments only
def list_filters(client, detector_id):
    try: return client.list_filters(DetectorId=detector_id)
    except ClientError as e: handle_error(e)
```
### TE-3: Compact error tables
```markdown
| Error | Resolution |
|-------|-----------|
| ResourceNotFoundException | Resource doesn't exist |
```
### TE-4: Centralized JSON paths
File-top comment block; one per resource type.
### TE-5: YAML anchors in example-config.yaml
Use `&dev` / `&prod` anchors to eliminate repeated fields.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow → no Complete Workflow in config or SDK file.

**See**: `aws-skill-generator` SKILL.md §Token Efficiency Requirements for detailed examples.

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

