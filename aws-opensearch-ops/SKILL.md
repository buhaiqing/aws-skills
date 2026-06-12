---
name: aws-opensearch-ops
description: >-
  Use when the user needs to create, manage, or delete Amazon OpenSearch
  Service domains; configure clusters, snapshots, VPC endpoints, or data
  ingestion pipelines; manage domain access policies, fine-grained access
  control, or advanced security options; upgrade OpenSearch versions; or
  perform domain recovery operations, even if they don't say "OpenSearch"
  and instead say "set up a search cluster", "create an Elasticsearch
  domain", "manage OpenSearch snapshots", "configure domain access",
  "set up ingestion pipeline", or "upgrade search cluster".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to OpenSearch Service endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-06-08"
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
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
---

## Common JSON Paths (Centralized)

```
# Domain Names:    .DomainNames[].{DomainName,EngineType}
# Domain Status:   .DomainStatus.{DomainId,DomainName,ARN,Endpoint,EngineVersion}
# Cluster Config:  .DomainStatus.ClusterConfig.{InstanceType,InstanceCount,DedicatedMasterEnabled}
# Access Policies: .DomainStatus.AccessPolicies
# Security:        .DomainStatus.AdvancedSecurityOptions.{Enabled,InternalUserDatabaseEnabled}
# VPC Options:     .DomainStatus.VPCOptions.{VPCId,SubnetIds,SecurityGroupIds}
# Snapshots:       .SnapshotList[].{SnapshotName,Status,ClusterName,Progress}
# VPC Endpoints:   .VpcEndpoints[].{VpcEndpointId,VpcEndpointOwner,DomainArn,Status}
# Pipelines:       .IngestionPipelineSummaries[].{PipelineName,PipelineArn,Status}
```

AWS OpenSearch Service operational skill for AI Agent automation.

## Trigger & Scope

### SHOULD Use When
- User mentions "OpenSearch", "OpenSearch Service", "Amazon OpenSearch"
- User requests domain creation, modification, or deletion
- User asks to create, restore, or manage domain snapshots
- User needs VPC endpoint setup or management for OpenSearch
- User requests data ingestion pipeline (OpenSearch Ingestion) operations
- User asks about domain access policies or fine-grained access control
- User needs cluster configuration updates or version upgrades
- Keywords: opensearch, elasticsearch, search cluster, domain, snapshot, ingestion, pipeline, access policy, fine-grained access control
- (AIOps) User reports slow queries, cluster yellow/red status, shard issues
- (AIOps) User asks for cost optimization or capacity forecast

### SHOULD NOT Use When
- IAM policies → delegate to: `aws-iam-ops`
- KMS encryption keys → delegate to: `aws-kms-ops`
- VPC networking → delegate to: `aws-vpc-ops`
- CloudWatch monitoring → delegate to: `aws-cloudwatch-ops`
- S3 for snapshot repository → delegate to: `aws-s3-ops`
- Kinesis for data streaming → not yet available in repo

### Delegation
- IAM roles/policies → `aws-iam-ops` | KMS keys → `aws-kms-ops`
- CloudWatch alarms → `aws-cloudwatch-ops` | S3 snapshot repo → `aws-s3-ops`

## Scope

| Operation | Safety Gate |
|-----------|-------------|
| Create/Modify Domain | Parameter validation |
| Delete Domain | **Human confirm** |
| Create/Delete Snapshot | Delete: human confirm |
| Create/Delete VPC Endpoint | Delete: human confirm |
| Create/Delete Ingestion Pipeline | Delete: human confirm |
| Update Domain Config | Parameter validation |
| Upgrade Domain | Human confirm |
| Add/Remove Tags | None |
| **Auto Heal Cluster** (red/yellow status) | AUTO_HEAL — automatic |
| **Diagnose Slow Query** | AI_ASSIST — recommend index/params |
| **Capacity Forecast** | AI_ASSIST — recommend scale |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.DomainName}}` | User input | Ask once; reuse |
| `{{user.EngineVersion}}` | User input | OpenSearch_X.Y or Elasticsearch_X.Y |
| `{{user.InstanceType}}` | User input | e.g., r6g.large.search |
| `{{output.DomainArn}}` | Last API response | Parse: `.DomainStatus.ARN` |
| `{{output.Endpoint}}` | Last API response | Parse: `.DomainStatus.Endpoint` |
| `{{output.DomainId}}` | Last API response | Parse: `.DomainStatus.DomainId` |

## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Credential verified. Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx`
On failure: `[FAIL] AWS credential verification failed. Action: Check .env`
```bash
# Verify engine version availability
aws opensearch list-domain-names --region {{env.AWS_DEFAULT_REGION}} --output json
```
Log: `[OK] OpenSearch API reachable in {{env.AWS_DEFAULT_REGION}}`

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md) for full command reference.

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

