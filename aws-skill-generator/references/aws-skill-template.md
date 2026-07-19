---
name: aws-[service-name]-ops
description: >-
  Use when operating AWS [Service Name] resources via AWS CLI or boto3 SDK;
  user mentions [Service Name], [Service Alias], or [Resource Type].
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-10"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  type: base             # base | composite  —— 复合/copilot 技能填 composite
  provides:              # 本 skill 能处理的操作列表（取自下方 Execution Flow 的 operation 名）
    - "<operation-1>"
    - "<operation-2>"
  delegate:              # 仅 composite 填：委派的下游 skill → 操作映射
    aws-<svc>-ops:
      - "<operation>"
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
---

# AWS [Service Name] Operations Skill

## Layering Contract (type / provides / delegate)

`metadata.type` declares the skill layer: `base` (single-service runbook, L1) or
`composite` (copilot/orchestrator, L2). A `composite` skill **orchestrates only** —
it lists the operations it `provides` and maps each to a downstream base skill via
`delegate:`; it must contain no service-level operation logic.
These fields are machine-readable: any agent globs `aws-*-ops/SKILL.md`, reads
frontmatter, and composes skills without a per-agent loader.

## Overview

AWS [Service Name] provides [brief description]. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, dual-path execution (AWS CLI + boto3 SDK), validation, and recovery.

## Trigger & Scope

### SHOULD Use When
- User mentions "AWS [Service Name]" or "[Service Alias]"
- Task involves CRUD on **[Resource Type]** (create, describe, modify, delete, list)
- Keywords: [keyword1], [keyword2], [keyword3]

### SHOULD NOT Use When
- Billing only → delegate to: `aws-cost-ops`
- IAM only → delegate to: `aws-iam-ops`
- Related service → delegate to: `aws-[other]-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole); overrides explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.resource_name}}` | User input | Ask once; reuse |
| `{{output.resource_id}}` | Last API response | Parse per AWS API docs |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values:

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{env.AWS_ACCOUNT_ID}}` | `.env` or runtime env | Substitute before use |
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

### Operation: Create [Resource]

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| Region valid | `aws [service] list-[resources] --region {{user.region}}` | Suggest valid region |
| Quota | Check service quotas | HALT; request increase |

#### Execute — CLI (Primary)
```bash
aws [service] create-[resource] \
  --name "{{user.resource_name}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('[service]', region_name='{{user.region}}')
response = client.create_[resource](Name='{{user.resource_name}}')
```

#### Validate
Poll until terminal state (running/available) with max wait.

#### Recover
| Error | Action |
|-------|--------|
| InvalidParameter | Fix args; retry once |
| QuotaExceeded | HALT |
| Throttling (429) | Backoff, retry 3x |
| 5xx Internal | Retry 3x, then HALT |

### Operation: Delete [Resource]

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Integration Setup](references/integration.md)

## Token Efficiency Guidelines (P0)

Generated skills MUST follow these 6 rules to minimize Token consumption:

### TE-1: API Query > Static Tables
Use API commands instead of hardcoding version/port/limit tables.
```markdown
# DO: minimal table + API fallback
aws [service] describe-[something] --query "..."
| Engine | Port | Min |
|--------|------|-----|
| EngineA | 1234 | X GB |
```
### TE-2: No docstrings in boto3 SDK
```python
# DO: inline comments only
def create_resource(name):
    try: return client.create_resource(Name=name)['Resource']
    except ClientError as e: handle_error(e)
```
### TE-3: Compact error tables
```markdown
| Error | Resolution |
|-------|-----------|
| InvalidParameter | HALT — fix params |
```
### TE-4: Centralized JSON paths
File-top comment block; one per resource type.
### TE-5: YAML anchors in example-config.yaml
Use `&dev` / `&prod` anchors to eliminate repeated fields.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow → no Complete Workflow in config or SDK file.

**See**: `aws-skill-generator` SKILL.md §Token Efficiency Requirements for detailed examples.

---

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。