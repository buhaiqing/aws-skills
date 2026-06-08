# AWS OpenSearch, GuardDuty, Security Hub Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create three complete AWS operational skills (`aws-opensearch-ops`, `aws-guardduty-ops`, `aws-securityhub-ops`) with full GCL scaffolding, following the exact repository patterns established by the EC2, IAM, KMS, and S3 pilot skills.

**Architecture:** Each skill follows the canonical `aws-<service>-ops/` directory layout with `SKILL.md`, `references/` (aws-cli-usage.md, boto3-sdk-usage.md, core-concepts.md, troubleshooting.md, rubric.md, prompt-templates.md), and `assets/` (example-config.yaml). All three have destructive operations and require full GCL scaffolding per `AGENTS.md` §11.5. `aws-securityhub-ops` already has a `SKILL.md` (v1.0.0) but is missing all `references/` files and `assets/`.

**Tech Stack:** Markdown, YAML frontmatter, AWS CLI v2, boto3 SDK, GCL (Generator-Critic-Loop)

---

## File Structure

### Skill 1: `aws-opensearch-ops/` (NEW — empty shell exists)

| File | Responsibility |
|------|---------------|
| `SKILL.md` | Frontmatter, Trigger & Scope, Variable Convention, Execution Flow, Safety Gates, Output Convention, Quality Gate (GCL) |
| `references/aws-cli-usage.md` | OpenSearch CLI commands, JSON paths, common patterns |
| `references/boto3-sdk-usage.md` | boto3 `opensearch` client patterns, error handling, polling |
| `references/core-concepts.md` | OpenSearch Service architecture, instance types, quotas, dependencies |
| `references/troubleshooting.md` | Compact error tables, diagnostic flows |
| `references/rubric.md` | GCL 5-dimension rubric + operation-specific overrides + Safety special cases |
| `references/prompt-templates.md` | Generator / Critic / Orchestrator prompt skeletons |
| `assets/example-config.yaml` | Domain config, access policy, snapshot config with YAML anchors |

### Skill 2: `aws-guardduty-ops/` (NEW — empty shell exists)

| File | Responsibility |
|------|---------------|
| `SKILL.md` | Frontmatter, Trigger & Scope, Variable Convention, Execution Flow, Safety Gates, Output Convention, Quality Gate (GCL) |
| `references/aws-cli-usage.md` | GuardDuty CLI commands, JSON paths, common patterns |
| `references/boto3-sdk-usage.md` | boto3 `guardduty` client patterns, error handling, polling |
| `references/core-concepts.md` | GuardDuty architecture, finding types, detector lifecycle, quotas |
| `references/troubleshooting.md` | Compact error tables, diagnostic flows |
| `references/rubric.md` | GCL 5-dimension rubric + operation-specific overrides + Safety special cases |
| `references/prompt-templates.md` | Generator / Critic / Orchestrator prompt skeletons |
| `assets/example-config.yaml` | Detector config, filter rules, IP set / threat intel set config with YAML anchors |

### Skill 3: `aws-securityhub-ops/` (PARTIAL — SKILL.md exists, all references missing)

| File | Responsibility |
|------|---------------|
| `SKILL.md` | **MODIFY** — add missing `## Quality Gate (GCL)` section, update version to 1.1.0, add `metadata.gcl` block to frontmatter |
| `references/aws-cli-usage.md` | Security Hub CLI commands, JSON paths, common patterns |
| `references/boto3-sdk-usage.md` | boto3 `securityhub` client patterns, error handling, polling |
| `references/core-concepts.md` | Security Hub architecture, standards/controls, findings, quotas |
| `references/troubleshooting.md` | Compact error tables, diagnostic flows |
| `references/rubric.md` | GCL 5-dimension rubric + operation-specific overrides + Safety special cases |
| `references/prompt-templates.md` | Generator / Critic / Orchestrator prompt skeletons |
| `assets/example-config.yaml` | Hub config, insight config, automation rule config with YAML anchors |

### README Updates

| File | Responsibility |
|------|---------------|
| `README.md` | Add three new skills to "Existing Skills" table, update AIOps section |
| `README_cn.md` | Sync with English README changes |

---

## Task 1: Create `aws-opensearch-ops/SKILL.md`

**Files:**
- Create: `aws-opensearch-ops/SKILL.md`

- [ ] **Step 1: Write YAML frontmatter with `metadata.gcl` block**

```yaml
---
name: aws-opensearch-ops
description: >-
  Use when the user needs to manage Amazon OpenSearch Service resources:
  create, update, or delete OpenSearch domains; configure domain access
  policies; manage VPC endpoints; create, restore, or delete manual and
  automated snapshots; scale cluster instances or storage; configure
  advanced security, encryption, and fine-grained access control. Also
  use for OpenSearch operational tasks such as cluster health monitoring,
  index management, blue/green deployment tracking, or domain version
  upgrades.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials,
  network access to OpenSearch endpoints.
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
```

**CRITICAL:** Exactly two `---` markers. `description: >-` folded scalar must end with a blank line, NOT a `---` line. Verify with:
```bash
awk '/^---$/{c++; if(c==2){exit}} c==1' aws-opensearch-ops/SKILL.md
```

- [ ] **Step 2: Write `## Trigger & Scope` section with SHOULD/SHOULD NOT**

```markdown
## Trigger & Scope

### SHOULD Use When
- User mentions "OpenSearch", "Elasticsearch", "OpenSearch Service", "managed Elasticsearch"
- User requests create, update, or delete an OpenSearch domain
- User asks to configure domain access policies or fine-grained access control
- User needs snapshot management (create, restore, delete manual snapshots)
- User requests cluster scaling (instance type, count, storage)
- User asks for domain version upgrade or blue/green deployment status
- User needs VPC endpoint creation or deletion for OpenSearch
- User mentions index management, cluster health, or shard allocation
- Keywords: opensearch, elasticsearch, domain, snapshot, cluster, index, shard, access policy, fgac

### SHOULD NOT Use When
- IAM policy changes for OpenSearch access → delegate to: `aws-iam-ops`
- KMS encryption key operations → delegate to: `aws-kms-ops`
- VPC / subnet / security group changes → delegate to: `aws-vpc-ops`
- CloudWatch alarms for OpenSearch metrics → delegate to: `aws-cloudwatch-ops`
- S3 bucket operations for snapshot repository → delegate to: `aws-s3-ops`
- Direct OpenSearch REST API calls (index CRUD, search, ingest) → out of scope; use OpenSearch client directly

### Delegation
- IAM roles/policies → `aws-iam-ops` | KMS keys → `aws-kms-ops`
- VPC / Security Groups → `aws-vpc-ops` | CloudWatch → `aws-cloudwatch-ops`
- S3 snapshot repository → `aws-s3-ops`
```

- [ ] **Step 3: Write `## Scope` table with Safety Gate column**

```markdown
## Scope

| Operation | Safety Gate |
|-----------|-------------|
| Create/Update/Delete Domain | Delete: human confirm |
| Update Domain Config (scaling, version) | Update: human confirm |
| Create/Delete VPC Endpoint | Delete: human confirm |
| Create/Restore/Delete Snapshot | Delete/Restore: human confirm |
| Update Domain Access Policy | Update: human confirm |
| Enable/Disable Fine-Grained Access Control | Disable: human confirm |
| Describe Domain / List Domains | None |
| Describe Domain Health / Cluster Health | None |
| List Snapshots / Describe Snapshot | None |
| List VPC Endpoints | None |
```

- [ ] **Step 4: Write `## Variable Convention` table**

```markdown
## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.domain_name}}` | User input | Ask once; reuse |
| `{{user.snapshot_name}}` | User input | Ask once; reuse |
| `{{user.vpc_endpoint_id}}` | User input | Ask once; reuse |
| `{{user.engine_version}}` | User input | Ask once; reuse |
| `{{output.DomainName}}` | Last API response | Parse: `.DomainStatus.DomainName` |
| `{{output.DomainId}}` | Last API response | Parse: `.DomainStatus.DomainId` |
| `{{output.Endpoint}}` | Last API response | Parse: `.DomainStatus.Endpoint` |
| `{{output.ARN}}` | Last API response | Parse: `.DomainStatus.ARN` |
```

- [ ] **Step 5: Write `## Execution Flow` section (Pre-flight → Execute → Validate → Recover)**

```markdown
## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Credential verified. Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx`
On failure: `[FAIL] AWS credential verification failed. Action: Check .env`
```bash
# Verify OpenSearch is available in region
aws opensearch list-domain-names --region {{env.AWS_DEFAULT_REGION}} --output json
```
Log: `[OK] OpenSearch available in {{env.AWS_DEFAULT_REGION}}`

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md) for full command reference.

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md).

### Validate
```
1. Poll: aws opensearch describe-domain --domain-name {{user.domain_name}}
2. Verify state matches expected (Created/Processing/Active/Deleted)
3. For snapshots: confirm snapshot status is SUCCESSFUL or FAILED
```

### Recover
| Error Type | Action |
|------------|--------|
| ResourceNotFoundException | HALT — verify domain name |
| InvalidTypeException | HALT — check instance type availability |
| LimitExceededException | HALT — request quota increase |
| ThrottlingException (429) | Exponential backoff, max 3 retries |
| InternalException (5xx) | Retry 3x; HALT |
| SnapshotInProgressException | Wait; retry after current snapshot completes |
```

- [ ] **Step 6: Write `## Safety Gates` section with exact confirmation strings**

```markdown
## Safety Gates

### Delete Domain
```
BEFORE delete-domain:
1. Display: "Deleting domain {{user.domain_name}} will permanently remove all data, indices, and snapshots stored in this domain. This action is IRREVERSIBLE."
2. Ask: "Type 'DELETE_DOMAIN {{user.domain_name}}' to confirm"
```

### Update Domain Config (Destructive Changes)
```
BEFORE update-domain-config with instance count/type reduction OR version downgrade:
1. Display: "Reducing cluster capacity or downgrading version may cause data loss or service interruption for {{user.domain_name}}"
2. Ask: "Type 'UPDATE_DOMAIN {{user.domain_name}}' to confirm"
```

### Delete Snapshot
```
BEFORE delete-snapshot:
1. Display: "Deleting snapshot {{user.snapshot_name}} will permanently remove this backup"
2. Ask: "Type 'DELETE_SNAPSHOT {{user.snapshot_name}}' to confirm"
```

### Restore Snapshot
```
BEFORE restore-snapshot:
1. Display: "Restoring snapshot {{user.snapshot_name}} to domain {{user.domain_name}} will overwrite existing indices"
2. Ask: "Type 'RESTORE_SNAPSHOT {{user.snapshot_name}} TO {{user.domain_name}}' to confirm"
```

### Delete VPC Endpoint
```
BEFORE delete-vpc-endpoint:
1. Display: "Deleting VPC endpoint {{user.vpc_endpoint_id}} will break private connectivity to the domain"
2. Ask: "Type 'DELETE_VPC_ENDPOINT {{user.vpc_endpoint_id}}' to confirm"
```
```

- [ ] **Step 7: Write `## Output Convention` section with centralized JSON paths**

```markdown
## Output Convention
All commands use `--output json`. Key JSON paths:
- `.DomainStatus.{DomainName,DomainId,ARN,Endpoint,Endpoints,EngineVersion,ClusterConfig,AccessPolicies,SnapshotOptions,VPCOptions}`
- `.DomainStatus.ClusterConfig.{InstanceType,InstanceCount,DedicatedMasterEnabled,DedicatedMasterType,DedicatedMasterCount,ZoneAwarenessEnabled,ZoneAwarenessConfig}`
- `.DomainStatus.{Created,Deleted,Processing,UpgradeProcessing}`
- `.DomainNames[].{DomainName,EngineType}`
- `.Snapshots[].{SnapshotName,Status,StartTime,EndTime,SnapshotType,EngineVersion}`
- `.VPCEndpoints[].{VPCEndpointId,DomainArn,VPCId,Status,Endpoint}`
```

- [ ] **Step 8: Write `## Related Skills`, `## Cross-Skill Orchestration`, `## Reference Files`**

```markdown
## Related Skills
- `aws-iam-ops` — IAM policies and roles | `aws-kms-ops` — Encryption keys
- `aws-vpc-ops` — VPC, subnets, security groups | `aws-cloudwatch-ops` — Alarms and metrics
- `aws-s3-ops` — S3 snapshot repository | `aws-elb-ops` — Load balancer for OpenSearch

## Cross-Skill Orchestration

| Scenario | Chain |
|----------|-------|
| OpenSearch + VPC | opensearch → vpc (create VPC endpoint for private access) |
| OpenSearch + IAM | opensearch → iam (fine-grained access control requires IAM roles) |
| OpenSearch + KMS | opensearch → kms (at-rest encryption requires KMS CMK) |
| OpenSearch + S3 | opensearch → s3 (snapshot repository is an S3 bucket) |
| OpenSearch + CloudWatch | opensearch → cloudwatch (monitoring and alarms) |

## Reference Files
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — OpenSearch Service architecture, concepts
- `references/troubleshooting.md` — Error codes, recovery procedures
- `references/rubric.md` — GCL 5-dimension rubric
- `references/prompt-templates.md` — G/C/O prompt skeletons
- `assets/example-config.yaml` — Configuration examples
```

