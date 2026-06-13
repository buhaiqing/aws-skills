---
name: incident-schema
version: "1.1.0"
parent: aws-aiops-cruise
status: mandatory
---

# Incident Schema — Standardized Finding Contract

All runbook outputs MUST emit findings conforming to this schema.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | UUID | Unique finding ID |
| `schema_version` | semver | e.g. `1.1.0` |
| `customer` | string | Scope label (RG name or tag value) |
| `timestamp` | ISO8601 | Finding time (UTC) |
| `run_id` | UUID | Parent patrol run |
| `level` | enum | `CRITICAL` / `WARNING` / `INFO` |
| `resource_type` | enum | `EC2` / `ALB` / `NLB` / `RDS` / `Aurora` / `RDSProxy` / `ElastiCache` / `NAT` / `EIP` / `VPC` / `SG` / `EKS` / `Lambda` / `OTHER` |
| `resource_id` | string | AWS resource identifier (cluster id, instance id, proxy name) |
| `region` | string | AWS region |
| `rule_id` | string | Inference or metric rule ID |
| `rule_version` | semver | Rule version |
| `title` | string | Human-readable summary |
| `dedup_key` | string | `{customer}:{resource_type}:{resource_id}:{rule_id}:{date}` |

## Conditional (metric-triggered)

| Field | Type |
|-------|------|
| `metric` | string |
| `current_value` | number |
| `threshold_warning` | number |
| `threshold_critical` | number |

## Optional (orchestrator / runbook)

| Field | Type | Description |
|-------|------|-------------|
| `runbook_id` | string | e.g. `RB-023` |
| `decision_tier` | enum | `AUTO_HEAL` / `AI_ASSIST` / `MANUAL` |
| `delegate_skill` | string | e.g. `aws-aurora-ops` |

## Required recommendation

| Field | Type |
|-------|------|
| `recommendation` | string — read-only patrol; link to delegated skill + runbook for fixes |

## Examples

### RDS instance — connection pressure

```json
{
  "incident_id": "550e8400-e29b-41d4-a716-446655440000",
  "schema_version": "1.1.0",
  "customer": "prod-web-rg",
  "timestamp": "2026-06-13T10:00:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "level": "WARNING",
  "resource_type": "RDS",
  "resource_id": "prod-db-01",
  "region": "us-east-1",
  "rule_id": "RDS-CONN-01",
  "rule_version": "1.0.0",
  "title": "RDS connection count elevated",
  "dedup_key": "prod-web-rg:RDS:prod-db-01:RDS-CONN-01:2026-06-13",
  "metric": "DatabaseConnections",
  "current_value": 420,
  "threshold_warning": 350,
  "threshold_critical": 480,
  "decision_tier": "AI_ASSIST",
  "delegate_skill": "aws-rds-ops",
  "runbook_id": "RB-010",
  "recommendation": "Review connection pooling; load aws-rds-ops for PI analysis"
}
```

### Aurora cluster — replica lag

```json
{
  "incident_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "schema_version": "1.1.0",
  "customer": "prod-web-rg",
  "timestamp": "2026-06-13T11:30:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "level": "WARNING",
  "resource_type": "Aurora",
  "resource_id": "prod-aurora-app",
  "region": "us-east-1",
  "rule_id": "AURORA-LAG-01",
  "rule_version": "1.0.0",
  "title": "Aurora replica lag elevated",
  "dedup_key": "prod-web-rg:Aurora:prod-aurora-app:AURORA-LAG-01:2026-06-13",
  "metric": "AuroraReplicaLag",
  "current_value": 8500,
  "threshold_warning": 1000,
  "threshold_critical": 30000,
  "decision_tier": "AI_ASSIST",
  "delegate_skill": "aws-aurora-ops",
  "runbook_id": "RB-023",
  "recommendation": "PI top SQL on writer; add reader or scale writer — aws-aurora-ops RB-023"
}
```

### Aurora Serverless v2 — ACU at ceiling

```json
{
  "incident_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.1.0",
  "customer": "analytics-rg",
  "timestamp": "2026-06-13T14:00:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "level": "CRITICAL",
  "resource_type": "Aurora",
  "resource_id": "analytics-serverless",
  "region": "us-east-1",
  "rule_id": "AURORA-SLV2-01",
  "rule_version": "1.0.0",
  "title": "Aurora Serverless v2 capacity at configured max",
  "dedup_key": "analytics-rg:Aurora:analytics-serverless:AURORA-SLV2-01:2026-06-13",
  "metric": "ServerlessDatabaseCapacity",
  "current_value": 15.2,
  "threshold_warning": 12.8,
  "threshold_critical": 15.0,
  "decision_tier": "AUTO_HEAL",
  "delegate_skill": "aws-aurora-ops",
  "runbook_id": "RB-024",
  "recommendation": "Raise MaxCapacity (≤ ceiling); aws-aurora-ops modify-db-cluster Serverless v2"
}
```

### RDS Proxy → Aurora — connection storm

```json
{
  "incident_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "schema_version": "1.1.0",
  "customer": "prod-web-rg",
  "timestamp": "2026-06-13T16:45:00Z",
  "run_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "level": "CRITICAL",
  "resource_type": "Aurora",
  "resource_id": "prod-aurora-catalog",
  "region": "us-east-1",
  "rule_id": "RDS-PROXY-AURORA-02",
  "rule_version": "1.0.0",
  "title": "Aurora cluster connections high via RDS Proxy prod-proxy",
  "dedup_key": "prod-web-rg:Aurora:prod-aurora-catalog:RDS-PROXY-AURORA-02:2026-06-13",
  "metric": "DatabaseConnections",
  "current_value": 1850,
  "threshold_warning": 1600,
  "threshold_critical": 1900,
  "decision_tier": "AI_ASSIST",
  "delegate_skill": "aws-aurora-ops",
  "runbook_id": "RB-027",
  "recommendation": "Tune proxy pool + max_connections; aws-aurora-ops RB-027; runbook 06"
}
```
