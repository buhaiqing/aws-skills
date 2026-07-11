---
name: aws-rds-ops
description: >-
  Use when the user needs to create, manage, or delete managed relational
  databases in AWS (RDS); configure MySQL, PostgreSQL, MariaDB, Oracle, or
  Aurora clusters; set up Multi-AZ deployments for high availability; create
  or restore database snapshots; manage read replicas; configure parameter
  groups and option groups; set up automated backups; or perform database
  recovery operations, even if they don't say "RDS" and instead say "set up
  a managed database", "create a MySQL instance on AWS", "configure Aurora
  cluster", "manage database snapshots", "set up read replicas for my database",
  or "configure database failover".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to RDS endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-06-27"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'event']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

AWS Relational Database Service (RDS) operational skill for AI Agent automation.

## Common JSON Paths (Centralized)

```
# Describe:     .DBInstances[0].{DBInstanceStatus,Endpoint.Address,Endpoint.Port,DBInstanceClass,Engine,EngineVersion,DBInstanceArn,PerformanceInsightsEnabled,DbiResourceId}
# Create:       .DBInstance.{DBInstanceArn,DBInstanceStatus}
# Snapshot:     .DBSnapshot.{DBSnapshotIdentifier,Status}
# Cluster:      .DBClusters[0].{Status,Endpoint,ReaderEndpoint,DBClusterMembers[*].DBInstanceIdentifier}
# PI (top SQL): .MetricList[0].DataPoints[*].{Timestamp,Value}
# Versions:     .DBEngineVersions[0].{Engine,EngineVersion,DBParameterGroupFamily}
```

## Trigger & Scope

### SHOULD Use When
- User mentions "RDS", "Relational Database Service", "managed database"
- User requests DB instance creation, modification, or deletion
- User asks to create, restore, or manage database snapshots
- User needs read replica setup or management
- User requests parameter group configuration
- Keywords: database, mysql, postgresql, snapshot, replica, failover
- (AIOps) User reports slow database, connection issues, storage warning, backup compliance
- (AIOps) User asks for cost optimization or capacity forecast

### SHOULD NOT Use When
- Aurora cluster operations (failover, Global Database, Serverless v2, cluster snapshots) → `aws-aurora-ops`
- DynamoDB → delegate to: `aws-dynamodb-ops`
- ElastiCache → delegate to: `aws-elasticache-ops`
- EC2 self-managed DB / DocumentDB / Neptune

### Delegation
- Security groups → `aws-ec2-ops` | IAM roles → `aws-iam-ops` | KMS keys → `aws-kms-ops`
- CloudWatch alarms → `aws-cloudwatch-ops` | S3 backup → `aws-s3-ops`

## Scope

| Operation | Safety Gate |
|-----------|-------------|
| Create/Modify DB Instance | Parameter validation |
| Delete DB Instance | **Human confirm + final snapshot** |
| Create/Restore/Delete Snapshot | Delete: human confirm |
| Create/Promote Read Replica | None |
| Create/Modify/Delete Parameter Group | Delete: human confirm |
| Create/Delete Aurora Cluster | Delete: human confirm + snapshot |
| **Auto Heal Storage** (FreeStorage <10%) | AUTO_HEAL — automatic |
| **Diagnose Slow Query** | AI_ASSIST — recommend index/params |
| **Enable Performance Insights** | AUTO_HEAL — automated setup |
| **Capacity Forecast** | AI_ASSIST — recommend scale |
| **Backup Compliance Scan** | MANUAL — report findings |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.DBInstanceIdentifier}}` | User input | Ask once; reuse |
| `{{user.DBEngine}}` | User input | mysql, postgres, aurora-mysql, etc. |
| `{{user.MasterUsername}}` | User input | Ask once; reuse |
| `{{output.DBArn}}` | Last API response | Parse: `.DBInstance.DBInstanceArn` |
| `{{output.Endpoint}}` | Last API response | Parse: `.DBInstance.Endpoint.Address` |
| `{{user.query_duration_threshold}}` | User input | Slow query threshold in sec (default: 5) |
| `{{user.pi_metric_period}}` | User input | PI metric period in sec (default: 60) |

## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Credential verified. Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx`
On failure: `[FAIL] AWS credential verification failed. Action: Check .env`
```bash
# Verify region, engine, quota
aws rds describe-db-engine-versions --region {{env.AWS_DEFAULT_REGION}} --engine {{user.DBEngine}}
```
Log: `[OK] Engine {{user.DBEngine}} available in {{env.AWS_DEFAULT_REGION}}`

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md) for full command reference.

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