- [ ] **Step 9: Write `## Quality Gate (GCL)` section**

```markdown
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

- `delete-domain` — `confirm=DELETE_DOMAIN {{user.domain_name}}`
- `update-domain-config` (reduction/downgrade) — `confirm=UPDATE_DOMAIN {{user.domain_name}}`
- `delete-snapshot` — `confirm=DELETE_SNAPSHOT {{user.snapshot_name}}`
- `restore-snapshot` — `confirm=RESTORE_SNAPSHOT {{user.snapshot_name}} TO {{user.domain_name}}`
- `delete-vpc-endpoint` — `confirm=DELETE_VPC_ENDPOINT {{user.vpc_endpoint_id}}`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource echo-back),
A9 (no secrets in trace), A10 (sts first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.
```

- [ ] **Step 10: Verify frontmatter parses correctly**

Run:
```bash
python3 -c "import yaml,re; yaml.safe_load(re.search(r'^---\n(.*?)\n---', open('aws-opensearch-ops/SKILL.md').read(), re.DOTALL).group(1))"
```
Expected: No error, `gcl` block visible.

---

## Task 2: Create `aws-opensearch-ops/references/aws-cli-usage.md`

**Files:**
- Create: `aws-opensearch-ops/references/aws-cli-usage.md`

- [ ] **Step 1: Write Common JSON Paths block (file-top, centralized per TE-4)**

```markdown
# AWS CLI Usage — OpenSearch Service

## Common JSON Paths (Centralized)

```
# Create/Describe Domain: .DomainStatus.{DomainName,DomainId,ARN,Endpoint,EngineVersion,ClusterConfig,AccessPolicies}
# List Domains:           .DomainNames[].{DomainName,EngineType}
# Describe Health:        .DomainStatus.{Health,Processing,UpgradeProcessing}
# Create Snapshot:        .SnapshotDetail.{SnapshotName,Status,StartTime}
# List Snapshots:         .Snapshots[].{SnapshotName,Status,SnapshotType,EngineVersion}
# Describe VPC Endpoint:  .VPCEndpoint.{VPCEndpointId,DomainArn,VPCId,Status,Endpoint}
# List VPC Endpoints:     .VPCEndpoints[].{VPCEndpointId,DomainArn,Status}
```
```

- [ ] **Step 2: Write Command Map table**

```markdown
## Command Map

| Goal | CLI Command |
|------|-------------|
| Create domain | `aws opensearch create-domain` |
| Describe domain | `aws opensearch describe-domain` |
| Update domain config | `aws opensearch update-domain-config` |
| Delete domain | `aws opensearch delete-domain` |
| List domains | `aws opensearch list-domain-names` |
| Create snapshot | `aws opensearch create-snapshot` |
| Restore snapshot | `aws opensearch restore-snapshot` |
| Delete snapshot | `aws opensearch delete-snapshot` |
| List snapshots | `aws opensearch list-snapshots` |
| Create VPC endpoint | `aws opensearch create-vpc-endpoint` |
| Delete VPC endpoint | `aws opensearch delete-vpc-endpoint` |
| Describe VPC endpoint | `aws opensearch describe-vpc-endpoints` |
```

- [ ] **Step 3: Write Key CLI Conventions and Common Patterns**

```markdown
## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Region
Pass `--region` or rely on `AWS_DEFAULT_REGION`. OpenSearch domains are regional.

## Common Patterns

### Create Domain (Full Example)
```bash
aws opensearch create-domain \
  --domain-name "{{user.domain_name}}" \
  --engine-version "OpenSearch_2.11" \
  --cluster-config 'InstanceType=t3.small.search,InstanceCount=2' \
  --ebs-options 'EBSEnabled=true,VolumeType=gp3,VolumeSize=10' \
  --access-policies '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"*"},"Action":"es:*","Resource":"*"}]}' \
  --region "{{user.region}}" \
  --output json
```

### Describe Domain
```bash
aws opensearch describe-domain \
  --domain-name "{{user.domain_name}}" \
  --region "{{user.region}}" \
  --output json
```

### Update Domain Config (Scale)
```bash
aws opensearch update-domain-config \
  --domain-name "{{user.domain_name}}" \
  --cluster-config 'InstanceType=t3.medium.search,InstanceCount=3' \
  --region "{{user.region}}" \
  --output json
```

### Delete Domain
```bash
aws opensearch delete-domain \
  --domain-name "{{user.domain_name}}" \
  --region "{{user.region}}" \
  --output json
```

### Create Snapshot
```bash
aws opensearch create-snapshot \
  --domain-name "{{user.domain_name}}" \
  --snapshot-name "{{user.snapshot_name}}" \
  --region "{{user.region}}" \
  --output json
```

### List Snapshots
```bash
aws opensearch list-snapshots \
  --domain-name "{{user.domain_name}}" \
  --region "{{user.region}}" \
  --output json
```

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```

## Retry Strategy (CLI)

CLI has built-in retry logic. Configure in `~/.aws/config`:
```ini
[default]
retry_mode = adaptive
max_attempts = 3
```
```

---

## Task 3: Create `aws-opensearch-ops/references/boto3-sdk-usage.md`

**Files:**
- Create: `aws-opensearch-ops/references/boto3-sdk-usage.md`

- [ ] **Step 1: Write Client Initialization and Operation Patterns (no docstrings per TE-2)**

```markdown
# boto3 SDK Usage — OpenSearch Service

## Client Initialization

```python
import boto3
import os

client = boto3.client(
    'opensearch',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)
```

## Operation Patterns

### Create Domain

```python
response = client.create_domain(
    DomainName='{{user.domain_name}}',
    EngineVersion='OpenSearch_2.11',
    ClusterConfig={
        'InstanceType': 't3.small.search',
        'InstanceCount': 2,
        'DedicatedMasterEnabled': False,
        'ZoneAwarenessEnabled': False
    },
    EBSOptions={
        'EBSEnabled': True,
        'VolumeType': 'gp3',
        'VolumeSize': 10
    },
    AccessPolicies='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"*"},"Action":"es:*","Resource":"*"}]}'
)
domain_name = response['DomainStatus']['DomainName']
print(f"Creating: {domain_name}")
```

### Describe Domain

```python
response = client.describe_domain(DomainName='{{user.domain_name}}')
status = response['DomainStatus']
print(f"State: Processing={status.get('Processing')}, Created={status.get('Created')}")
print(f"Endpoint: {status.get('Endpoint')}")
```

### List Domains

```python
response = client.list_domain_names()
for domain in response['DomainNames']:
    print(f"{domain['DomainName']} ({domain.get('EngineType', 'OpenSearch')})")
```

### Update Domain Config

```python
response = client.update_domain_config(
    DomainName='{{user.domain_name}}',
    ClusterConfig={
        'InstanceType': 't3.medium.search',
        'InstanceCount': 3
    }
)
print(f"Updating: {response['DomainConfig']['ClusterConfig']['Status']['State']}")
```

### Delete Domain

```python
response = client.delete_domain(DomainName='{{user.domain_name}}')
print(f"Deleted: {response['DomainStatus']['DomainName']}")
```

### Create Snapshot

```python
response = client.create_snapshot(
    DomainName='{{user.domain_name}}',
    SnapshotName='{{user.snapshot_name}}'
)
print(f"Snapshot: {response['SnapshotDetail']['SnapshotName']} — {response['SnapshotDetail']['Status']}")
```

### List Snapshots

```python
response = client.list_snapshots(DomainName='{{user.domain_name}}')
for snap in response.get('Snapshots', []):
    print(f"{snap['SnapshotName']}: {snap['Status']} ({snap['SnapshotType']})")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_domain(**params)
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'ResourceAlreadyExistsException':
        print("Domain already exists.")
    elif code == 'InvalidTypeException':
        print("Invalid instance type. Check availability.")
    elif code == 'LimitExceededException':
        print("Quota exceeded. Request increase.")
    elif code == 'ThrottlingException':
        pass  # Retry with backoff
    else:
        raise
```

## Polling Pattern

```python
import time

def wait_for_domain(client, domain_name, target_state='Active', max_wait=1800, interval=60):
    for _ in range(max_wait // interval):
        response = client.describe_domain(DomainName=domain_name)
        status = response['DomainStatus']
        if status.get('Processing') == False and status.get('Created') == True:
            return True
        if status.get('Deleted'):
            raise RuntimeError("Domain was deleted")
        time.sleep(interval)
    raise TimeoutError("Timeout waiting for domain")
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| ResourceAlreadyExistsException | 409 | Domain exists; use update or different name |
| ResourceNotFoundException | 404 | Verify domain name |
| InvalidTypeException | 400 | Check instance type availability |
| LimitExceededException | 400 | Request quota increase |
| ThrottlingException | 429 | Backoff and retry |
| InternalException | 500 | Retry 3x; HALT |
| SnapshotInProgressException | 409 | Wait; retry after current snapshot |
| DisabledOperationException | 409 | Operation not allowed in current state |

## Retry Configuration

```python
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'adaptive'})
client = boto3.client('opensearch', config=config)
```
```

---

## Task 4: Create `aws-opensearch-ops/references/core-concepts.md`

**Files:**
- Create: `aws-opensearch-ops/references/core-concepts.md`

- [ ] **Step 1: Write service overview, primary resources, architecture, lifecycle, dependencies, best practices**

```markdown
# Core Concepts — OpenSearch Service

## What is Amazon OpenSearch Service

- **Purpose**: Managed search and analytics engine (successor to Amazon Elasticsearch Service)
- **Category**: Analytics / Search
- **Console**: https://console.aws.amazon.com/aos/
- **Docs**: https://docs.aws.amazon.com/opensearch-service/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| Domain | Managed OpenSearch cluster | /aos/home#opensearch/domains |
| Snapshot | Point-in-time backup | /aos/home#opensearch/snapshots |
| VPC Endpoint | Private access endpoint | /aos/home#opensearch/vpc-endpoints |
| Access Policy | Domain-level IAM policy | Domain detail → Security |

## Domain Lifecycle

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| Processing | Creating or updating | None (wait) |
| Active | Operational | All operations |
| SnapshotInProgress | Snapshot running | Read-only |
| UpgradeProcessing | Version upgrade | Read-only |
| Deleting | Deletion in progress | None |

## Architecture & Limits

### Region Availability
- Regional service
- Available in most AWS regions

### Quotas (Service Limits)

| Quota | Default | Adjustable |
|-------|---------|------------|
| Domains per region | 100 | Yes |
| Instances per domain | 80 | Yes |
| EBS volume size | 3 TB per node | No |
| Snapshot frequency | 1 per 5 min (manual) | No |

## Dependencies

| Dependency | Required? | Skill |
|------------|-----------|-------|
| VPC | Optional (public or VPC) | `aws-vpc-ops` |
| Subnet | If VPC | `aws-vpc-ops` |
| Security Group | If VPC | `aws-vpc-ops` |
| IAM Role | For fine-grained access | `aws-iam-ops` |
| KMS Key | For encryption at rest | `aws-kms-ops` |
| S3 Bucket | For snapshot repository | `aws-s3-ops` |

## Pricing Model (Summary)

- **On-demand instances**: Per hour per node
- **Storage**: EBS gp2/gp3/io1 per GB-month
- **Data transfer**: Standard AWS rates
- **UltraWarm / Cold**: Lower-cost storage tiers
- **Estimator**: https://calculator.aws/#/

## Best Practices

### Security
- Enable fine-grained access control (FGAC) with IAM or SAML
- Use VPC endpoints for private access
- Enable encryption at rest (KMS) and in transit (TLS)
- Restrict access policies to least privilege

### Availability
- Enable multi-AZ with ZoneAwareness
- Use dedicated master nodes for production
- Maintain regular snapshots

### Cost
- Right-size instance types (t3 for dev, m6g/r6g for prod)
- Use UltraWarm for infrequently accessed data
- Delete unused domains
```

---

## Task 5: Create `aws-opensearch-ops/references/troubleshooting.md`

**Files:**
- Create: `aws-opensearch-ops/references/troubleshooting.md`

- [ ] **Step 1: Write compact error tables and diagnostic flows (TE-3)**

