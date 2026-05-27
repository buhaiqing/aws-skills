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
---
# AWS RDS Ops Skill

AWS Relational Database Service (RDS) operational skill for AI Agent automation.

## Triggers

**SHOULD activate when:**
- User requests DB instance creation, modification, or deletion
- User asks to create, restore, or manage database snapshots
- User needs read replica setup or management
- User requests parameter group configuration
- User asks about Aurora cluster operations
- User mentions "RDS", "managed database", "MySQL/PostgreSQL on AWS", "Aurora"
- User needs database backup or recovery operations
- (AIOps) User reports slow database, connection issues, storage warning, backup compliance
- (AIOps) User asks for cost optimization or capacity forecast

**SHOULD-NOT activate when:**
- DynamoDB → `aws-dynamodb-ops` / ElastiCache → `aws-elasticache-ops` / Redshift → `aws-redshift-ops`
- EC2 self-managed DB / DocumentDB / Neptune

**Delegation:**
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
| **Capacity Forecast** | AI_ASSIST — recommend scale |
| **Backup Compliance Scan** | MANUAL — report findings |

## Variable Convention

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.*}}` | Environment | `AWS_ACCESS_KEY_ID`, `AWS_DEFAULT_REGION` |
| `{{user.*}}` | User input | `DBInstanceIdentifier`, `DBEngine`, `MasterUsername` |

**Never commit real credentials. Always use `{{env.*}}` or `{{user.*}}` placeholders.**

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

## Output Convention
All commands use `--output json`. Key JSON paths:
- `.DBInstances[0].{DBInstanceStatus,Endpoint.Address,Endpoint.Port,DBInstanceArn}`
- `.DBSnapshot.{DBSnapshotIdentifier,Status}`
- `.DBClusters[0].{Status,Endpoint,ReaderEndpoint}`

## Related Skills
- `aws-ec2-ops` — Security groups | `aws-iam-ops` — IAM roles | `aws-kms-ops` — Encryption
- `aws-cloudwatch-ops` — Performance Insights, alarms | `aws-s3-ops` — Import/export
- `aws-secrets-manager-ops` — Credential management

## Cross-Skill Orchestration
| Scenario | Chain |
|----------|-------|
| RDS Performance RCA | rds → cloudwatch → ec2 (查指标 → 查底层 → 查安全组) |
| RDS Cost Optimization | rds → cloudwatch (查闲置 → 建议降配/预留) |
| RDS Security Audit | rds → kms → iam → secretsmanager (加密 → 权限 → 凭据) |
| Layered Inspection | cloudwatch → elb/vpc → ec2/rds → eks — see [layered-inspection](references/layered-inspection-template.md) |

## AIOps Scenarios
See [references/prompt-examples.md](references/prompt-examples.md) for 10 concrete scenarios:
- Slow query RCA / Storage AUTO_HEAL / Connection surge diagnosis
- Backup compliance scan / Idle instance cleanup (FinOps)
- Cross-region DR / Parameter tuning / Aurora failover
- Cross-skill RCA / Capacity forecast

## Reference Files
- [Prompt Examples](references/prompt-examples.md) — 10 AIOps user prompts
- [Layered Inspection Template](references/layered-inspection-template.md) — Health check + RCA
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — RDS architecture, concepts
- `references/troubleshooting.md` — Error codes, recovery procedures
- `assets/example-config.yaml` — Configuration examples