### Validate
```
1. Poll: aws rds describe-db-instances --db-instance-identifier {{user.DBInstanceIdentifier}}
2. Wait for terminal state (available/deleted) — max 30min create, 15min delete
3. Optional: test endpoint via nc/psql/mysql
```

### Recover
| Error Type | Action |
|------------|--------|
| AlreadyExists / InvalidState / QuotaExceeded | HALT |
| StorageTypeNotSupported | Retry gp2/gp3 |
| Throttling (429) | Exponential backoff, max 3 retries |
| 5xx Internal | Retry 3x; HALT |

## Safety Gates

### Database Deletion
```
BEFORE delete-db-instance:
1. Display: "Deleting {{user.DBInstanceIdentifier}} will permanently remove all data"
2. Ask: "Create final snapshot? (recommended)"
3. Ask: "Type 'DELETE {{user.DBInstanceIdentifier}}' to confirm"
```
### Snapshot / Parameter Group Deletion
```
BEFORE delete-db-snapshot / delete-db-parameter-group:
1. Confirm with user: "Type 'DELETE (SNAPSHOT|PG) {{name}}' to confirm"
2. PG precondition: No DB instances using this group
```

## SQL Slow Query Diagnosis

Workflow: detect → analyze → optimize SQL slow queries on RDS.
Detailed commands in [references/aws-cli-usage.md](references/aws-cli-usage.md) (CLI) and [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md) (SDK).

### Quick Reference

**1. Pre-flight:** Check PI enabled + slow query log published to CloudWatch.
```bash
aws rds describe-db-instances --db-instance-identifier "{{user.DBInstanceIdentifier}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json \
  | jq '{PI: .DBInstances[0].PerformanceInsightsEnabled, CW_Logs: .DBInstances[0].EnabledCloudwatchLogsExports}'```
If not enabled: `modify-db-instance --enable-performance-insights --performance-insights-retention-period 7`
If slow log not published: `modify-db-instance --cloudwatch-logs-export-configuration '{"EnableLogTypes":["slowquery"]}'`

**2. Get DbiResourceId** (required for PI API):
```bash
aws rds describe-db-instances --db-instance-identifier "{{user.DBInstanceIdentifier}}" \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json | jq -r '.DBInstances[0].DbiResourceId'```
Save as `{{output.dbi_resource_id}}`.

**3. PI: Top SQL + Wait Events (last 1h):**
```bash
# Top SQL by DB load
aws pi get-resource-metrics --service-type RDS --identifier "{{output.dbi_resource_id}}" \
  --start-time $(date -u -d '-1 hour' +%s) --end-time $(date -u +%s) --period-in-seconds 60 \
  --metric-queries '[{"Metric":"db.sproc_execution_time","GroupBy":{"Group":"db.sql_tokenized","Limit":10}}]' \
  --region "{{env.AWS_DEFAULT_REGION}}" --output json
# Wait events: same command with Group="db.wait_event"```

**4. Query slow query log from CloudWatch:**
```bash
LOG_GROUP="/aws/rds/instance/{{user.DBInstanceIdentifier}}/slowquery"  # MySQL
# For PostgreSQL: LOG_GROUP="/aws/rds/instance/{{user.DBInstanceIdentifier}}/postgresql"
aws logs start-query --log-group-name "$LOG_GROUP" \
  --start-time $(date -u -d '-1 hour' +%s) --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /(?i)(Query_time|# User@Host)/ | parse @message /Query_time: (?<query_time>\S+).*Lock_time: (?<lock_time>\S+).*Rows_sent: (?<rows_sent>\d+).*Rows_examined: (?<rows_examined>\d+)/ | sort query_time desc | limit 50'
```
Wait 5-30s, then `aws logs get-query-results --query-id "$QUERY_ID"`.

**5. Pattern analysis:**

