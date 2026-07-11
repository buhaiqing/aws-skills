---
name: aws-cloudtrail-ops
description: >-
  Use when managing CloudTrail audit trails, querying AWS API events, or investigating "who did what when". Invoke when user mentions "CloudTrail", "audit trail", or needs event history and logging analysis.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access to CloudTrail endpoints.
metadata:
  author: aws
  version: "1.1.0"
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
  cross_skill_deps:
    - aws-s3-ops              # S3 bucket for trail logs
    - aws-kms-ops           # KMS key for trail encryption
    - aws-cloudwatch-ops    # CloudWatch Logs integration
    - aws-iam-ops           # IAM roles for CloudTrail access
  gcl:
    enabled: true
    class: optional
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['rca', 'change-impact', 'forensic']
    produces_facts: ['event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS CloudTrail Operations Skill

## Overview

AWS CloudTrail records AWS API calls. This skill is an **operational runbook**
with explicit scope, credential rules, pre-flight checks, dual-path execution
(AWS CLI + boto3 SDK), validation, and recovery.

## Common JSON Paths (Centralized)

```
# Create Trail:      .Trail.{TrailARN,Name,S3BucketName}
# Describe Trails:   .trailList[].{Name,TrailARN,S3BucketName,IsMultiRegionTrail,HomeRegion}
# Get Trail Status:  .{IsLogging,LatestDeliveryTime,LatestDeliveryError}
# Lookup Events:     .Events[].{EventId,EventTime,EventSource,EventName,Username}
# Get Event Sel:     .EventSelectors[].{ReadWriteType,IncludeManagementEvents}
# Get Insight Sel:   .InsightSelectors[].InsightType
```

## Trigger & Scope

### SHOULD Use When
- User requests CloudTrail trail creation, modification, or deletion
- User asks to query events with `lookup-events`
- User needs to enable/disable trail logging
- User mentions "CloudTrail", "audit trail", "API logging", "event history"
- User needs to troubleshoot "who did what when" in AWS
- User asks about CloudTrail Insights or anomaly detection
- User needs multi-region or organization trail setup

### SHOULD NOT Use When
- General monitoring/alarms → delegate to: `aws-cloudwatch-ops`
- S3 bucket operations → delegate to: `aws-s3-ops`
- IAM operations → delegate to: `aws-iam-ops`
- Log analysis → delegate to: `aws-cloudwatch-ops`

### Delegation
- S3 bucket → `aws-s3-ops` (trail logging bucket)
- KMS key → `aws-kms-ops` (trail encryption)
- CloudWatch Logs → `aws-cloudwatch-ops` (CloudWatch integration)
- IAM → `aws-iam-ops` (trail role permissions)

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole); overrides explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.TrailName}}` | User input | Ask once; reuse |
| `{{user.S3BucketName}}` | User input | my-cloudtrail-logs |
| `{{user.S3KeyPrefix}}` | User input | audit/ |
| `{{user.KmsKeyId}}` | User input | alias/cloudtrail |
| `{{user.StartTime}}` | User input | ISO 8601 timestamp |
| `{{user.EndTime}}` | User input | ISO 8601 timestamp |
| `{{output.TrailARN}}` | API response | Parse: `.Trail.TrailARN` after Create/Describe |
| `{{output.IsLogging}}` | API response | Parse: `.IsLogging` from get-trail-status; must be `true` before confirming success |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
| `{{user.TrailName}}` | User input | Ask once; substitute |
| `{{user.S3BucketName}}` | User input | Ask once; substitute |

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

### Common Pre-flight Steps (all ops)

#### Step 1: Check CLI
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: pip install awscli`