```markdown
# Troubleshooting — OpenSearch Service

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| ResourceAlreadyExistsException (409) | Domain exists; use update or different name |
| ResourceNotFoundException (404) | Verify domain name and region |
| InvalidTypeException (400) | Check instance type availability in region |
| LimitExceededException (400) | Request quota increase |
| ThrottlingException (429) | Backoff and retry (max 3x) |
| InternalException (500) | Retry 3x; HALT |
| SnapshotInProgressException (409) | Wait; retry after current snapshot completes |
| DisabledOperationException (409) | Operation not allowed in current domain state |
| AccessDeniedException (403) | Check IAM permissions for `es:*` |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify region**: Check `AWS_DEFAULT_REGION` or pass `--region`
3. **Describe domain**: `aws opensearch describe-domain --domain-name {{user.domain_name}}`
4. **Check domain state**: Verify not in `Processing` or `UpgradeProcessing`
5. **Check cluster health**: Use domain endpoint `/_cluster/health` (out of CLI scope)
6. **Check dependencies**: VPC, SG, IAM role, KMS key, S3 snapshot bucket

## Common Issues

### Domain Stuck in Processing

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Stuck > 30 min | Service issue | Contact AWS support |
| Stuck after update | Blue/green in progress | Wait; normal for some changes |

### Snapshot Fails

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Status FAILED | Insufficient permissions | Check S3 bucket policy and IAM role |
| Status FAILED | Cluster red status | Fix cluster health first |

### Connection Refused

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot reach endpoint | Domain not Active | Wait for creation to complete |
| Cannot reach endpoint | VPC misconfiguration | Check VPC endpoint, SG, route tables |
| Access denied | Access policy too restrictive | Update domain access policy |

## CloudWatch Metrics

Key metrics for OpenSearch:
- `ClusterStatus.green|yellow|red`
- `Nodes`, `Shards.active`, `Shards.unassigned`
- `CPUUtilization`, `JVMMemoryPressure`
- `FreeStorageSpace`

```bash
aws cloudwatch get-metric-data \
  --namespace AWS/OpenSearchService \
  --metric-name ClusterStatus.red \
  --dimensions Name=DomainName,Value={{user.domain_name}} \
  --output json
```

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production domain down | Critical | Immediate support ticket |
| Data loss (no snapshots) | Critical | Immediate support ticket |
| Persistent InternalException | High | Support ticket with correlation IDs |
```

---

## Task 6: Create `aws-opensearch-ops/references/rubric.md`

**Files:**
- Create: `aws-opensearch-ops/references/rubric.md`

- [ ] **Step 1: Write full GCL rubric with 5 dimensions, operation-specific overrides, and Safety special cases**