| PI Signal | Log Pattern | Likely Root Cause | Fix |
|-----------|-------------|-------------------|-----|
| CPU high | `rows_examined >> rows_sent` | Missing index | `CREATE INDEX` |
| `Lock:RowLockWait` | High `Lock_time` | Lock contention | Shorten transactions; use NOWAIT |
| `IO:DataFileRead` | Buffer pool miss | Memory pressure | Increase `innodb_buffer_pool_size` |
| `IO:XactSync` | High commit time | Sync binlog | Batch commits |
| `tcp:connection` | `max_connections` hit | Connection leak | Increase max_connections; fix pool |
| Temp tables | `Created_tmp_disk_tables` > 0 | Sort exceeds tmp_table | Increase `tmp_table_size` |

**6. Apply fix & validate:
- Parameter tuning: `modify-db-parameter-group` (see [references/aws-cli-usage.md](references/aws-cli-usage.md))
- Re-run PI `get-resource-metrics` with `db.sproc_execution_time`, `db.cpu`, `db.io` — compare before/after.

**7. Escalate if no improvement:**

| Condition | Action |
|-----------|--------|
| No improvement | Scale instance class |
| IOPS saturated | io2 storage or scale |
| Read-heavy | Add read replica |
| Query unfixable | Rewrite query; add ElastiCache |

Full diagnoses tables in [references/troubleshooting.md](references/troubleshooting.md).


## Related Skills
- `aws-ec2-ops` — Security groups | `aws-iam-ops` — IAM roles | `aws-kms-ops` — Encryption
- `aws-cloudwatch-ops` — Performance Insights, alarms, **slow query log query** | `aws-s3-ops` — Import/export
- `aws-secretsmanager-ops` — Credential management

## Cross-Skill Orchestration
| Scenario | Chain |
|----------|-------|
| RDS Performance RCA | rds → cloudwatch → ec2 (查指标 → 查底层 → 查安全组) |
| RDS Slow Query Analysis | rds(pi) → cloudwatch(logs) → rds(optimize) (PI top SQL → 慢查询日志 → 参数调优) |
| RDS Cost Optimization | rds → cloudwatch (查闲置 → 建议降配/预留) |
| RDS Security Audit | rds → kms → iam → secretsmanager (加密 → 权限 → 凭据) |
| Layered Inspection | cloudwatch → elb/vpc → ec2/rds → eks — see [layered-inspection](references/layered-inspection-template.md) |

## AIOps Scenarios
See [references/prompt-examples.md](references/prompt-examples.md) for 10 concrete scenarios:
- Slow query RCA / Storage AUTO_HEAL / Connection surge diagnosis
- Backup compliance scan / Idle instance cleanup (FinOps)
- Cross-region DR / Parameter tuning → delegate **`aws-aurora-ops`** for Aurora failover
- Cross-skill RCA / Capacity forecast

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded engine versions/instance classes — use `describe-db-engine-versions` / `describe-orderable-db-instance-options`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block at file top
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files
- [Prompt Examples](references/prompt-examples.md) — 10 AIOps user prompts
- [Layered Inspection Template](references/layered-inspection-template.md) — Health check + RCA
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — RDS architecture, concepts
- `references/troubleshooting.md` — Error codes, recovery procedures
- `assets/example-config.yaml` — Configuration examples
## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-rds-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace
(exact format `confirm=<OPERATION> <resource>`):

- `delete-db-instance` / `delete-db-cluster` — default path requires
  `--final-db-snapshot-identifier`; `--skip-final-snapshot` needs
  literal `DELETE_NO_SNAPSHOT <db-id>` (rule A5)
- `delete-db-snapshot` / `delete-db-cluster-snapshot`
- `delete-db-parameter-group` / `delete-db-cluster-parameter-group` —
  must not be in use
- `delete-db-subnet-group` — must not be referenced
- `delete-event-subscription`
- `stop-db-instance` / `stop-db-cluster` (7-day window; reversible)
- `promote-read-replica` (cross-region needs stronger confirm)
- `modify-db-instance` with storage SHRINK

Relevant AWS rules from `gcl-spec.md` §8: A5 (final-snapshot guard),
A7 (region), A8 (resource echo-back), A9 (no passwords in trace),
A10 (sts first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.

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