#### Step 2: Load & Verify Credentials
```bash
aws sts get-caller-identity --output json
```
Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from env)
[OK]   AWS_ACCESS_KEY_ID=**** (masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```
On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/troubleshooting.md for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide to troubleshooting.md |
| Region valid | `aws cloudtrail describe-trails --region {{user.region}}` | Suggest valid region |
| S3 bucket exists | `aws s3api head-bucket --bucket {{user.S3BucketName}}` | Create bucket or delegate to `aws-s3-ops` |

## Safety Gates

| Operation | Gate | Confirm Token |
|-----------|------|---------------|
| `delete-trail` | IRREVERSIBLE; stops ALL audit logging; event history lost | `confirm=DELETE_TRAIL <name>` |
| `stop-logging` | Audit gap from stop to restart; events not recorded | `confirm=STOP_LOGGING <name>` |
| `update-trail` | Changing S3 bucket or KMS key affects log delivery | `confirm=UPDATE_TRAIL <name>` |
| `put-event-selectors` | Narrowing scope reduces audit coverage | `confirm=PUT_EVENT_SELECTORS <name>` |

### Trail Deletion (Critical)
```
⚠️ Deleting {{user.TrailName}} will stop all audit logging.
Confirm: Type DELETE {{user.TrailName}} to proceed.
```

### Stop Logging
```
⚠️ Logging will stop. No events will be recorded until restarted.
Continue? (yes/no)
```

## Operations

### Operation: Create Trail

#### Pre-flight
| Check | Method | On Failure |
|-------|--------|------------|
| S3 bucket exists | `aws s3api head-bucket --bucket {{user.S3BucketName}}` | Delegate to `aws-s3-ops` |
| Bucket policy allows CloudTrail | `aws s3api get-bucket-policy --bucket {{user.S3BucketName}}` | Add CloudTrail write policy |
| Trail name unique | `aws cloudtrail describe-trails --trail-name-list {{user.TrailName}}` | Use different name |

#### Execute — CLI (Primary)
```bash
TRAIL_ARN=$(aws cloudtrail create-trail \
  --name "{{user.TrailName}}" \
  --s3-bucket-name "{{user.S3BucketName}}" \
  --s3-key-prefix "{{user.S3KeyPrefix:audit/}}" \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --region "{{user.region}}" \
  --output json | jq -r '.TrailARN')
```
Log: `[OK] Trail created: $TRAIL_ARN`
Set `{{output.TrailARN}}` = `$TRAIL_ARN`

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('cloudtrail', region_name='{{user.region}}')
response = client.create_trail(
    Name='{{user.TrailName}}',
    S3BucketName='{{user.S3BucketName}}',
    S3KeyPrefix='{{user.S3KeyPrefix}}',
    IsMultiRegionTrail=True,
    EnableLogFileValidation=True
)
trail_arn = response['TrailARN']
```

#### Validate
Poll until `IsLogging=true` (max 5 min, interval 10s):
```bash
for i in $(seq 1 30); do
  LOGGING=$(aws cloudtrail get-trail-status --name "{{user.TrailName}}" --region "{{user.region}}" --output json | jq -r '.IsLogging')
  [ "$LOGGING" = "true" ] && break
  sleep 10
done
```

#### Recover
| Error | Action |
|-------|--------|
| TrailAlreadyExists | HALT — describe existing trail and inform user |
| InsufficientS3BucketPolicy | FIX — add CloudTrail S3 policy |
| S3BucketNotFound | HALT — delegate to `aws-s3-ops` to create bucket |
| KMSKeyNotFound | HALT — delegate to `aws-kms-ops` to verify key |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Start Logging

#### Pre-flight
- Verify trail exists and name matches: `aws cloudtrail describe-trails --trail-name-list {{user.TrailName}}`
- Check current status: `aws cloudtrail get-trail-status --name {{user.TrailName}}`

#### Execute — CLI (Primary)
```bash
aws cloudtrail start-logging \
  --name "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.start_logging(Name='{{user.TrailName}}')
```

#### Validate
Poll `get-trail-status` until `IsLogging=true` (max 2 min, interval 10s):
```bash
for i in $(seq 1 12); do
  LOGGING=$(aws cloudtrail get-trail-status --name "{{user.TrailName}}" --region "{{user.region}}" --output json | jq -r '.IsLogging')
  [ "$LOGGING" = "true" ] && break
  sleep 10
done
```

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — verify trail name |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Stop Logging (Destructive)

#### Safety Gate (Mandatory)
- MUST confirm: `confirm=STOP_LOGGING {{user.TrailName}}`
- Warn: audit events will NOT be recorded from this point until `start-logging` is called

#### Execute — CLI (Primary)
```bash
aws cloudtrail stop-logging \
  --name "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.stop_logging(Name='{{user.TrailName}}')
```

#### Validate
Poll `get-trail-status` until `IsLogging=false` (max 1 min, interval 5s):
```bash
for i in $(seq 1 12); do
  LOGGING=$(aws cloudtrail get-trail-status --name "{{user.TrailName}}" --region "{{user.region}}" --output json | jq -r '.IsLogging')
  [ "$LOGGING" = "false" ] && break
  sleep 5
done
```

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — verify trail name |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Delete Trail (Destructive)

#### Safety Gate (Mandatory)
- MUST confirm: `confirm=DELETE_TRAIL {{user.TrailName}}`
- Pre-flight: capture trail ARN and IsLogging state
- Warn: ALL event history in the S3 bucket remains but no NEW events recorded

#### Execute — CLI (Primary)
```bash
aws cloudtrail delete-trail \
  --name "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_trail(Name='{{user.TrailName}}')
```

#### Validate
Verify trail is gone:
```bash
aws cloudtrail describe-trails --trail-name-list "{{user.TrailName}}" --region "{{user.region}}" --output json
# Expected: ResourceNotFoundException
```

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — trail already deleted or name wrong |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Describe Trails

#### Execute — CLI (Primary)
```bash
# Single trail
aws cloudtrail describe-trails \
  --trail-name-list "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json

# All trails
aws cloudtrail describe-trails \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.describe_trails(TrailNameList=['{{user.TrailName}}'])
for t in response['trailList']:
    print(f"{t['Name']}: {t['TrailARN']} IsLogging={t.get('IsLogging')}")
```

#### Validate
Verify response contains requested trail.

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — verify trail name |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Lookup Events

#### Execute — CLI (Primary)
```bash
# Basic — last 90 days (CloudTrail default)
aws cloudtrail lookup-events \
  --region "{{user.region}}" \
  --output json

# By time range
aws cloudtrail lookup-events \
  --start-time "{{user.StartTime}}" \
  --end-time "{{user.EndTime}}" \
  --region "{{user.region}}" \
  --output json

# By Username
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue="{{user.Username}}" \
  --region "{{user.region}}" \
  --output json

# By EventName
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue="{{user.EventName}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.lookup_events(
    LookupAttributes=[{'AttributeKey': 'Username', 'AttributeValue': '{{user.Username}}'}],
    StartTime='{{user.StartTime}}',
    EndTime='{{user.EndTime}}',
    MaxResults=50
)
for e in response['Events']:
    print(f"{e['EventTime']} {e['EventName']} by {e['Username']}")
```

#### Validate
Verify response contains `Events[]` array. Handle `NextToken` for pagination.

#### Recover
| Error | Action |
|-------|--------|
| InvalidLookupAttribute | Fix attribute key/value; retry |
| ThrottlingException | Backoff; retry 3x |
| 5xx Internal | Retry 3x; then HALT |

---

### Operation: Put Event Selectors

#### Pre-flight
- Verify trail exists and name matches
- Check current selectors: `aws cloudtrail get-event-selectors --trail-name {{user.TrailName}}`

#### Execute — CLI (Primary)
```bash
# Management events only (recommended)
aws cloudtrail put-event-selectors \
  --trail-name "{{user.TrailName}}" \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true}]' \
  --region "{{user.region}}" \
  --output json

# With S3 data events
aws cloudtrail put-event-selectors \
  --trail-name "{{user.TrailName}}" \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,"DataResources":[{"Type":"AWS::S3::Object","Values":["arn:aws:s3:::{{user.BucketName}}/*"]}]}]' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_event_selectors(
    TrailName='{{user.TrailName}}',
    EventSelectors=[{
        'ReadWriteType': 'All',
        'IncludeManagementEvents': True,
        'DataResources': [{'Type': 'AWS::S3::Object', 'Values': ['arn:aws:s3:::{{user.BucketName}}/*']}]
    }]
)
```

#### Validate
```bash
aws cloudtrail get-event-selectors \
  --trail-name "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json | jq '.EventSelectors'
```

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — verify trail name |
| InvalidEventSelectors | Fix selectors format; retry |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Put Insight Selectors

#### Pre-flight
- Verify trail exists and is logging

#### Execute — CLI (Primary)
```bash
aws cloudtrail put-insight-selectors \
  --trail-name "{{user.TrailName}}" \
  --insight-selectors '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]' \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.put_insight_selectors(
    TrailName='{{user.TrailName}}',
    InsightSelectors=[
        {'InsightType': 'ApiCallRateInsight'},
        {'InsightType': 'ApiErrorRateInsight'}
    ]
)
```

#### Validate
```bash
aws cloudtrail get-insight-selectors \
  --trail-name "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json | jq '.InsightSelectors'
```

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — verify trail name |
| InvalidInsightSelector | Fix selectors; retry |
| InsightNotEnabled | HALT — Insights must be enabled on the trail first |
| ThrottlingException | Backoff; retry 3x |

---

### Operation: Get Trail Status

#### Execute — CLI (Primary)
```bash
aws cloudtrail get-trail-status \
  --name "{{user.TrailName}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
response = client.get_trail_status(Name='{{user.TrailName}}')
logging = response['IsLogging']
latest_delivery = response.get('LatestDeliveryTime')
latest_error = response.get('LatestDeliveryError')
print(f"Logging: {logging}, LastDelivery: {latest_delivery}, Error: {latest_error}")
```

#### Validate
Verify `IsLogging` matches expected state.

#### Recover
| Error | Action |
|-------|--------|
| TrailNotFound | HALT — verify trail name |
| ThrottlingException | Backoff; retry 3x |

---

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](../aws-skill-generator/references/integration.md)
- [Example Configuration](assets/example-config.yaml)
- [Prompt Examples](references/prompt-examples.md)