```markdown
# OpenSearch Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-opensearch-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-domain` / `restore-snapshot` | 0 / 0.5 / 1 | Verifies `DomainName` / `SnapshotName` match the user request. Read back via `describe-domain` / `list-snapshots` and compare. Resource id must be echoed from a lookup (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-domain`, `delete-snapshot`, `restore-snapshot`, `delete-vpc-endpoint`, destructive `update-domain-config`) MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-domain` returns `ResourceAlreadyExistsException` if name collides — acceptable terminal state. `delete-domain` is idempotent at the API level (returns success for non-existent domain). `update-domain-config` triggers blue/green; not idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws opensearch <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-domain` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: instance type is valid for region, engine version is supported, EBS size ≤ quota, access policy is valid JSON. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-domain` | Correctness, Spec Compliance | Verify instance type availability; capture `DomainId` for downstream ops |
| `describe-domain` / `list-domain-names` | Correctness | Read-only; no safety gate |
| `update-domain-config` (non-destructive) | Correctness, Spec Compliance | Adding nodes, increasing storage — safe |
| `update-domain-config` (reduction/downgrade) | Correctness, **Safety** | `confirm=UPDATE_DOMAIN {{user.domain_name}}` required |
| `delete-domain` | Correctness, Safety, **Traceability** | Pre-flight: `describe-domain` to confirm exists and capture pre-delete state |
| `create-snapshot` | Correctness | Verify domain is Active; snapshot name is unique |
| `restore-snapshot` | Correctness, Safety, **Traceability** | `confirm=RESTORE_SNAPSHOT <name> TO <domain>`; pre-flight: `describe-domain` to confirm target exists |
| `delete-snapshot` | Correctness, **Safety** | `confirm=DELETE_SNAPSHOT <name>` required |
| `create-vpc-endpoint` | Correctness, Spec Compliance | VPC, subnet, SG must exist |
| `delete-vpc-endpoint` | Correctness, **Safety** | `confirm=DELETE_VPC_ENDPOINT <id>` required |

## Safety special cases (auto-fail)

- `delete-domain` on a domain with `SnapshotOptions.AutomatedSnapshotStartHour` set
  and no recent manual snapshot → **Correctness = 0 → ABORT** (data loss risk).
- `delete-domain` without `confirm=DELETE_DOMAIN {{user.domain_name}}` in trace →
  **Safety = 0 → ABORT**.
- `restore-snapshot` without `confirm=RESTORE_SNAPSHOT <name> TO <domain>` in trace →
  **Safety = 0 → ABORT**.
- `restore-snapshot` to a domain that is NOT in `Active` state →
  **Correctness = 0 → ABORT**.
- `update-domain-config` that reduces `InstanceCount` or changes to a smaller
  `InstanceType` without `confirm=UPDATE_DOMAIN {{user.domain_name}}` →
  **Safety = 0 → ABORT**.
- `DomainName` / `SnapshotName` in the request not echoed from a
  `describe-domain` / `list-snapshots` lookup → **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` →
  **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default for destructive skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial rubric for `aws-opensearch-ops` |
```

---

## Task 7: Create `aws-opensearch-ops/references/prompt-templates.md`

**Files:**
- Create: `aws-opensearch-ops/references/prompt-templates.md`

- [ ] **Step 1: Write Generator, Critic, Orchestrator prompts with Variable Convention table**

```markdown
# GCL Prompt Templates — `aws-opensearch-ops`

> Generator, Critic, and Orchestrator prompt skeletons mandated by
> `aws-skill-generator/references/gcl-spec.md` §7.

## 1. Generator Prompt (G)

```text
You are the **Generator** for the `aws-opensearch-ops` skill.
You execute OpenSearch Service operations on AWS via the AWS CLI v2 (primary)
or the boto3 SDK (fallback after 3 consecutive CLI failures).

# Inputs
- user request: {{user.request}}
- previous Critic feedback (empty on iter 1): {{output.critic_feedback}}
- rubric to satisfy: {{output.rubric}}
- operation type: {{output.operation}}
  # one of: create-domain | describe-domain | update-domain-config | delete-domain |
  #         list-domain-names | create-snapshot | restore-snapshot | delete-snapshot |
  #         list-snapshots | create-vpc-endpoint | delete-vpc-endpoint | describe-vpc-endpoints

# Required behavior
1. Follow `references/aws-cli-usage.md` and `references/core-concepts.md`
   for the matching operation.
2. Apply the **AWS CLI primary / boto3 fallback** policy:
   - Primary: `aws opensearch <op> --output json --region "{{user.region}}"`
     (always `--output json` AFTER the subcommand, per `gcl-spec.md` §9).
   - Retry up to 3 times with exponential backoff (0s → 2s → 4s) on failure.
   - Only after 3 consecutive failures, switch to boto3.
3. **First command of every trace MUST be:**
   `aws sts get-caller-identity --output json --region "{{user.region}}"`
   (rule A10).
4. For destructive ops (`delete-domain`, `delete-snapshot`, `restore-snapshot`,
   `delete-vpc-endpoint`, destructive `update-domain-config`), the Orchestrator
   will inject a `{{user.safety_confirm}}` flag. The trace MUST record the exact
   confirmation string per operation:
   - `delete-domain`: `confirm=DELETE_DOMAIN {{user.domain_name}}`
   - `delete-snapshot`: `confirm=DELETE_SNAPSHOT {{user.snapshot_name}}`
   - `restore-snapshot`: `confirm=RESTORE_SNAPSHOT {{user.snapshot_name}} TO {{user.domain_name}}`
   - `delete-vpc-endpoint`: `confirm=DELETE_VPC_ENDPOINT {{user.vpc_endpoint_id}}`
   - `update-domain-config` (reduction/downgrade): `confirm=UPDATE_DOMAIN {{user.domain_name}}`
   Refuse to proceed without the correct literal in the trace.
5. For `delete-domain`:
   - Pre-flight: `aws opensearch describe-domain --domain-name <name>` to confirm
     exists and capture pre-delete state.
   - Warn if no recent manual snapshot exists.
6. For `restore-snapshot`:
   - Pre-flight: `aws opensearch describe-domain --domain-name <name>` to confirm
     target domain is Active.
7. NEVER include any credentials or secret values in the trace (rule A9).

# Output (strict JSON)
{
  "command":   "<exact aws or boto3 call you ran>",
  "args":      { ... },
  "exit_code": <int>,
  "result":    "<raw response excerpt, max 2 KB>",
  "post_state": {
    "domain_name":    "...",
    "domain_id":      "...",
    "endpoint":       "...",
    "status":         "Active|Processing|...",
    "engine_version": "...",
    "cluster_config": { ... }
  },
  "errors":    [],
  "notes":     "<free text, ≤ 200 chars>"
}

# Constraint
Do NOT self-score. Do NOT modify the rubric. Just execute and report.
```

## 2. Critic Prompt (C)

```text
You are the **Critic** for the `aws-opensearch-ops` skill.
You are an independent auditor. You will see ONE execution result and its
trace. You will score it STRICTLY against the rubric below.

# Critical rule
You will NOT see the original user request. Judge ONLY what was actually done.

# Inputs
- generator output: {{output.generator_output}}
- trace:             {{output.trace}}
- rubric:            {{output.rubric}}
- operation type:    {{output.operation}}

# Scoring procedure
For each of the 5 dimensions in `rubric`, output a score per the allowed scale
(0, 0.5, or 1) and a one-sentence justification.

# Output (strict JSON only)
{
  "scores": {
    "correctness":      0|0.5|1,
    "safety":           0|0.5|1,
    "idempotency":      0|0.5|1,
    "traceability":     0|0.5|1,
    "spec_compliance":  0|0.5|1
  },
  "justifications": { ... },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": <true if any safety/correctness = 0, else false>
}

# Hard rules
- Safety = 0 if `delete-domain` lacks `confirm=DELETE_DOMAIN <name>` in trace.
- Safety = 0 if `restore-snapshot` lacks `confirm=RESTORE_SNAPSHOT <name> TO <domain>` in trace.
- Safety = 0 if destructive `update-domain-config` lacks `confirm=UPDATE_DOMAIN <name>` in trace.
- Correctness = 0 if `delete-domain` called while domain has no recent snapshot.
- Correctness = 0 if `restore-snapshot` called on non-Active domain.
- Correctness = 0 if resource name not echoed from lookup (rule A8).
- Correctness = 0 if `--region` mismatch (rule A7).
- Traceability = 0 if `aws sts get-caller-identity` not first command (rule A10).
- Never invent values. If a field is missing, score 0 and explain.
```

## 3. Orchestrator Decider Prompt (O)

```text
You are the **Orchestrator** deciding the next step of the GCL loop.

# Inputs
- previous Critic scores:  {{output.critic_scores}}
- rubric thresholds:        {{output.rubric}}
- iteration count:          {{output.iter}}
- max_iterations:           2
- blocking flag:            {{output.critic_blocking}}

# Decision rules (first match wins)
1. If `safety == 0` OR `blocking == true` → decision = `ABORT`
2. Else if every score meets its threshold → decision = `RETURN`
3. Else if `iter < max_iterations`        → decision = `RETRY`
4. Else                                   → decision = `RETURN_BEST`

# Output (strict JSON)
{
  "decision": "ABORT|RETURN|RETRY|RETURN_BEST",
  "reason":   "<one sentence>",
  "next_iter_feedback": "<suggestions or null>"
}
```

## Variable Convention

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or `{{env.AWS_DEFAULT_REGION}}` | mismatch → Correctness=0 (rule A7) |
| `{{user.domain_name}}` | user input | Echoed from `describe-domain` (rule A8) |
| `{{user.snapshot_name}}` | user input | Echoed from `list-snapshots` |
| `{{user.vpc_endpoint_id}}` | user input | Echoed from `describe-vpc-endpoints` |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER prompt user; NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | command, args, exit_code, result, post_state, errors |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of listed operation types |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial GCL prompt templates for `aws-opensearch-ops` |
```

---

## Task 8: Create `aws-opensearch-ops/assets/example-config.yaml`

**Files:**
- Create: `aws-opensearch-ops/assets/example-config.yaml`

- [ ] **Step 1: Write YAML config with anchors (TE-5)**

```yaml
# OpenSearch Service Configuration Examples (YAML Anchors)
# =========================================================
# Template: Replace {{user.*}} placeholders at runtime.
# Use YAML anchors to avoid repeating common settings.

# --- Shared Anchors ---
x-tags-dev: &tags-dev
  Tags:
    - Key: "Name"; Value: "{{user.domain_name}}"
    - Key: "Environment"; Value: "dev"
    - Key: "ManagedBy"; Value: "AI-Agent"

x-cluster-small: &cluster-small
  InstanceType: "t3.small.search"
  InstanceCount: 2
  DedicatedMasterEnabled: false
  ZoneAwarenessEnabled: false

x-cluster-prod: &cluster-prod
  InstanceType: "m6g.large.search"
  InstanceCount: 3
  DedicatedMasterEnabled: true
  DedicatedMasterType: "m6g.large.search"
  DedicatedMasterCount: 3
  ZoneAwarenessEnabled: true
  ZoneAwarenessConfig:
    AvailabilityZoneCount: 3

x-ebs-gp3: &ebs-gp3
  EBSEnabled: true
  VolumeType: "gp3"
  VolumeSize: 100
  Iops: 3000

# --- Domain Launch Configuration ---
domain_config_dev:
  DomainName: "{{user.domain_name}}"
  EngineVersion: "OpenSearch_2.11"
  ClusterConfig:
    <<: *cluster-small
  EBSOptions:
    <<: *ebs-gp3
    VolumeSize: 10
  AccessPolicies: >
    {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:root"},"Action":"es:*","Resource":"arn:aws:es:{{env.AWS_DEFAULT_REGION}}:{{env.AWS_ACCOUNT_ID}}:domain/{{user.domain_name}}/*"}]}
  <<: *tags-dev

domain_config_prod:
  DomainName: "{{user.domain_name}}"
  EngineVersion: "OpenSearch_2.11"
  ClusterConfig:
    <<: *cluster-prod
  EBSOptions:
    <<: *ebs-gp3
    VolumeSize: 500
  EncryptionAtRestOptions:
    Enabled: true
    KmsKeyId: "{{user.kms_key_id}}"
  NodeToNodeEncryptionOptions:
    Enabled: true
  DomainEndpointOptions:
    EnforceHTTPS: true
    TLSSecurityPolicy: "Policy-Min-TLS-1-2-2019-07"
  AccessPolicies: >
    {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:root"},"Action":"es:*","Resource":"arn:aws:es:{{env.AWS_DEFAULT_REGION}}:{{env.AWS_ACCOUNT_ID}}:domain/{{user.domain_name}}/*"}]}
  <<: *tags-dev

# --- Snapshot Configuration ---
snapshot_config:
  DomainName: "{{user.domain_name}}"
  SnapshotName: "manual-{{user.snapshot_name}}"
  Repository: "cs-automated"  # or custom S3 repo

# --- VPC Endpoint Configuration ---
vpc_endpoint_config:
  DomainArn: "arn:aws:es:{{env.AWS_DEFAULT_REGION}}:{{env.AWS_ACCOUNT_ID}}:domain/{{user.domain_name}}"
  VPCOptions:
    SubnetIds:
      - "{{user.subnet_id}}"
    SecurityGroupIds:
      - "{{user.sg_id}}"
```

---

## Task 9: Create `aws-guardduty-ops/SKILL.md`

**Files:**
- Create: `aws-guardduty-ops/SKILL.md`

- [ ] **Step 1: Write YAML frontmatter with `metadata.gcl` block**

```yaml
---
name: aws-guardduty-ops
description: >-
  Use when the user needs to manage AWS GuardDuty resources: create or
  delete detectors, enable or disable GuardDuty in an account or
  organization, create and manage filter rules, IP sets, and threat
  intel sets, archive or unarchive findings, manage suppression rules,
  configure publishing destinations (S3/EventBridge), or review
  GuardDuty finding details and severity. Also use for GuardDuty
  operational tasks such as threat detection coverage review, finding
  triage, or multi-account GuardDuty administration.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials,
  network access to GuardDuty endpoints.
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
```

- [ ] **Step 2: Write `## Trigger & Scope` section**

```markdown
## Trigger & Scope

### SHOULD Use When
- User mentions "GuardDuty", "threat detection", "security findings"
- User requests enable/disable GuardDuty in an account or organization
- User asks to create, update, list, or delete detectors
- User needs filter rules, IP sets, or threat intel sets
- User requests finding archive/unarchive or suppression rules
- User asks to create, update, or delete publishing destinations
- User needs GuardDuty finding details, severity review, or triage
- User requests multi-account GuardDuty administration
- Keywords: guardduty, detector, finding, threat, ip set, threat intel, suppression, archive, destination

### SHOULD NOT Use When
- IAM policy changes → delegate to: `aws-iam-ops`
- KMS encryption key operations → delegate to: `aws-kms-ops`
- Security Hub findings management → delegate to: `aws-securityhub-ops`
- EventBridge automated response rules → delegate to: `aws-eventbridge-ops`
- S3 bucket operations for publishing destination → delegate to: `aws-s3-ops`
- CloudWatch alarms for GuardDuty metrics → delegate to: `aws-cloudwatch-ops`

### Delegation
- IAM roles/policies → `aws-iam-ops` | KMS keys → `aws-kms-ops`
- Security Hub → `aws-securityhub-ops` | EventBridge → `aws-eventbridge-ops`
- S3 publishing destination → `aws-s3-ops` | CloudWatch → `aws-cloudwatch-ops`
```

- [ ] **Step 3: Write `## Scope` table**

```markdown
## Scope

| Operation | Safety Gate |
|-----------|-------------|
| Create/Delete Detector | Delete: human confirm |
| Enable/Disable GuardDuty | Disable: human confirm |
| Create/Update/Delete Filter | Delete: human confirm |
| Create/Update/Delete IP Set | Delete: human confirm |
| Create/Update/Delete Threat Intel Set | Delete: human confirm |
| Create/Update/Delete Publishing Destination | Delete: human confirm |
| Archive/Unarchive Findings | Archive: human confirm |
| Create/Update/Delete Suppression Rule | Delete: human confirm |
| Get Findings / List Findings | None |
| Describe Organization Configuration | None |
```

- [ ] **Step 4: Write `## Variable Convention` table**

```markdown
## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.detector_id}}` | User input | Ask once; reuse |
| `{{user.filter_name}}` | User input | Ask once; reuse |
| `{{user.ip_set_id}}` | User input | Ask once; reuse |
| `{{user.threat_intel_set_id}}` | User input | Ask once; reuse |
| `{{user.destination_id}}` | User input | Ask once; reuse |
| `{{user.finding_id}}` | User input | Ask once; reuse |
| `{{output.DetectorId}}` | Last API response | Parse: `.DetectorId` |
| `{{output.FindingId}}` | Last API response | Parse: `.Findings[0].Id` |
```

- [ ] **Step 5: Write `## Execution Flow` section**

```markdown
## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```
Log: `[OK] Region={{env.AWS_DEFAULT_REGION}} Credential verified.`
On failure: `[FAIL] AWS credential verification failed. Action: Check .env`
```bash
# Verify GuardDuty is available in region
aws guardduty list-detectors --region {{env.AWS_DEFAULT_REGION}} --output json
```
Log: `[OK] GuardDuty available in {{env.AWS_DEFAULT_REGION}}`

### Execute (Primary: CLI)
See [references/aws-cli-usage.md](references/aws-cli-usage.md) for full command reference.

### Execute (Fallback: boto3)
After 3 CLI failures, switch to SDK.

### Validate
```
1. Poll: aws guardduty get-detector --detector-id {{user.detector_id}}
2. Verify state matches expected (enabled/disabled/created/deleted)
3. For findings: confirm count and severity match request
```

### Recover
| Error Type | Action |
|------------|--------|
| BadRequestException | HALT — verify request parameters |
| AccessDeniedException | HALT — check IAM permissions |
| LimitExceededException | HALT — request quota increase |
| ThrottlingException (429) | Exponential backoff, max 3 retries |
| InternalServerError (5xx) | Retry 3x; HALT |
```

- [ ] **Step 6: Write `## Safety Gates` section**

```markdown
## Safety Gates

### Delete Detector
```
BEFORE delete-detector:
1. Display: "Deleting detector {{user.detector_id}} will permanently remove all GuardDuty configuration for this account/region"
2. Ask: "Type 'DELETE_DETECTOR {{user.detector_id}}' to confirm"
```

### Disable GuardDuty
```
BEFORE disable-guardduty:
1. Display: "Disabling GuardDuty will stop all threat detection in this account/region"
2. Ask: "Type 'DISABLE_GUARDDUTY {{user.detector_id}}' to confirm"
```

### Delete Filter
```
BEFORE delete-filter:
1. Display: "Deleting filter {{user.filter_name}} will remove this suppression rule"
2. Ask: "Type 'DELETE_FILTER {{user.filter_name}}' to confirm"
```

### Delete IP Set
```
BEFORE delete-ip-set:
1. Display: "Deleting IP set {{user.ip_set_id}} will remove this trusted/threat IP list"
2. Ask: "Type 'DELETE_IP_SET {{user.ip_set_id}}' to confirm"
```

### Delete Threat Intel Set
```
BEFORE delete-threat-intel-set:
1. Display: "Deleting threat intel set {{user.threat_intel_set_id}} will remove this threat intelligence source"
2. Ask: "Type 'DELETE_THREAT_INTEL_SET {{user.threat_intel_set_id}}' to confirm"
```

### Delete Publishing Destination
```
BEFORE delete-publishing-destination:
1. Display: "Deleting publishing destination {{user.destination_id}} will stop GuardDuty findings from being published"
2. Ask: "Type 'DELETE_DESTINATION {{user.destination_id}}' to confirm"
```

### Archive Findings
```
BEFORE archive-findings:
1. Display: "Archiving findings will hide them from the default findings view"
2. Ask: "Type 'ARCHIVE_FINDINGS {{user.finding_id}}' to confirm"
```
```

- [ ] **Step 7: Write `## Output Convention` section**

```markdown
## Output Convention
All commands use `--output json`. Key JSON paths:
- `.DetectorIds[]`
- `.DetectorId`, `.Status`, `.ServiceRole`, `.FindingPublishingFrequency`
- `.Findings[].{Id,DetectorId,Type,ServiceName,Resource,Severity,Count,AccountId,Region,CreatedAt,UpdatedAt,Description}`
- `.FilterNames[]`, `.FilterName`, `.FilterAction`, `.FindingCriteria`
- `.IpSetIds[]`, `.IpSetId`, `.Name`, `.Format`, `.Location`, `.Status`
- `.ThreatIntelSetIds[]`, `.ThreatIntelSetId`, `.Name`, `.Format`, `.Location`, `.Status`
- `.Destinations[].{DestinationId,DestinationType,Status}`
```

- [ ] **Step 8: Write `## Related Skills`, `## Cross-Skill Orchestration`, `## Reference Files`**

```markdown
## Related Skills
- `aws-iam-ops` — IAM policies and roles | `aws-kms-ops` — Encryption keys
- `aws-securityhub-ops` — Security findings aggregation | `aws-eventbridge-ops` — Automated response
- `aws-s3-ops` — S3 publishing destination | `aws-cloudwatch-ops` — Alarms and metrics

## Cross-Skill Orchestration

| Scenario | Chain |
|----------|-------|
| GuardDuty + Security Hub | guardduty → securityhub (enable GuardDuty → export findings to Security Hub) |
| GuardDuty + EventBridge | guardduty → eventbridge (finding → EventBridge rule → remediation) |
| GuardDuty + S3 | guardduty → s3 (publishing destination is an S3 bucket) |
| GuardDuty + IAM | guardduty → iam (service-linked role and cross-account roles) |

## Reference Files
- `references/aws-cli-usage.md` — CLI command reference
- `references/boto3-sdk-usage.md` — Python SDK patterns
- `references/core-concepts.md` — GuardDuty architecture, concepts
- `references/troubleshooting.md` — Error codes, recovery procedures
- `references/rubric.md` — GCL 5-dimension rubric
- `references/prompt-templates.md` — G/C/O prompt skeletons
- `assets/example-config.yaml` — Configuration examples
```

- [ ] **Step 9: Write `## Quality Gate (GCL)` section**

```markdown
## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-08, required). Every execution of
> `aws-guardduty-ops` MUST be wrapped by the Generator-Critic-Loop.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-detector` — `confirm=DELETE_DETECTOR {{user.detector_id}}`
- `disable-guardduty` — `confirm=DISABLE_GUARDDUTY {{user.detector_id}}`
- `delete-filter` — `confirm=DELETE_FILTER {{user.filter_name}}`
- `delete-ip-set` — `confirm=DELETE_IP_SET {{user.ip_set_id}}`
- `delete-threat-intel-set` — `confirm=DELETE_THREAT_INTEL_SET {{user.threat_intel_set_id}}`
- `delete-publishing-destination` — `confirm=DELETE_DESTINATION {{user.destination_id}}`
- `archive-findings` — `confirm=ARCHIVE_FINDINGS {{user.finding_id}}`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource echo-back),
A9 (no secrets in trace), A10 (sts first command).

See `references/rubric.md` and `references/prompt-templates.md` for details.
```

- [ ] **Step 10: Verify frontmatter parses correctly**

Run:
```bash
python3 -c "import yaml,re; yaml.safe_load(re.search(r'^---\n(.*?)\n---', open('aws-guardduty-ops/SKILL.md').read(), re.DOTALL).group(1))"
```

---

## Task 10: Create `aws-guardduty-ops/references/aws-cli-usage.md`

**Files:**
- Create: `aws-guardduty-ops/references/aws-cli-usage.md`

- [ ] **Step 1: Write Common JSON Paths, Command Map, and Common Patterns**

```markdown
# AWS CLI Usage — GuardDuty

## Common JSON Paths (Centralized)

