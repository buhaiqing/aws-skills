# CloudTrail Skill — Prompt Examples

_Last updated: 2026-06-27_

This document provides concrete user prompts for CloudTrail trail management,
event lookup, and cross-service audit investigations.

---

## Scenario 1: Create a multi-region trail with KMS encryption

### User Prompt
```
Create a CloudTrail trail called prod-audit with KMS encryption,
multi-region coverage, and Insights enabled. Use S3 bucket my-ct-logs.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Verify bucket | `aws s3api head-bucket --bucket my-ct-logs` | |
| 2. Check bucket policy | `aws s3api get-bucket-policy --bucket my-ct-logs` | Must allow CloudTrail writes |
| 3. Create trail | `aws cloudtrail create-trail --is-multi-region-trail --kms-key-id` | |
| 4. Put event selectors | `aws cloudtrail put-event-selectors --trail-name prod-audit` | |
| 5. Start logging | `aws cloudtrail start-logging --name prod-audit` | |
| 6. Poll IsLogging | `aws cloudtrail get-trail-status --name prod-audit` | max 5 min |

---

## Scenario 2: Find who deleted an S3 object

### User Prompt
```
Who deleted the file backups/2024/q4.tar.gz from our S3 bucket data-backups-prod yesterday?
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Lookup events | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=S3ObjectKey,AttributeValue=backups/2024/q4.tar.gz` | |
| 2. Filter by time | `--start-time 2024-12-01T00:00:00Z --end-time 2024-12-02T00:00:00Z` | |
| 3. Check IAM user | If Username is present → `[MANUAL]` confirm with team | |
| 4. Check ARN | If ARN-based principal → cross-ref with aws-iam-ops | |

---

## Scenario 3: Investigate unusual API call spike

### User Prompt
```
Our CloudTrail shows an unusual spike in DescribeInstances calls.
Can you identify the source and what happened?
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Enable Insights | `aws cloudtrail put-insight-selectors --trail-name prod-audit --insight-selectors ApiCallRateInsight` | |
| 2. Query Insights | `aws cloudtrail lookup-events --event-category insight` | |
| 3. Identify source IP | Filter `lookup-events` for `DescribeInstances` + time range | |
| 4. Check CloudWatch | `aws cloudwatch get-metric-statistics` for API call rate | |
| 5. RCA output | Source IAM principal, time window, estimated call count | |

---

## Scenario 4: Stop and delete a trail (destructive)

### User Prompt
```
Stop logging on the dev-audit trail and then delete it.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Safety gate | `confirm=STOP_LOGGING dev-audit` | `[MANUAL]` |
| 2. Stop logging | `aws cloudtrail stop-logging --name dev-audit` | |
| 3. Verify stopped | `aws cloudtrail get-trail-status --name dev-audit` → IsLogging=false | |
| 4. Safety gate | `confirm=DELETE_TRAIL dev-audit` | `[MANUAL]` |
| 5. Delete trail | `aws cloudtrail delete-trail --name dev-audit` | |
| 6. Verify | `aws cloudtrail describe-trails --trail-name-list dev-audit` → TrailNotFound | |

---

## Scenario 5: Compliance audit — who changed IAM policies

### User Prompt
```
Show me all IAM policy changes (PutUserPolicy, PutRolePolicy, DeleteUserPolicy)
in the last 90 days that affected admin-level users.
```

### Agent Execution Flow
| Step | Action | Decision |
|------|--------|----------|
| 1. Lookup events | `aws cloudtrail lookup-events --event-name PutUserPolicy --event-name PutRolePolicy --event-name DeleteUserPolicy` | |
| 2. Filter by time | `--start-time <90d>` | |
| 3. Parse response | Username + EventTime + AWSRegion + SourceIPAddress | |
| 4. Cross-ref | `aws iam list-users` → identify admin users | |
| 5. Report | Table: Who, When, Where, What, SourceIP | |

---

## Quick Reference

| User says | Scenario | Decision | Modules |
|-----------|----------|----------|---------|
| "Create trail with KMS + multi-region" | Trail creation | `[AI_ASSIST]` | cloudtrail + kms |
| "Who deleted this S3 file" | Forensic lookup | `[AI_ASSIST]` | cloudtrail + s3 |
| "Unusual API spike" | Insights RCA | `[AI_ASSIST]` | cloudtrail + cloudwatch |
| "Stop and delete dev trail" | Trail deletion | `[MANUAL]` strong safety gate | cloudtrail |
| "IAM policy changes last 90 days" | Compliance audit | `[OBSERVE]` | cloudtrail + iam |