## Related Skills

- `aws-s3-ops` — S3 bucket for trail logs
- `aws-kms-ops` — KMS key for trail encryption
- `aws-iam-ops` — IAM roles for CloudTrail access
- `aws-cloudwatch-ops` — CloudWatch Logs integration

## Token Efficiency Guidelines (P0)

The following 6 rules minimize Token consumption:

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding trail config or limit tables.
```markdown
# DO: describe-trails to discover existing trails
aws cloudtrail describe-trails --region {{user.region}}
```
### TE-2: No docstrings in boto3 SDK
```python
# DO: inline comments only
def create_trail(client, name, bucket):
    try: return client.create_trail(Name=name, S3BucketName=bucket)
    except ClientError as e: handle_error(e)
```
### TE-3: Compact error tables
```markdown
| Error | Resolution |
|-------|-----------|
| TrailAlreadyExists | HALT — provide existing trail info |
| TrailNotFound | HALT — verify trail name |
| InsufficientS3BucketPolicy | FIX — update bucket policy for CloudTrail |
| S3BucketNotFound | FIX — create bucket first |
| Throttling | Backoff, retry 3x |
| 5xx Internal | Retry 3x; then HALT |
```
### TE-4: Centralized JSON paths
File-top `## Common JSON Paths` block; one path per resource type.
### TE-5: YAML anchors in example-config.yaml
Use `&trail-basic` / `&event-sel-all` anchors in `assets/example-config.yaml`.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow → no Complete Workflow in reference files.

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, optional). Every execution of
> `aws-cloudtrail-ops` MUST be wrapped by the Generator-Critic-Loop
> defined in `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value | Source |
|---|---|---|
| Class | `optional` | `gcl-spec.md` §10 |
| `max_iterations` | `3` | `gcl-spec.md` §10 (default for optional skills) |
| Rubric | `references/rubric.md` (v1) | this skill |
| Prompts | `references/prompt-templates.md` (v1) | this skill |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |

### Per-operation gating

The Orchestrator applies GCL on every execution. The following operations
are **destructive** and require `{{user.safety_confirm}}` in the trace
(exact format `confirm=<OPERATION> <resource-id>`):

- `delete-trail` — **SEVERE**; stops ALL audit logging; all event history lost;
  confirm `confirm=DELETE_TRAIL <name>`
- `stop-logging` — audit gap from stop to restart; confirm
  `confirm=STOP_LOGGING <name>`
- `update-trail` — changing S3 bucket or KMS key affects log delivery;
  confirm `confirm=UPDATE_TRAIL <name>`
- `put-event-selectors` — narrowing scope reduces audit coverage

### AWS-specific rules in force

This skill's rubric instantiates the repo-wide AWS rules from
`gcl-spec.md` §8. The ones most relevant to CloudTrail:

- **A7** — `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** — `TrailName` in request must be echoed from a `describe-trails` lookup
- **A9** — Event data containing credentials (AKIA*, `-----BEGIN .*-----`) MUST NOT appear in trace; mask to `***<len>`
- **A10** — `aws sts get-caller-identity` MUST be the first command in trace

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric + safety special cases
- `references/prompt-templates.md` — Generator / Critic / Orchestrator skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## AIOps: CloudTrail for Audit & Forensic RCA