```
# List Detectors:    .DetectorIds[]
# Get Detector:      .Status, .ServiceRole, .FindingPublishingFrequency
# Create Detector:   .DetectorId
# List Findings:     .FindingIds[]
# Get Findings:      .Findings[].{Id,Type,ServiceName,Severity,Count,AccountId,Region,CreatedAt}
# List Filters:      .FilterNames[]
# Get Filter:        .FilterName, .FilterAction, .FindingCriteria, .Rank
# List IP Sets:      .IpSetIds[]
# Get IP Set:        .Name, .Format, .Location, .Status
# List Threat Intel: .ThreatIntelSetIds[]
# Get Threat Intel:  .Name, .Format, .Location, .Status
# List Destinations: .Destinations[].{DestinationId,DestinationType,Status}
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Create detector | `aws guardduty create-detector` |
| Get detector | `aws guardduty get-detector` |
| Update detector | `aws guardduty update-detector` |
| Delete detector | `aws guardduty delete-detector` |
| List detectors | `aws guardduty list-detectors` |
| List findings | `aws guardduty list-findings` |
| Get findings | `aws guardduty get-findings` |
| Archive findings | `aws guardduty archive-findings` |
| Unarchive findings | `aws guardduty unarchive-findings` |
| Create filter | `aws guardduty create-filter` |
| Update filter | `aws guardduty update-filter` |
| Delete filter | `aws guardduty delete-filter` |
| List filters | `aws guardduty list-filters` |
| Create IP set | `aws guardduty create-ip-set` |
| Update IP set | `aws guardduty update-ip-set` |
| Delete IP set | `aws guardduty delete-ip-set` |
| Create threat intel set | `aws guardduty create-threat-intel-set` |
| Delete threat intel set | `aws guardduty delete-threat-intel-set` |
| Create publishing destination | `aws guardduty create-publishing-destination` |
| Update publishing destination | `aws guardduty update-publishing-destination` |
| Delete publishing destination | `aws guardduty delete-publishing-destination` |

## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Region
Pass `--region` or rely on `AWS_DEFAULT_REGION`. GuardDuty is regional.

## Common Patterns

### Create Detector
```bash
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --region "{{user.region}}" \
  --output json
```

### Get Detector
```bash
aws guardduty get-detector \
  --detector-id "{{user.detector_id}}" \
  --region "{{user.region}}" \
  --output json
```

### List Findings
```bash
aws guardduty list-findings \
  --detector-id "{{user.detector_id}}" \
  --region "{{user.region}}" \
  --output json
```

### Get Findings
```bash
aws guardduty get-findings \
  --detector-id "{{user.detector_id}}" \
  --finding-ids "{{user.finding_id}}" \
  --region "{{user.region}}" \
  --output json
```

### Archive Findings
```bash
aws guardduty archive-findings \
  --detector-id "{{user.detector_id}}" \
  --finding-ids "{{user.finding_id}}" \
  --region "{{user.region}}" \
  --output json
```

### Create IP Set
```bash
aws guardduty create-ip-set \
  --detector-id "{{user.detector_id}}" \
  --name "TrustedIPs" \
  --format TXT \
  --location "s3://{{user.bucket}}/trusted-ips.txt" \
  --activate \
  --region "{{user.region}}" \
  --output json
```

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```

## Retry Strategy (CLI)

CLI has built-in retry logic. Configure in `~/.aws/config`:
```ini
[default]
retry_mode = adaptive
max_attempts = 3
```
```

---

## Task 11: Create `aws-guardduty-ops/references/boto3-sdk-usage.md`

**Files:**
- Create: `aws-guardduty-ops/references/boto3-sdk-usage.md`

- [ ] **Step 1: Write boto3 patterns (no docstrings per TE-2)**

```markdown
# boto3 SDK Usage — GuardDuty

## Client Initialization

```python
import boto3
import os

client = boto3.client(
    'guardduty',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)
```

## Operation Patterns

### Create Detector

```python
response = client.create_detector(
    Enable=True,
    FindingPublishingFrequency='FIFTEEN_MINUTES'
)
detector_id = response['DetectorId']
print(f"Created detector: {detector_id}")
```

### Get Detector

```python
response = client.get_detector(DetectorId='{{user.detector_id}}')
print(f"Status: {response['Status']}")
print(f"Frequency: {response.get('FindingPublishingFrequency')}")
```

### List Findings

```python
response = client.list_findings(DetectorId='{{user.detector_id}}')
for finding_id in response.get('FindingIds', []):
    print(finding_id)
```

### Get Findings

```python
response = client.get_findings(
    DetectorId='{{user.detector_id}}',
    FindingIds=['{{user.finding_id}}']
)
for finding in response.get('Findings', []):
    print(f"{finding['Id']}: {finding['Type']} (Severity: {finding['Severity']})")
```

### Archive Findings

```python
response = client.archive_findings(
    DetectorId='{{user.detector_id}}',
    FindingIds=['{{user.finding_id}}']
)
print("Archived")
```

### Create IP Set

```python
response = client.create_ip_set(
    DetectorId='{{user.detector_id}}',
    Name='TrustedIPs',
    Format='TXT',
    Location='s3://{{user.bucket}}/trusted-ips.txt',
    Activate=True
)
print(f"IP Set: {response['IpSetId']}")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.create_detector(**params)
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'BadRequestException':
        print("Invalid request parameters.")
    elif code == 'AccessDeniedException':
        print("Insufficient IAM permissions.")
    elif code == 'LimitExceededException':
        print("Quota exceeded.")
    elif code == 'ThrottlingException':
        pass  # Retry with backoff
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| BadRequestException | 400 | Fix args; retry once |
| AccessDeniedException | 403 | HALT; check IAM permissions |
| LimitExceededException | 400 | HALT; request quota increase |
| ThrottlingException | 429 | Backoff and retry |
| InternalServerError | 500 | Retry 3x; HALT |

## Retry Configuration

```python
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'adaptive'})
client = boto3.client('guardduty', config=config)
```
```

---

## Task 12: Create `aws-guardduty-ops/references/core-concepts.md`

**Files:**
- Create: `aws-guardduty-ops/references/core-concepts.md`

- [ ] **Step 1: Write service overview, resources, architecture, lifecycle, dependencies**

```markdown
# Core Concepts — GuardDuty

## What is Amazon GuardDuty

- **Purpose**: Intelligent threat detection service that continuously monitors for malicious activity
- **Category**: Security
- **Console**: https://console.aws.amazon.com/guardduty/
- **Docs**: https://docs.aws.amazon.com/guardduty/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| Detector | Core GuardDuty resource per region | /guardduty/home#/findings |
| Finding | Security issue detected | /guardduty/home#/findings |
| Filter | Suppression rule for findings | Detector settings → Filters |
| IP Set | Trusted or threat IP list | Detector settings → Lists |
| Threat Intel Set | External threat intelligence | Detector settings → Lists |
| Publishing Destination | S3 or EventBridge export | Detector settings → Destinations |

## Detector Lifecycle

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| Enabled | Active threat detection | All operations |
| Disabled | Detection paused | Enable, delete, read |
| Non-existent | Not created | Create |

## Architecture & Limits

### Region Availability
- Regional service
- Available in most AWS regions

### Quotas (Service Limits)

| Quota | Default | Adjustable |
|-------|---------|------------|
| Detectors per region | 1 | No |
| Filters per detector | 100 | Yes |
| IP sets per detector | 6 | No |
| Threat intel sets per detector | 6 | No |
| Publishing destinations | 1 S3 + 1 EventBridge | No |

## Dependencies

| Dependency | Required? | Skill |
|------------|-----------|-------|
| IAM Role | Yes (service-linked) | `aws-iam-ops` |
| S3 Bucket | If S3 destination | `aws-s3-ops` |
| EventBridge | If EventBridge destination | `aws-eventbridge-ops` |
| KMS Key | For S3 encryption | `aws-kms-ops` |

## Pricing Model (Summary)

- **Per-event analysis**: CloudTrail, VPC Flow Logs, DNS logs
- **Free trial**: 30 days
- **Estimator**: https://calculator.aws/#/

## Best Practices

### Security
- Enable in all active regions
- Use IP sets to reduce false positives
- Integrate with Security Hub for centralized findings
- Use EventBridge for automated response

### Operations
- Regular review of high-severity findings
- Archive false positives with suppression rules
- Maintain threat intel sets from trusted sources

### Cost
- Disable in unused regions
- Use filters to reduce noise
```

---

## Task 13: Create `aws-guardduty-ops/references/troubleshooting.md`

**Files:**
- Create: `aws-guardduty-ops/references/troubleshooting.md`

- [ ] **Step 1: Write compact error tables and diagnostic flows**

```markdown
# Troubleshooting — GuardDuty

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| BadRequestException (400) | Fix args per AWS API docs |
| AccessDeniedException (403) | HALT — check IAM permissions (guardduty:*) |
| LimitExceededException (400) | HALT — request quota increase |
| ThrottlingException (429) | Backoff and retry (max 3x) |
| InternalServerError (500) | Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify region**: Check `AWS_DEFAULT_REGION` or pass `--region`
3. **List detectors**: `aws guardduty list-detectors`
4. **Get detector status**: `aws guardduty get-detector --detector-id {{user.detector_id}}`
5. **Check findings**: `aws guardduty list-findings --detector-id {{user.detector_id}}`
6. **Verify IAM permissions**: Ensure `guardduty:*` or specific actions allowed

## Common Issues

### Detector Already Exists

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create detector | One detector per region | Use existing detector or delete first |

### Findings Not Appearing

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No findings after enable | Delay in analysis | Wait 1-2 hours; check data sources |
| No findings | Region has no activity | Normal for inactive regions |

### IP Set Fails to Activate

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Status = ERROR | Invalid file format | Ensure TXT format with one IP per line |
| Status = ERROR | S3 permission | Check bucket policy allows GuardDuty |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production account compromise | Critical | Immediate support ticket + incident response |
| Persistent InternalServerError | High | Support ticket with correlation IDs |
| False positive flood | Medium | Create filter; contact support if pattern |
```

---

## Task 14: Create `aws-guardduty-ops/references/rubric.md`

**Files:**
- Create: `aws-guardduty-ops/references/rubric.md`

- [ ] **Step 1: Write full GCL rubric**

```markdown
# GuardDuty Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric for `aws-guardduty-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-detector` | 0 / 0.5 / 1 | Verifies `DetectorId` / `FindingId` / `FilterName` match the user request. Read back via `get-detector` / `list-findings` / `list-filters` and compare. Resource id must be echoed from a lookup (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-detector`, `disable-guardduty`, `delete-filter`, `delete-ip-set`, `delete-threat-intel-set`, `delete-publishing-destination`, `archive-findings`) MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-detector` returns `BadRequestException` if detector already exists (one per region). `archive-findings` is idempotent. `delete-detector` is idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws guardduty <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `get-detector` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: one detector per region, filter count ≤ 100, IP set count ≤ 6, threat intel set count ≤ 6. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-detector` | Correctness, Spec Compliance | One per region; capture `DetectorId` |
| `get-detector` / `list-detectors` | Correctness | Read-only |
| `update-detector` | Correctness | Non-destructive config changes |
| `delete-detector` | Correctness, Safety, **Traceability** | `confirm=DELETE_DETECTOR <id>` required |
| `disable-guardduty` | Correctness, **Safety** | `confirm=DISABLE_GUARDDUTY <id>` required |
| `list-findings` / `get-findings` | Correctness | Read-only |
| `archive-findings` | Correctness, **Safety** | `confirm=ARCHIVE_FINDINGS <id>` required |
| `create-filter` / `update-filter` | Correctness, Spec Compliance | Filter count ≤ 100 |
| `delete-filter` | Correctness, **Safety** | `confirm=DELETE_FILTER <name>` required |
| `create-ip-set` / `update-ip-set` | Correctness, Spec Compliance | IP set count ≤ 6 |
| `delete-ip-set` | Correctness, **Safety** | `confirm=DELETE_IP_SET <id>` required |
| `create-threat-intel-set` | Correctness, Spec Compliance | Threat intel set count ≤ 6 |
| `delete-threat-intel-set` | Correctness, **Safety** | `confirm=DELETE_THREAT_INTEL_SET <id>` required |
| `create-publishing-destination` | Correctness, Spec Compliance | S3 or EventBridge |
| `delete-publishing-destination` | Correctness, **Safety** | `confirm=DELETE_DESTINATION <id>` required |

## Safety special cases (auto-fail)

- `delete-detector` without `confirm=DELETE_DETECTOR {{user.detector_id}}` in trace →
  **Safety = 0 → ABORT**.
- `disable-guardduty` without `confirm=DISABLE_GUARDDUTY {{user.detector_id}}` in trace →
  **Safety = 0 → ABORT**.
- `archive-findings` without `confirm=ARCHIVE_FINDINGS {{user.finding_id}}` in trace →
  **Safety = 0 → ABORT**.
- `delete-filter` without `confirm=DELETE_FILTER {{user.filter_name}}` in trace →
  **Safety = 0 → ABORT**.