### Validate
```
1. Poll: aws opensearch describe-domain --domain-name {{user.DomainName}}
2. Wait for terminal state (Active/Processing/Deleted) — max 30 min create, 15 min delete
3. Optional: test endpoint via curl / OpenSearch client
```

### Recover
| Error Type | Action |
|------------|--------|
| AlreadyExists / InvalidState / QuotaExceeded | HALT |
| InvalidType | Retry with supported instance type |
| Throttling (429) | Exponential backoff, max 3 retries |
| 5xx Internal | Retry 3x; HALT |

## Safety Gates

### Domain Deletion
```
BEFORE delete-domain:
1. Display: "Deleting {{user.DomainName}} will permanently remove all data and indices"
2. Ask: "Type 'DELETE_DOMAIN {{user.DomainName}}' to confirm"
3. Pre-flight: describe-domain to confirm domain exists and is not in 'Creating' state
```

### Snapshot Deletion
```
BEFORE delete-snapshot:
1. Confirm with user: "Type 'DELETE_SNAPSHOT {{user.SnapshotName}} from {{user.DomainName}}' to confirm"
2. Pre-flight: list-snapshots to verify snapshot exists
```

### VPC Endpoint Deletion
```
BEFORE delete-vpc-endpoint:
1. Confirm with user: "Type 'DELETE_VPC_ENDPOINT {{user.VpcEndpointId}}' to confirm"
2. Pre-flight: describe-vpc-endpoints to verify endpoint exists
```

### Ingestion Pipeline Deletion
```
BEFORE delete-ingestion:
1. Confirm with user: "Type 'DELETE_INGESTION {{user.PipelineName}}' to confirm"
2. Pre-flight: describe-ingestion to verify pipeline exists and is not active
```

## Output Convention
All commands use `--output json`. Key JSON paths:
- `.DomainStatus.{DomainId,DomainName,ARN,Endpoint,EngineVersion,ClusterConfig,AccessPolicies,AdvancedSecurityOptions}`
- `.DomainNames[].{DomainName,EngineType}`
- `.SnapshotList[].{SnapshotName,Status,ClusterName}`
- `.VpcEndpoints[].{VpcEndpointId,VpcEndpointOwner,DomainArn}`
- `.IngestionPipelineSummaries[].{PipelineName,PipelineArn,Status}`

## Related Skills
- `aws-ec2-ops` — Security groups | `aws-iam-ops` — IAM roles | `aws-kms-ops` — Encryption
- `aws-cloudwatch-ops` — Alarms, logs | `aws-s3-ops` — Snapshot repository
- `aws-vpc-ops` — VPC endpoints, subnets

## Cross-Skill Orchestration
| Scenario | Chain |
|----------|-------|
| OpenSearch Performance RCA | opensearch → cloudwatch → ec2 (查指标 → 查底层 → 查安全组) |
| OpenSearch Security Audit | opensearch → iam → kms (访问策略 → 权限 → 加密) |
| OpenSearch Cost Optimization | opensearch → cloudwatch (查闲置 → 建议降配/预留) |
| OpenSearch Snapshot DR | opensearch → s3 (快照 → 跨区域复制) |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded engine versions/instance types — use `list-versions` / `describe-domain`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` block above
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — OpenSearch architecture, concepts
- `references/troubleshooting.md` — Error codes, recovery procedures
- `references/rubric.md` — GCL 5-dimension rubric
- `references/prompt-templates.md` — GCL Generator/Critic/Orchestrator prompts
- `assets/example-config.yaml` — Configuration examples

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-08, required). Every execution of
> `aws-opensearch-ops` MUST be wrapped by the Generator-Critic-Loop defined in
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

- `delete-domain` — `confirm=DELETE_DOMAIN <domain-name>`
- `delete-snapshot` — `confirm=DELETE_SNAPSHOT <snapshot-name> from <domain-name>`
- `delete-vpc-endpoint` — `confirm=DELETE_VPC_ENDPOINT <vpc-endpoint-id>`
- `delete-ingestion` — `confirm=DELETE_INGESTION <pipeline-name>`
- `upgrade-domain` — `confirm=UPGRADE_DOMAIN <domain-name> to <target-version>`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource echo-back),
A9 (no secrets in trace), A10 (sts first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.