### AIOps Data Collection: CloudTrail Metrics for RCA

| Metric / Event | Namespace | AIOps Use |
|----------------|-----------|-----------|
| `LookupEvents` count | CloudTrail API | Anomalous admin activity detection |
| `CreateTrail` / `DeleteTrail` | CloudTrail Management | Trail config change audit |
| `PutUserPolicy` / `PutRolePolicy` | IAM events | Privilege escalation RCA |
| `DeleteUser` / `DeleteRole` | IAM events | Identity deletion forensic |
| `PutBucketPolicy` / `PutBucketAcl` | S3 events | Public exposure RCA |
| `AuthorizeSecurityIngress` | EC2 events | Security group widening RCA |
| `ConsoleLogin` / `AssumeRole` | STS events | Unauthorized access detection |
| ApiCallRateInsight | CloudTrail | Unusual API volume anomaly detection |
| ApiErrorRateInsight | CloudTrail | Error spike detection |

### AIOps Diagnostic Flows (Cross-Skill)

```
CloudTrail RCA Flow:
  1. [aws-cloudtrail-ops] lookup-events for target resource + time window
  2. [aws-cloudtrail-ops] Identify actor: Username / ARN / Root / SSOUser
  3. [aws-iam-ops] If IAM actor: describe-user / describe-role
  4. [aws-s3-ops] If S3 event: check bucket policy + ACL for public access
  5. [aws-cloudwatch-ops] Correlate API spike with CloudWatch API throttle metrics
  6. [aws-cloudtrail-ops] Generate RCA: Who, When, Where, What, SourceIP, UserAgent
```