- `delete-ip-set` without `confirm=DELETE_IP_SET {{user.ip_set_id}}` in trace →
  **Safety = 0 → ABORT**.
- `delete-threat-intel-set` without `confirm=DELETE_THREAT_INTEL_SET {{user.threat_intel_set_id}}` in trace →
  **Safety = 0 → ABORT**.
- `delete-publishing-destination` without `confirm=DELETE_DESTINATION {{user.destination_id}}` in trace →
  **Safety = 0 → ABORT**.
- `DetectorId` / `FindingId` / `FilterName` in request not echoed from a
  `get-detector` / `list-findings` / `list-filters` lookup →
  **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` →
  **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- `create-detector` called when a detector already exists in the region →
  **Spec Compliance = 0 → ABORT** (one per region limit).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial rubric for `aws-guardduty-ops` |
```

---

## Task 15: Create `aws-guardduty-ops/references/prompt-templates.md`

**Files:**
- Create: `aws-guardduty-ops/references/prompt-templates.md`

- [ ] **Step 1: Write Generator, Critic, Orchestrator prompts**

```markdown
# GCL Prompt Templates — `aws-guardduty-ops`

## 1. Generator Prompt (G)

```text
You are the **Generator** for the `aws-guardduty-ops` skill.

# Inputs
- user request: {{user.request}}
- previous Critic feedback: {{output.critic_feedback}}
- rubric: {{output.rubric}}
- operation type: {{output.operation}}
  # one of: create-detector | get-detector | update-detector | delete-detector | list-detectors |
  #         list-findings | get-findings | archive-findings | unarchive-findings |
  #         create-filter | update-filter | delete-filter | list-filters |
  #         create-ip-set | update-ip-set | delete-ip-set | list-ip-sets |
  #         create-threat-intel-set | delete-threat-intel-set | list-threat-intel-sets |
  #         create-publishing-destination | update-publishing-destination | delete-publishing-destination

# Required behavior
1. Follow `references/aws-cli-usage.md` and `references/core-concepts.md`.
2. Primary: `aws guardduty <op> --output json --region "{{user.region}}"`
3. **First command MUST be:** `aws sts get-caller-identity --output json` (rule A10).
4. For destructive ops, trace MUST record exact confirmation:
   - `delete-detector`: `confirm=DELETE_DETECTOR {{user.detector_id}}`
   - `disable-guardduty`: `confirm=DISABLE_GUARDDUTY {{user.detector_id}}`
   - `delete-filter`: `confirm=DELETE_FILTER {{user.filter_name}}`
   - `delete-ip-set`: `confirm=DELETE_IP_SET {{user.ip_set_id}}`
   - `delete-threat-intel-set`: `confirm=DELETE_THREAT_INTEL_SET {{user.threat_intel_set_id}}`
   - `delete-publishing-destination`: `confirm=DELETE_DESTINATION {{user.destination_id}}`
   - `archive-findings`: `confirm=ARCHIVE_FINDINGS {{user.finding_id}}`
5. NEVER include credentials in trace (rule A9).

# Output (strict JSON)
{
  "command": "<exact call>",
  "args": { ... },
  "exit_code": <int>,
  "result": "<excerpt, max 2 KB>",
  "post_state": {
    "detector_id": "...",
    "status": "ENABLED|DISABLED",
    "finding_count": <int>
  },
  "errors": [],
  "notes": "<≤ 200 chars>"
}

# Constraint
Do NOT self-score. Do NOT modify the rubric.
```

## 2. Critic Prompt (C)

```text
You are the **Critic** for `aws-guardduty-ops`.
You will NOT see the original user request. Judge ONLY what was done.

# Inputs
- generator output: {{output.generator_output}}
- trace: {{output.trace}}
- rubric: {{output.rubric}}
- operation type: {{output.operation}}

