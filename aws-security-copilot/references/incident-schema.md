---
name: incident-schema
version: "1.1.0"
parent: aws-security-copilot
status: mandatory
---

# Security Incident Schema — Standardized Finding Contract

Aligns with `aws-aiops-cruise` incident-schema v1.1.0. All security findings
MUST emit incidents conforming to this schema.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | UUID | Unique finding ID |
| `schema_version` | semver | `1.1.0` |
| `customer` | string | Scope label (resource group or tag) |
| `timestamp` | ISO8601 | Finding time (UTC) |
| `run_id` | UUID | Parent security scan run |
| `level` | enum | `CRITICAL` / `WARNING` / `INFO` |
| `resource_type` | enum | `EC2` / `S3` / `RDS` / `IAM` / `Lambda` / `KMS` / `SecretsManager` / `VPC` / `SG` / `OTHER` |
| `resource_id` | string | AWS resource identifier |
| `region` | string | AWS region |
| `rule_id` | string | Security rule ID (e.g. `SEC-F01`, `SEC-CRED-001`) |
| `rule_version` | semver | Rule version |
| `title` | string | Human-readable summary |
| `dedup_key` | string | `{customer}:{resource_type}:{resource_id}:{rule_id}:{date}` |

## Security-Specific Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | enum | `guardduty` / `securityhub` / `config` / `iam-analyzer` / `secretsmanager` / `kms` / `cloudtrail` |
| `finding_type` | string | Finding type ID from [`findings-matrix.md`](findings-matrix.md) (e.g. `F01-CRED-EXPOSED`) |
| `affected_resources` | array | List of affected resource IDs |
| `remediation` | object | See Remediation Object below |

## Conditional (metric-triggered)

| Field | Type |
|-------|------|
| `metric` | string |
| `current_value` | number |
| `threshold_warning` | number |
| `threshold_critical` | number |

## Remediation Object

```json
"remediation": {
  "skill": "aws-xxx-ops",
  "action": "operation-name",
  "requires_confirmation": true,
  "auto_approvable": false
}
```

- `requires_confirmation: true` — required for all HIGH/CRITICAL findings.
- `auto_approvable: true` — only for MEDIUM/LOW findings with pre-approved playbooks.

## Optional

| Field | Type | Description |
|-------|------|-------------|
| `runbook_id` | string | e.g. `RB-SEC-001` |
| `decision_tier` | enum | `HALT` (CRITICAL) / `MANUAL` (HIGH) / `AUTO_HEAL` (MEDIUM/LOW) |
| `delegate_skill` | string | e.g. `aws-iam-ops` |
| `recommendation` | string | Read-only patrol; link to delegated skill for fixes |

## Decision Tier Mapping

| Finding Level | Decision Tier | Behavior |
|---------------|---------------|----------|
| CRITICAL | `HALT` | Stop immediately; alert; require explicit user confirmation |
| HIGH | `MANUAL` | Log; require confirmation before any remediation |
| MEDIUM | `AUTO_HEAL` | Log; auto-remediate if pre-approved playbook exists |
| LOW | `AUTO_HEAL` | Log only; no immediate action |

## Examples

### Exposed credentials (CRITICAL)

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440001",
  "schema_version": "1.1.0",
  "customer": "prod-web-rg",
  "timestamp": "2026-07-19T10:00:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "level": "CRITICAL",
  "resource_type": "IAM",
  "resource_id": "AKIAXXXXXXXXXXXXXX",
  "region": "us-east-1",
  "rule_id": "SEC-F01",
  "rule_version": "1.0.0",
  "title": "Exposed AWS access key detected",
  "dedup_key": "prod-web-rg:IAM:AKIAXXXXXXXXXXXXXX:SEC-F01:2026-07-19",
  "source": "guardduty",
  "finding_type": "F01-CRED-EXPOSED",
  "affected_resources": ["AKIAXXXXXXXXXXXXXX"],
  "decision_tier": "HALT",
  "delegate_skill": "aws-iam-ops",
  "runbook_id": "RB-SEC-001",
  "recommendation": "Rotate key immediately via aws-iam-ops; user confirmation required"
}
```

### Open SSH to 0.0.0.0/0 (HIGH)

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440002",
  "schema_version": "1.1.0",
  "customer": "prod-web-rg",
  "timestamp": "2026-07-19T10:05:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "level": "WARNING",
  "resource_type": "SG",
  "resource_id": "sg-0123456789abcdef0",
  "region": "us-east-1",
  "rule_id": "SEC-F02",
  "rule_version": "1.0.0",
  "title": "Port 22 open to 0.0.0.0/0",
  "dedup_key": "prod-web-rg:SG:sg-0123456789abcdef0:SEC-F02:2026-07-19",
  "source": "config",
  "finding_type": "F02-NET-OPEN-PORT",
  "affected_resources": ["sg-0123456789abcdef0"],
  "remediation": {
    "skill": "aws-vpc-ops",
    "action": "restrict-sg",
    "requires_confirmation": true,
    "auto_approvable": false
  },
  "decision_tier": "MANUAL",
  "delegate_skill": "aws-vpc-ops",
  "recommendation": "Restrict SG ingress to known IP ranges; delegate to aws-vpc-ops"
}
```

### S3 public access (CRITICAL)

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440003",
  "schema_version": "1.1.0",
  "customer": "prod-web-rg",
  "timestamp": "2026-07-19T10:10:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "level": "CRITICAL",
  "resource_type": "S3",
  "resource_id": "arn:aws:s3:::prod-data-bucket",
  "region": "us-east-1",
  "rule_id": "SEC-F08",
  "rule_version": "1.0.0",
  "title": "S3 bucket has public access enabled",
  "dedup_key": "prod-web-rg:S3:arn:aws:s3:::prod-data-bucket:SEC-F08:2026-07-19",
  "source": "config",
  "finding_type": "F08-S3-PUBLIC",
  "affected_resources": ["arn:aws:s3:::prod-data-bucket"],
  "remediation": {
    "skill": "aws-s3-ops",
    "action": "remove-public",
    "requires_confirmation": true,
    "auto_approvable": false
  },
  "decision_tier": "HALT",
  "delegate_skill": "aws-s3-ops",
  "recommendation": "Block public access via bucket settings; delegate to aws-s3-ops"
}
```