### Self-Healing Actions

#### AH-CT-01: Auto-Enable Trail Logging After Outage [AI_ASSIST]

Trigger: Trail `IsLogging=false` detected AND no `stop-logging` event in CloudTrail.

```
Decision: [AI_ASSIST] (logging gap = compliance risk; user must confirm)
```

```bash
aws cloudtrail start-logging --name "{{user.TrailName}}"
aws cloudtrail get-trail-status --name "{{user.TrailName}}"
```

#### AH-CT-02: Enable CloudTrail Insights on Anomaly Detection [AI_ASSIST]

Trigger: Repeated `ThrottlingException` on a specific API across multiple accounts.

```
Decision: [AI_ASSIST] (cost: ~$0.35/100k insights events; no data risk)
```

```bash
aws cloudtrail put-insight-selectors \
  --name "{{user.TrailName}}" \
  --insight-selectors \
    '[{"InsightType":"ApiCallRateInsight"},{"InsightType":"ApiErrorRateInsight"}]' \
  --region "{{user.region}}" --output json
```

### Cross-Module Integration

| Condition | Delegate To |
|-----------|-------------|
| S3 bucket for trail logs | `aws-s3-ops` |
| KMS key for trail encryption | `aws-kms-ops` |
| CloudWatch Logs integration | `aws-cloudwatch-ops` |
| IAM role for CloudTrail | `aws-iam-ops` |
| API throttle correlation | `aws-cloudwatch-ops` |

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