# Output (strict JSON)
{
  "scores": { "correctness": 0|0.5|1, "safety": 0|0.5|1, "idempotency": 0|0.5|1, "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1 },
  "justifications": { ... },
  "suggestions": ["≤ 3 improvements"],
  "blocking": <true if safety/correctness = 0>
}

# Hard rules
- Safety = 0 if destructive op lacks confirmation in trace.
- Correctness = 0 if resource id not echoed from lookup (rule A8).
- Correctness = 0 if region mismatch (rule A7).
- Traceability = 0 if sts not first command (rule A10).
- Spec Compliance = 0 if create-detector called when detector exists.
```

## 3. Orchestrator Decider Prompt (O)

```text
You are the **Orchestrator**.

# Inputs
- previous Critic scores: {{output.critic_scores}}
- rubric thresholds: {{output.rubric}}
- iteration count: {{output.iter}}
- max_iterations: 2
- blocking flag: {{output.critic_blocking}}

# Decision rules (first match wins)
1. If `safety == 0` OR `blocking == true` → `ABORT`
2. Else if every score meets threshold → `RETURN`
3. Else if `iter < max_iterations` → `RETRY`
4. Else → `RETURN_BEST`

# Output (strict JSON)
{
  "decision": "ABORT|RETURN|RETRY|RETURN_BEST",
  "reason": "<one sentence>",
  "next_iter_feedback": "<suggestions or null>"
}
```

## Variable Convention

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or env | mismatch → Correctness=0 (rule A7) |
| `{{user.detector_id}}` | user input | Echoed from `list-detectors` (rule A8) |
| `{{user.filter_name}}` | user input | Echoed from `list-filters` |
| `{{user.ip_set_id}}` | user input | Echoed from `list-ip-sets` |
| `{{user.threat_intel_set_id}}` | user input | Echoed from `list-threat-intel-sets` |
| `{{user.destination_id}}` | user input | Echoed from `list-publishing-destinations` |
| `{{user.finding_id}}` | user input | Echoed from `list-findings` |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | command, args, exit_code, result, post_state, errors |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of listed operation types |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial GCL prompt templates for `aws-guardduty-ops` |
```

---

## Task 16: Create `aws-guardduty-ops/assets/example-config.yaml`

**Files:**
- Create: `aws-guardduty-ops/assets/example-config.yaml`

- [ ] **Step 1: Write YAML config with anchors**

```yaml
# GuardDuty Configuration Examples (YAML Anchors)
# ================================================

# --- Shared Anchors ---
x-tags: &tags
  Tags:
    - Key: "ManagedBy"; Value: "AI-Agent"
    - Key: "Environment"; Value: "{{user.environment:production}}"

# --- Detector Configuration ---
detector_config:
  Enable: true
  FindingPublishingFrequency: "FIFTEEN_MINUTES"
  DataSources:
    S3Logs:
      Enable: true
    Kubernetes:
      AuditLogs:
        Enable: true
    MalwareProtection:
      ScanEc2InstanceWithFindings:
        Enable: true
  <<: *tags

# --- Filter Rule Configuration ---
filter_config:
  DetectorId: "{{user.detector_id}}"
  Name: "suppress-low-severity"
  Action: "ARCHIVE"
  Rank: 1
  FindingCriteria:
    Criterion:
      severity:
        Eq:
          - "2"  # Low severity

# --- IP Set Configuration ---
ip_set_config:
  DetectorId: "{{user.detector_id}}"
  Name: "TrustedIPs"
  Format: "TXT"
  Location: "s3://{{user.bucket}}/trusted-ips.txt"
  Activate: true

# --- Threat Intel Set Configuration ---
threat_intel_set_config:
  DetectorId: "{{user.detector_id}}"
  Name: "ThreatIntelFeed"
  Format: "TXT"
  Location: "s3://{{user.bucket}}/threat-intel.txt"
  Activate: true

# --- Publishing Destination Configuration ---
destination_config_s3:
  DetectorId: "{{user.detector_id}}"
  DestinationType: "S3"
  DestinationProperties:
    BucketName: "{{user.bucket}}"
    KmsKeyArn: "arn:aws:kms:{{env.AWS_DEFAULT_REGION}}:{{env.AWS_ACCOUNT_ID}}:key/{{user.kms_key_id}}"

destination_config_eventbridge:
  DetectorId: "{{user.detector_id}}"
  DestinationType: "EVENT_BRIDGE"
```

---

## Task 17: Modify `aws-securityhub-ops/SKILL.md` (Add GCL)

**Files:**
- Modify: `aws-securityhub-ops/SKILL.md`

- [ ] **Step 1: Add `metadata.gcl` block to frontmatter**

Locate the existing frontmatter (lines 1-33). After line 20 (`cli_applicability: dual-path`), add the `gcl` block BEFORE the `environment:` block:

```yaml
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
```

The frontmatter should now read:
```yaml
---
name: aws-securityhub-ops
description: >-
  Use when the user needs to manage AWS Security Hub resources: enable or
  disable Security Hub, create and manage insights and action targets,
  import and update findings, enable or disable security standards and
  controls, manage product subscriptions, create automation rules, or
  configure organization-level policies. Also use for Security Hub
  operational tasks such as compliance posture review, finding aggregation,
  cross-account finding analysis, or security score monitoring.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials,
  network access to Security Hub endpoints.
metadata:
  author: aws
  version: "1.1.0"
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
```

Also update `version: "1.0.0"` to `version: "1.1.0"` and `last_updated` to `"2026-06-08"`.

- [ ] **Step 2: Add `## Quality Gate (GCL)` section before `## Related Skills`**

Insert this section at the end of the file, before the existing `## Related Skills` section:

```markdown
## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-08, required). Every execution of
> `aws-securityhub-ops` MUST be wrapped by the Generator-Critic-Loop defined in
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

- `delete-insight` — `confirm=DELETE_INSIGHT {{user.insight_arn}}`
- `delete-action-target` — `confirm=DELETE_ACTION_TARGET {{user.action_target_arn}}`
- `disable-security-hub` — `confirm=DISABLE_SECURITY_HUB`
- `disable-import-findings-for-product` — `confirm=DISABLE_PRODUCT {{user.product_subscription_arn}}`
- `delete-automation-rule` — `confirm=DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource echo-back),
A9 (no secrets in trace), A10 (sts first command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.
```

- [ ] **Step 3: Verify frontmatter still parses correctly**

Run:
```bash
python3 -c "import yaml,re; yaml.safe_load(re.search(r'^---\n(.*?)\n---', open('aws-securityhub-ops/SKILL.md').read(), re.DOTALL).group(1))"
```

---

## Task 18: Create `aws-securityhub-ops/references/aws-cli-usage.md`

**Files:**
- Create: `aws-securityhub-ops/references/aws-cli-usage.md`

- [ ] **Step 1: Write Common JSON Paths, Command Map, and Common Patterns**

```markdown
# AWS CLI Usage — Security Hub

## Common JSON Paths (Centralized)

```
# Describe Hub:           .HubArn, .SubscribedAt, .AutoEnableControls
# Create Insight:         .InsightArn
# Get Findings:           .Findings[].{SchemaVersion,Id,ProductArn,Types,Severity,Confidence,Compliance,Remediation}
# Get Insights:           .Insights[].{Name,InsightArn,ResultValue}
# Get Action Targets:     .ActionTargets[].{Name,Description,ActionTargetArn}
# Get Standards:          .Standards[].{StandardsArn,Name,Description,EnabledByDefault}
# Get Controls:           .Controls[].{ControlId,ControlArn,Title,Description,ControlStatus,Compliance}
# Get Automation Rules:   .AutomationRules[].{RuleArn,RuleName,RuleOrder,RuleStatus,Actions}
# Get Configuration Policy: .ConfigurationPolicy.{ConfigurationPolicyIdentifier,UpdatedAt}
```

## Command Map

| Goal | CLI Command |
|------|-------------|
| Enable Security Hub | `aws securityhub enable-security-hub` |
| Disable Security Hub | `aws securityhub disable-security-hub` |
| Describe hub | `aws securityhub describe-hub` |
| Create insight | `aws securityhub create-insight` |
| Update insight | `aws securityhub update-insight` |
| Delete insight | `aws securityhub delete-insight` |
| Get findings | `aws securityhub get-findings` |
| Batch import findings | `aws securityhub batch-import-findings` |
| Batch update findings | `aws securityhub batch-update-findings` |
| Create action target | `aws securityhub create-action-target` |
| Delete action target | `aws securityhub delete-action-target` |
| Enable standard | `aws securityhub batch-enable-standards` |
| Disable standard | `aws securityhub batch-disable-standards` |
| Enable control | `aws securityhub update-standards-control` |
| Get enabled standards | `aws securityhub get-enabled-standards` |
| Get controls | `aws securityhub describe-standards-controls` |
| Create automation rule | `aws securityhub create-automation-rule` |
| Update automation rule | `aws securityhub update-automation-rule` |
| Delete automation rule | `aws securityhub delete-automation-rule` |
| Get configuration policy | `aws securityhub get-configuration-policy` |
| Update configuration policy | `aws securityhub update-configuration-policy` |

## Key CLI Conventions

### Output Format
Always use `--output json` for agent parsing.

### Region
Pass `--region` or rely on `AWS_DEFAULT_REGION`. Security Hub is regional.

## Common Patterns

### Enable Security Hub
```bash
aws securityhub enable-security-hub \
  --enable-default-standards \
  --region "{{user.region}}" \
  --output json
```

### Get Findings
```bash
aws securityhub get-findings \
  --filters '{"SeverityLabel":[{"Value":"CRITICAL","Comparison":"EQUALS"}]}' \
  --region "{{user.region}}" \
  --output json
```

### Batch Update Findings (Archive)
```bash
aws securityhub batch-update-findings \
  --finding-identifiers '[{"Id":"{{user.finding_id}}","ProductArn":"arn:aws:securityhub:{{user.region}}::product/aws/securityhub"}]' \
  --workflow '{"Status":"SUPPRESSED"}' \
  --region "{{user.region}}" \
  --output json
```

### Create Action Target
```bash
aws securityhub create-action-target \
  --name "SendToSNS" \
  --description "Send finding to SNS topic for remediation" \
  --id "SendToSNS" \
  --region "{{user.region}}" \
  --output json
```

### Enable Standard
```bash
aws securityhub batch-enable-standards \
  --standards-subscription-requests '[{"StandardsArn":"arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"}]' \
  --region "{{user.region}}" \
  --output json
```

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```

## Retry Strategy (CLI)

CLI has built-in retry logic. Configure in `~/.aws/config`:
```ini
[default]
retry_mode = adaptive
max_attempts = 3
```
```

---

## Task 19: Create `aws-securityhub-ops/references/boto3-sdk-usage.md`

**Files:**
- Create: `aws-securityhub-ops/references/boto3-sdk-usage.md`

- [ ] **Step 1: Write boto3 patterns (no docstrings)**

```markdown
# boto3 SDK Usage — Security Hub

## Client Initialization

```python
import boto3
import os

client = boto3.client(
    'securityhub',
    region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
)
```

## Operation Patterns

### Enable Security Hub

```python
response = client.enable_security_hub(EnableDefaultStandards=True)
print("Security Hub enabled")
```

### Get Findings

```python
response = client.get_findings(
    Filters={
        'SeverityLabel': [{'Value': 'CRITICAL', 'Comparison': 'EQUALS'}]
    },
    MaxResults=10
)
for finding in response.get('Findings', []):
    print(f"{finding['Id']}: {finding['Title']} ({finding['Severity']['Label']})")
```

### Batch Update Findings

```python
response = client.batch_update_findings(
    FindingIdentifiers=[
        {
            'Id': '{{user.finding_id}}',
            'ProductArn': 'arn:aws:securityhub:{{user.region}}::product/aws/securityhub'
        }
    ],
    Workflow={'Status': 'SUPPRESSED'}
)
print(f"Updated: {response['ProcessedFindings']}")
```

### Create Action Target

```python
response = client.create_action_target(
    Name='SendToSNS',
    Description='Send finding to SNS topic for remediation',
    Id='SendToSNS'
)
print(f"Action Target: {response['ActionTargetArn']}")
```

### Enable Standard

```python
response = client.batch_enable_standards(
    StandardsSubscriptionRequests=[
        {
            'StandardsArn': 'arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0'
        }
    ]
)
print(f"Enabled: {response['StandardsSubscriptions']}")
```

## Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = client.enable_security_hub()
except ClientError as e:
    code = e.response['Error']['Code']
    if code == 'ResourceConflictException':
        print("Security Hub already enabled.")
    elif code == 'AccessDeniedException':
        print("Insufficient IAM permissions.")
    elif code == 'ThrottlingException':
        pass  # Retry with backoff
    else:
        raise
```

## Common Error Codes

| Error Code | HTTP | Action |
|------------|------|--------|
| ResourceConflictException | 409 | Resource already in requested state |
| ResourceNotFoundException | 404 | Verify ARN/ID |
| AccessDeniedException | 403 | HALT; check IAM permissions |
| InvalidAccessException | 403 | HALT; check IAM permissions |
| LimitExceededException | 400 | HALT; request quota increase |
| ThrottlingException | 429 | Backoff and retry |
| InternalException | 500 | Retry 3x; HALT |

## Retry Configuration

```python
from botocore.config import Config

config = Config(retries={'max_attempts': 3, 'mode': 'adaptive'})
client = boto3.client('securityhub', config=config)
```
```

---

## Task 20: Create `aws-securityhub-ops/references/core-concepts.md`

**Files:**
- Create: `aws-securityhub-ops/references/core-concepts.md`

- [ ] **Step 1: Write service overview, resources, architecture, lifecycle, dependencies**

```markdown
# Core Concepts — Security Hub

## What is AWS Security Hub

- **Purpose**: Centralized security and compliance center aggregating findings from AWS services and partners
- **Category**: Security
- **Console**: https://console.aws.amazon.com/securityhub/
- **Docs**: https://docs.aws.amazon.com/securityhub/

## Primary Resources

| Resource | Description | Console Path |
|----------|-------------|--------------|
| Hub | Security Hub instance per region | /securityhub/home |
| Finding | Security issue from integrated product | /securityhub/home#/findings |
| Insight | Saved filter for findings | /securityhub/home#/insights |
| Action Target | Custom response workflow | Settings → Custom actions |
| Standard | Compliance framework (CIS, PCI DSS, NIST) | /securityhub/home#/standards |
| Control | Individual security check within a standard | Standard detail page |
| Automation Rule | Automated finding update | Settings → Automation |
| Configuration Policy | Organization-level policy | Settings → Configuration |

## Hub Lifecycle

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| Enabled | Active aggregation and scoring | All operations |
| Disabled | Aggregation stopped | Enable, delete |
| Non-existent | Not enabled | Enable |

## Architecture & Limits

### Region Availability
- Regional service
- Available in most AWS regions

### Quotas (Service Limits)

| Quota | Default | Adjustable |
|-------|---------|------------|
| Insights per region | 100 | Yes |
| Action targets per region | 100 | Yes |
| Automation rules per region | 100 | Yes |
| Standards per region | 5 | No |
| Findings import rate | 1000/sec | Yes |

## Dependencies

| Dependency | Required? | Skill |
|------------|-----------|-------|
| IAM Role | Yes (service-linked) | `aws-iam-ops` |
| GuardDuty | Optional (findings source) | `aws-guardduty-ops` |
| Config | Optional (compliance source) | `aws-config-ops` |
| Inspector | Optional (findings source) | `aws-inspector-ops` |
| EventBridge | Optional (automation target) | `aws-eventbridge-ops` |
| Organizations | Optional (central config) | `aws-organizations-ops` |

## Pricing Model (Summary)

- **Per finding ingested**: First 10,000 free, then tiered
- **Security Hub checks**: Per check per account per region
- **Free tier**: 30-day trial
- **Estimator**: https://calculator.aws/#/

## Best Practices

### Security
- Enable in all active regions
- Enable CIS AWS Foundations Benchmark standard
- Use automation rules to suppress false positives
- Integrate with EventBridge for automated response

### Compliance
- Regular review of failed controls
- Use insights to track compliance trends
- Export findings to S3 for long-term retention

### Cost
- Disable in unused regions
- Use suppression rules to reduce noise
- Archive old findings
```

---

## Task 21: Create `aws-securityhub-ops/references/troubleshooting.md`

**Files:**
- Create: `aws-securityhub-ops/references/troubleshooting.md`

- [ ] **Step 1: Write compact error tables and diagnostic flows**

```markdown
# Troubleshooting — Security Hub

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| ResourceConflictException (409) | Resource already in requested state |
| ResourceNotFoundException (404) | Verify ARN/ID |
| AccessDeniedException (403) | HALT — check IAM permissions |
| InvalidAccessException (403) | HALT — check IAM permissions |
| LimitExceededException (400) | HALT — request quota increase |
| ThrottlingException (429) | Backoff and retry (max 3x) |
| InternalException (500) | Retry 3x; HALT |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify region**: Check `AWS_DEFAULT_REGION` or pass `--region`
3. **Describe hub**: `aws securityhub describe-hub`
4. **Check standards**: `aws securityhub get-enabled-standards`
5. **Check findings**: `aws securityhub get-findings --max-results 1`
6. **Verify IAM permissions**: Ensure `securityhub:*` or specific actions allowed

## Common Issues

### Security Hub Already Enabled

| Symptom | Cause | Resolution |
|---------|-------|------------|
| ResourceConflictException | Hub already enabled | Use existing hub or disable first |

### Findings Not Appearing

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No findings | Product not integrated | Enable product integration |
| No findings | Region mismatch | Check source service region |

### Standard Enablement Fails

| Symptom | Cause | Resolution |
|---------|-------|------------|
| AccessDenied | Missing IAM permission | Add `securityhub:BatchEnableStandards` |
| LimitExceeded | Too many standards | Disable unused standard first |

## Support Escalation Criteria

| Scenario | Severity | Action |
|----------|----------|--------|
| Production security finding not aggregating | Critical | Immediate support ticket |
| Persistent InternalException | High | Support ticket with correlation IDs |
| Compliance standard not enabling | Medium | Check IAM; contact support |
```

---

## Task 22: Create `aws-securityhub-ops/references/rubric.md`

**Files:**
- Create: `aws-securityhub-ops/references/rubric.md`

- [ ] **Step 1: Write full GCL rubric**

```markdown
# Security Hub Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric for `aws-securityhub-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `disable-security-hub` / `delete-insight` | 0 / 0.5 / 1 | Verifies `InsightArn` / `ActionTargetArn` / `StandardsArn` / `AutomationRuleArn` match the user request. Read back via `get-findings` / `get-insights` / `describe-action-targets` and compare. Resource id must be echoed from a lookup (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`disable-security-hub`, `delete-insight`, `delete-action-target`, `disable-import-findings-for-product`, `delete-automation-rule`, `update-configuration-policy`) MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `enable-security-hub` returns `ResourceConflictException` if already enabled — acceptable terminal state. `disable-security-hub` is idempotent. `batch-update-findings` is idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws securityhub <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-hub` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: insight count ≤ 100, action target count ≤ 100, automation rule count ≤ 100, standards count ≤ 5. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `enable-security-hub` | Correctness, Spec Compliance | One hub per region |
| `describe-hub` / `get-findings` | Correctness | Read-only |
| `disable-security-hub` | Correctness, Safety, **Traceability** | `confirm=DISABLE_SECURITY_HUB` required |
| `create-insight` | Correctness, Spec Compliance | Insight count ≤ 100 |
| `update-insight` | Correctness | Non-destructive |
| `delete-insight` | Correctness, **Safety** | `confirm=DELETE_INSIGHT {{user.insight_arn}}` required |
| `create-action-target` | Correctness, Spec Compliance | Action target count ≤ 100 |
| `delete-action-target` | Correctness, **Safety** | `confirm=DELETE_ACTION_TARGET {{user.action_target_arn}}` required |
| `batch-enable-standards` | Correctness, Spec Compliance | Standards count ≤ 5 |
| `batch-disable-standards` | Correctness, **Safety** | `confirm=DISABLE_STANDARD {{user.standard_arn}}` required |
| `batch-import-findings` | Correctness | Verify finding format |
| `batch-update-findings` | Correctness | Idempotent |
| `create-automation-rule` | Correctness, Spec Compliance | Rule count ≤ 100 |
| `delete-automation-rule` | Correctness, **Safety** | `confirm=DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}` required |
| `disable-import-findings-for-product` | Correctness, **Safety** | `confirm=DISABLE_PRODUCT {{user.product_subscription_arn}}` required |
| `update-configuration-policy` | Correctness, **Safety** | `confirm=UPDATE_CONFIG_POLICY {{user.policy_id}}` required |

## Safety special cases (auto-fail)

- `disable-security-hub` without `confirm=DISABLE_SECURITY_HUB` in trace →
  **Safety = 0 → ABORT**.
- `delete-insight` without `confirm=DELETE_INSIGHT {{user.insight_arn}}` in trace →
  **Safety = 0 → ABORT**.
- `delete-action-target` without `confirm=DELETE_ACTION_TARGET {{user.action_target_arn}}` in trace →
  **Safety = 0 → ABORT**.
- `delete-automation-rule` without `confirm=DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}` in trace →
  **Safety = 0 → ABORT**.
- `disable-import-findings-for-product` without `confirm=DISABLE_PRODUCT {{user.product_subscription_arn}}` in trace →
  **Safety = 0 → ABORT**.
- `batch-disable-standards` without `confirm=DISABLE_STANDARD {{user.standard_arn}}` in trace →
  **Safety = 0 → ABORT**.
- `update-configuration-policy` without `confirm=UPDATE_CONFIG_POLICY {{user.policy_id}}` in trace →
  **Safety = 0 → ABORT**.
- Resource ARN/ID in request not echoed from a lookup →
  **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` →
  **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- `create-insight` called when insight count ≥ 100 →
  **Spec Compliance = 0 → ABORT**.

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial rubric for `aws-securityhub-ops` |
```

---

## Task 23: Create `aws-securityhub-ops/references/prompt-templates.md`

**Files:**
- Create: `aws-securityhub-ops/references/prompt-templates.md`

- [ ] **Step 1: Write Generator, Critic, Orchestrator prompts**

```markdown
# GCL Prompt Templates — `aws-securityhub-ops`

## 1. Generator Prompt (G)

```text
You are the **Generator** for the `aws-securityhub-ops` skill.

# Inputs
- user request: {{user.request}}
- previous Critic feedback: {{output.critic_feedback}}
- rubric: {{output.rubric}}
- operation type: {{output.operation}}
  # one of: enable-security-hub | disable-security-hub | describe-hub |
  #         create-insight | update-insight | delete-insight | get-insights |
  #         get-findings | batch-import-findings | batch-update-findings |
  #         create-action-target | delete-action-target | describe-action-targets |
  #         batch-enable-standards | batch-disable-standards | get-enabled-standards |
  #         describe-standards-controls | update-standards-control |
  #         create-automation-rule | update-automation-rule | delete-automation-rule |
  #         disable-import-findings-for-product |
  #         get-configuration-policy | update-configuration-policy

# Required behavior
1. Follow `references/aws-cli-usage.md` and `references/core-concepts.md`.
2. Primary: `aws securityhub <op> --output json --region "{{user.region}}"`
3. **First command MUST be:** `aws sts get-caller-identity --output json` (rule A10).
4. For destructive ops, trace MUST record exact confirmation:
   - `disable-security-hub`: `confirm=DISABLE_SECURITY_HUB`
   - `delete-insight`: `confirm=DELETE_INSIGHT {{user.insight_arn}}`
   - `delete-action-target`: `confirm=DELETE_ACTION_TARGET {{user.action_target_arn}}`
   - `delete-automation-rule`: `confirm=DELETE_AUTOMATION_RULE {{user.automation_rule_arn}}`
   - `disable-import-findings-for-product`: `confirm=DISABLE_PRODUCT {{user.product_subscription_arn}}`
   - `batch-disable-standards`: `confirm=DISABLE_STANDARD {{user.standard_arn}}`
   - `update-configuration-policy`: `confirm=UPDATE_CONFIG_POLICY {{user.policy_id}}`
5. NEVER include credentials in trace (rule A9).

# Output (strict JSON)
{
  "command": "<exact call>",
  "args": { ... },
  "exit_code": <int>,
  "result": "<excerpt, max 2 KB>",
  "post_state": {
    "hub_arn": "...",
    "status": "ENABLED|DISABLED",
    "finding_count": <int>,
    "standards": ["..."]
  },
  "errors": [],
  "notes": "<≤ 200 chars>"
}

# Constraint
Do NOT self-score. Do NOT modify the rubric.
```

## 2. Critic Prompt (C)

```text
You are the **Critic** for `aws-securityhub-ops`.
You will NOT see the original user request. Judge ONLY what was done.

# Inputs
- generator output: {{output.generator_output}}
- trace: {{output.trace}}
- rubric: {{output.rubric}}
- operation type: {{output.operation}}

# Output (strict JSON)
{
  "scores": { "correctness": 0|0.5|1, "safety": 0|0.5|1, "idempotency": 0|0.5|1, "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1 },
  "justifications": { ... },
  "suggestions": ["≤ 3 improvements"],
  "blocking": <true if safety/correctness = 0>
}

# Hard rules
- Safety = 0 if destructive op lacks confirmation in trace.
- Correctness = 0 if resource id not echoed from lookup (rule A8).
- Correctness = 0 if region mismatch (rule A7).
- Traceability = 0 if sts not first command (rule A10).
- Spec Compliance = 0 if insight/action-target/automation-rule count exceeded.
```

## 3. Orchestrator Decider Prompt (O)

```text
You are the **Orchestrator**.

# Inputs
- previous Critic scores: {{output.critic_scores}}
- rubric thresholds: {{output.rubric}}
- iteration count: {{output.iter}}
- max_iterations: 2
- blocking flag: {{output.critic_blocking}}

# Decision rules (first match wins)
1. If `safety == 0` OR `blocking == true` → `ABORT`
2. Else if every score meets threshold → `RETURN`
3. Else if `iter < max_iterations` → `RETRY`
4. Else → `RETURN_BEST`

# Output (strict JSON)
{
  "decision": "ABORT|RETURN|RETRY|RETURN_BEST",
  "reason": "<one sentence>",
  "next_iter_feedback": "<suggestions or null>"
}
```

## Variable Convention

| Placeholder | Resolved from | Notes |
|---|---|---|
| `{{user.request}}` | agent runtime | sanitized |
| `{{user.safety_confirm}}` | explicit user confirmation | required for destructive ops |
| `{{user.region}}` | user input or env | mismatch → Correctness=0 (rule A7) |
| `{{user.insight_arn}}` | user input | Echoed from `get-insights` (rule A8) |
| `{{user.action_target_arn}}` | user input | Echoed from `describe-action-targets` |
| `{{user.automation_rule_arn}}` | user input | Echoed from `list-automation-rules` |
| `{{user.standard_arn}}` | user input | Echoed from `get-enabled-standards` |
| `{{user.product_subscription_arn}}` | user input | Echoed from `describe-products` |
| `{{user.policy_id}}` | user input | Echoed from `get-configuration-policy` |
| `{{env.AWS_ACCESS_KEY_ID}}` | runtime env | NEVER prompt user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | runtime env | NEVER log (rule A9) |
| `{{output.rubric}}` | `references/rubric.md` | injected as literal block |
| `{{output.generator_output}}` | previous Generator run | empty on iter 1 |
| `{{output.trace}}` | execution trace buffer | command, args, exit_code, result, post_state, errors |
| `{{output.critic_scores}}` | previous Critic run | empty on iter 1 |
| `{{output.critic_blocking}}` | previous Critic run | empty on iter 1 |
| `{{output.iter}}` | Orchestrator counter | starts at 1 |
| `{{output.operation}}` | Orchestrator classification | one of listed operation types |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial GCL prompt templates for `aws-securityhub-ops` |
```

---

## Task 24: Create `aws-securityhub-ops/assets/example-config.yaml`

**Files:**
- Create: `aws-securityhub-ops/assets/example-config.yaml`

- [ ] **Step 1: Write YAML config with anchors**

```yaml
# Security Hub Configuration Examples (YAML Anchors)
# ===================================================

# --- Shared Anchors ---
x-tags: &tags
  Tags:
    - Key: "ManagedBy"; Value: "AI-Agent"
    - Key: "Environment"; Value: "{{user.environment:production}}"

# --- Hub Configuration ---
hub_config:
  EnableDefaultStandards: true
  Tags:
    - Key: "ManagedBy"; Value: "AI-Agent"

# --- Insight Configuration ---
insight_config:
  Name: "Critical Findings"
  Filters:
    SeverityLabel:
      - Comparison: EQUALS
        Value: CRITICAL
  GroupByAttribute:
    - Type

# --- Action Target Configuration ---
action_target_config:
  Name: "SendToSNS"
  Description: "Send finding to SNS topic for remediation"
  Id: "SendToSNS"

# --- Automation Rule Configuration ---
automation_rule_config:
  RuleName: "suppress-low-severity"
  RuleOrder: 1
  RuleStatus: ENABLED
  Criteria:
    SeverityLabel:
      - Comparison: EQUALS
        Value: LOW
  Actions:
    - Type: FINDING_FIELDS_UPDATE
      FindingFieldsUpdate:
        Workflow:
          Status: SUPPRESSED

# --- Standards Configuration ---
standards_config:
  StandardsSubscriptionRequests:
    - StandardsArn: "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"
    - StandardsArn: "arn:aws:securityhub:::ruleset/pci-dss/v/3.2.1"
    - StandardsArn: "arn:aws:securityhub:::ruleset/nist-800-53/v/5.0.0"
```

---

## Task 25: Update `README.md` and `README_cn.md`

**Files:**
- Modify: `README.md`
- Modify: `README_cn.md`

- [ ] **Step 1: Add three new skills to `README.md` "Existing Skills" section**

Find the existing skills table/list in `README.md`. Add entries for the three new skills in alphabetical order within the list:

For `README.md`, add after `aws-kms-ops` section (alphabetical order):

```markdown
├── aws-opensearch-ops/            # OpenSearch Service Operations Skill
│   ├── SKILL.md                   # Concise - Domain/Snapshot/VPC Endpoint ops
│   ├── references/
│   │   ├── aws-cli-usage.md       # OpenSearch CLI commands
│   │   ├── boto3-sdk-usage.md     # OpenSearch SDK code examples
│   │   ├── core-concepts.md       # OpenSearch architecture/quota
│   │   ├── troubleshooting.md     # OpenSearch troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Domain/Snapshot/VPC Endpoint config

├── aws-guardduty-ops/             # GuardDuty Operations Skill
│   ├── SKILL.md                   # Concise - Detector/Filter/Finding ops
│   ├── references/
│   │   ├── aws-cli-usage.md       # GuardDuty CLI commands
│   │   ├── boto3-sdk-usage.md     # GuardDuty SDK code examples
│   │   ├── core-concepts.md       # GuardDuty architecture/quota
│   │   ├── troubleshooting.md     # GuardDuty troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Detector/Filter/IP Set config
```

For `aws-securityhub-ops`, update the existing entry to show it now has rubric and prompt-templates:

```markdown
├── aws-securityhub-ops/           # Security Hub Operations Skill
│   ├── SKILL.md                   # Concise - Hub/Insight/Finding/Standard ops
│   ├── references/
│   │   ├── aws-cli-usage.md       # Security Hub CLI commands
│   │   ├── boto3-sdk-usage.md     # Security Hub SDK code examples
│   │   ├── core-concepts.md       # Security Hub architecture/quota
│   │   ├── troubleshooting.md     # Security Hub troubleshooting
│   │   ├── rubric.md              # GCL scoring rubric
│   │   └── prompt-templates.md    # GCL prompt templates
│   └── assets/
│       └── example-config.yaml    # Hub/Insight/Automation Rule config
```

- [ ] **Step 2: Update AIOps section in `README.md` if it references per-skill versions**

Check if there's an AIOps section that lists skills. If so, add the three new skills.

- [ ] **Step 3: Sync changes to `README_cn.md`**

Apply the same structural changes to `README_cn.md`, translating skill descriptions to Chinese.

---

## Task 26: Self-Reflection Round 1 (Charter + TE + GCL Verification)

**Files:**
- Read: All created/modified files

- [ ] **Step 1: Verify Charter C1-C6 for all three skills**

For each skill (`aws-opensearch-ops`, `aws-guardduty-ops`, `aws-securityhub-ops`):

Run:
```bash
# C1: Frontmatter
head -3 aws-opensearch-ops/SKILL.md | grep "^---"
python3 -c "import yaml,re; yaml.safe_load(re.search(r'^---\n(.*?)\n---', open('aws-opensearch-ops/SKILL.md').read(), re.DOTALL).group(1))"

# C2: SHOULD/SHOULD NOT
grep -c "SHOULD Use When" aws-opensearch-ops/SKILL.md
grep -c "SHOULD NOT Use When" aws-opensearch-ops/SKILL.md

# C3: Trigger & Scope
grep -c "Trigger & Scope" aws-opensearch-ops/SKILL.md

# C4: Variable Convention
grep -c "Variable Convention" aws-opensearch-ops/SKILL.md

# C5: Safety Gates
grep -c "Safety Gates" aws-opensearch-ops/SKILL.md

# C6: Token Efficiency (check for static tables, docstrings, etc.)
# TE-1: No hardcoded version/port/state tables in SKILL.md
grep -c "## Version" aws-opensearch-ops/SKILL.md || true
# TE-2: boto3-sdk-usage.md has no docstrings
grep -c '"""' aws-opensearch-ops/references/boto3-sdk-usage.md || true
# TE-3: Compact error tables
grep -c "## Common Error" aws-opensearch-ops/references/troubleshooting.md
# TE-4: Centralized JSON paths
grep -c "Common JSON Paths" aws-opensearch-ops/references/aws-cli-usage.md
# TE-5: YAML anchors
grep -c "&" aws-opensearch-ops/assets/example-config.yaml
# TE-6: No duplicate flows (SKILL.md has full flow, other files don't repeat)
```

Repeat for `aws-guardduty-ops` and `aws-securityhub-ops`.

- [ ] **Step 2: Verify GCL scaffolding completeness**

For each skill:
1. `references/rubric.md` exists and has 5 dimensions table
2. `references/prompt-templates.md` exists and has G/C/O sections
3. `SKILL.md` has `## Quality Gate (GCL)` section
4. Frontmatter has `metadata.gcl` block
5. Every destructive op in `## Scope` table has a matching confirmation string in `## Safety Gates` and `## Quality Gate (GCL)`

- [ ] **Step 3: Verify delegation references point to existing skills**

For each `SHOULD NOT Use When` and `Cross-Skill Orchestration` table:
```bash
ls aws-iam-ops/ aws-kms-ops/ aws-vpc-ops/ aws-cloudwatch-ops/ aws-s3-ops/ aws-eventbridge-ops/ aws-config-ops/ aws-guardduty-ops/ aws-securityhub-ops/ 2>/dev/null
```

