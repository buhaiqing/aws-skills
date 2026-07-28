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
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'state', 'finding']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS OpenSearch Operations Skill

Use for OpenSearch domains, clusters, snapshots, VPC endpoints, ingestion pipelines, upgrades, health, slow-query diagnosis, capacity, cost, and AIOps remediation. Detailed commands remain in references.

## Common JSON Paths

Domain: .DomainStatus.{DomainId,DomainName,ARN,Endpoint,EngineVersion,ClusterConfig,AccessPolicies,AdvancedSecurityOptions}
Domains: .DomainNames[].{DomainName,EngineType}
Snapshots: .SnapshotList[].{SnapshotName,Status,ClusterName}
VpcEndpoints: .VpcEndpoints[].{VpcEndpointId,VpcEndpointOwner,DomainArn}
Pipelines: .IngestionPipelineSummaries[].{PipelineName,PipelineArn,Status}

## Trigger & Scope

### SHOULD Use When
OpenSearch/Elasticsearch domains, cluster health, shards, slow queries, snapshots, VPC endpoints, ingestion pipelines, upgrades, capacity, or cost diagnosis.

### SHOULD NOT Use When
EC2/security groups → `aws-ec2-ops`; IAM access → `aws-iam-ops`; KMS → `aws-kms-ops`; alarms → `aws-cloudwatch-ops`; S3 repositories → `aws-s3-ops`.

### Delegation
Networking → `aws-vpc-ops`; metrics → `aws-cloudwatch-ops`; IAM/KMS/S3 operations → their respective skills.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.DomainName}}`, `{{user.EngineVersion}}`, `{{user.InstanceType}}` | User input | Domain configuration |
| `{{user.SnapshotName}}`, `{{user.VpcEndpointId}}`, `{{user.PipelineName}}` | User input | Dependent resources |
| `{{output.*}}` | API response | Reuse domain ARN, endpoint, and ID |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify identity, domain status, supported engine/type, dependencies, snapshots, endpoints, and pipelines. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll domain/snapshot/pipeline state; recover with bounded throttling retries and halt on invalid state, quota, or ambiguous identity. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/modify domain | Validate engine/type, VPC, access policy, encryption; poll active | Token for high-impact topology/access changes |
| Upgrade domain | Verify supported target and upgrade eligibility | `UPGRADE_DOMAIN <name> to <version>` |
| Delete domain | Display permanent index/data loss; describe current state | `DELETE_DOMAIN <name>` |
| Delete snapshot | Verify snapshot and recovery need | `DELETE_SNAPSHOT <snapshot> from <domain>` |
| Delete VPC endpoint | Describe endpoint/domain users | `DELETE_VPC_ENDPOINT <id>` |
| Delete ingestion pipeline | Verify pipeline is not active and inspect consumers | `DELETE_INGESTION <name>` |
| Auto-heal/diagnose | Collect health, shards, metrics; AUTO_HEAL only non-destructive | Tier/token rules below |

Mask credentials, access-policy secrets, auth headers, query bodies, and sensitive index data in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live engine/type support, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md) · [example-config.yaml](assets/example-config.yaml)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive, upgrade, or high-impact topology actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
