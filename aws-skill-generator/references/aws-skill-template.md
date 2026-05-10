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
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

# AWS [Service Name] Operations Skill

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
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.resource_name}}` | User input | Ask once; reuse |
| `{{output.resource_id}}` | Last API response | Parse per AWS API docs |

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
| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; configure env |
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