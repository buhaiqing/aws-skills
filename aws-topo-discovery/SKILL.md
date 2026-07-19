---
name: aws-topo-discovery
description: >-
  Use this skill to automatically discover and generate AWS network topology and resource inventory reports,
  and export cloud resources as Terraform HCL for declarative infrastructure archives.
  Triggers when the user asks to "scan network resources", "generate topology map", "inventory VPC resources",
  "check cloud resources", or "audit network structure", as well as "export as terraform", "create baseline snapshots",
  "generate HCL", or "audit infrastructure drift" for a specific AWS account.
  Supports both summary (brief) and detailed inventory modes, plus on-demand HCL export and periodic baseline management.
  Keywords: network topology, resource inventory, VPC scan, cloud resource scan, network audit,
  Terraform HCL export, infrastructure baseline, drift detection.
  Do NOT use for resource creation, modification, deletion, or troubleshooting. Read-only discovery only.
license: MIT
compatibility: >-
  AWS CLI v2, valid AWS credentials (IAM ReadOnlyAccess or equivalent),
  network access to AWS endpoints. Read-only operations (Describe/List/Get) strictly enforced.
metadata:
  author: aws
  version: "1.1.0"
  last_updated: "2026-06-13"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  type: cross-product-discovery
  cli_applicability: cli-only
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
    - AWS_PROFILE
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# AWS Network Topology Discovery Skill

## Common JSON Paths (Centralized)

```
# VPC:           .Vpcs[].{VpcId,CidrBlock,Tags}
# Subnet:        .Subnets[].{SubnetId,CidrBlock,AvailabilityZone,VpcId}
# ELB:           .LoadBalancers[].{LoadBalancerName,DNSName,Type,VpcId}
# EIP:           .Addresses[].{AllocationId,PublicIp,InstanceId}
# NAT GW:        .NatGateways[].{NatGatewayId,State,SubnetId}
# EC2:           .Reservations[].Instances[].{InstanceId,InstanceType,State.Name,PrivateIpAddress}
# RDS:           .DBInstances[].{DBInstanceIdentifier,Engine,Endpoint.Address}
# EKS:           .clusters[]
# Lambda:        .Functions[].{FunctionName,Runtime,VpcConfig}
# SG:            .SecurityGroups[].{GroupId,GroupName,VpcId}
# S3:            .Buckets[].Name
# IAM Role:      .Roles[].RoleName
```

Full jq mappings: `references/execution-commands.md` §JSON Output Path Mapping.

## READ-ONLY PRINCIPLE

The core design principle of this Skill is **Absolute Read-Only**. Before executing any operation, the Agent MUST enforce the following red lines:

| Rule | Description |
|------|------|
| **NO Write Operations** | Never execute any `Create`, `Update`, `Modify`, `Delete`, `Associate`, `Disassociate`, `Authorize`, `Revoke`, `Run`, `Terminate` operation |
| **NO State Changes** | Never alter the state of any cloud resource, including but not limited to instance start/stop, security group rule changes, EIP association, etc. |
| **NO Credential Exposure** | Never output full AK/Secret; output must be masked as `AKIA******SECRET` or `***` |
| **Read-Only API Only** | Only invoke `Describe*`, `List*`, `Get*` APIs (see [Safety Gate](references/safety-gate.md)) |

**Violation of this principle = critical security breach. HALT immediately and report to the user.**

## Overview

`aws-topo-discovery` is a **cross-product network discovery tool** that automatically scans VPC network structures and associated resources (EC2/RDS/ELB/NAT/Elastic IP/EKS/Lambda/S3/Security Groups) under an AWS account, and generates structured network topology maps and resource inventory reports.

### Core Features

| Feature | Description |
|---------|-------------|
| **Interactive Mode Selection** | User chooses between "Brief" (VPC/Subnet/ELB/EIP summary) or "Detailed" (full resource inventory) |
| **Tree Topology View** | VPC → Subnet → Resource tree structure per template |
| **Multi-Format Output** | ASCII tree + Mermaid diagram + Markdown report |
| **Multi-Document Generation** | Optional single-file or split files (topology / inventory / summary) |
| **Template Engine** | Based on `templates/*.md` files with variable substitution |
| **Health overlay** | `--health-json` from `aws-aiops-cruise` — CRITICAL/WARNING nodes highlighted in Mermaid (v1.9+: no blanket green) |
| **CloudFront origin graph** | `cf-origins-collector.py` — CF→ALB/S3/API GW/Lambda URL edges, Origin Group failover (parallel fetch, detailed/overlay only) |

### Relationship with Existing Skills

| Relationship | Description |
|--------------|-------------|
| **Does Not Replace** | This Skill does not replace any product-level Skill (e.g., `aws-ec2-ops`, `aws-vpc-ops`) |
| **Composable Calls** | This Skill aggregates cross-product topology by calling read-only APIs of each product |
| **Discovery vs Operations** | This Skill handles "discovery"; product Skills handle "operations" — guide users to the corresponding product Skill for resource changes |
| **AIOps Integration** | `aws-aiops-cruise` invokes `topo-scan.sh` via `cruise-topo-render.py`; health overlay from `cruise-*.json` |

## Trigger & Scope

### SHOULD Use When

- User needs to view/scan/discover/audit AWS network topology
- User needs a resource inventory or asset list under a VPC
- User needs to know which VPCs/EIPs/ELBs/EC2 instances exist in the account
- User needs a network architecture diagram or resource report
- User needs to export cloud resources as Terraform HCL (`export-hcl`)
- User needs to create an infrastructure baseline snapshot (`baseline`)
- User needs to compare configuration changes between two baselines (`baseline-diff`)
- User needs cross-account resource scanning (via `--assume-role`)
- Keywords: network topology, VPC structure, resource inventory, cloud resource scan, Terraform HCL export, infrastructure baseline
- User says "scan the network", "show me what resources exist", "generate a topology map", "export HCL", "create a baseline"

### SHOULD NOT Use When

- User needs to create/modify/delete resources → delegate to the corresponding product Skill
- User needs to troubleshoot resource failures or performance issues → delegate to monitoring/diagnostic Skills
- User needs billing/cost queries → no in-repo skill; use AWS Cost Explorer / Billing console directly
- User needs to configure security policies → delegate to `aws-iam-ops` / `aws-waf-ops`
- User needs to provision cloud resources via `terraform apply` → delegate to the Terraform workflow

## Delegation Rules

| Capability | Delegate To | Notes |
|------------|-------------|-------|
| GCL quality gate | Self (`references/gcl-rubric.md`) | Optional per AGENTS.md §11.5; `max_iter=3`; read-only — Safety must = 1 |

## Quality Gate (GCL)

This Skill follows the AGENTS.md §11 Generator-Critic-Loop quality gate (**optional**, `max_iter=3`).

### Rubric Dimensions

See [references/gcl-rubric.md](references/gcl-rubric.md).

| Dimension | Weight | Description |
|---|---|---|
| **Correctness** | 25% | Topology relationships and resource inventory match actual state |
| **Safety** | 30% | Read-only only; any write operation scores 0 |
| **Idempotency** | 15% | Repeated scans with the same input produce consistent results |
| **Traceability** | 20% | Report includes full execution context (commands, parameters, output paths) |
| **Spec Compliance** | 10% | Follows manifest-schema and field-mapping conventions |

### Sub-Mode Rubric

| Sub-Mode | Correctness Focus | Safety Checkpoint |
|----------|-------------------|-------------------|
| scan-topo | Complete output format, accurate topology relationships | Read-only gate |
| export-hcl | Field-mapping accuracy | No sensitive data leakage |
| baseline | Complete directory structure | No data deletion |
| baseline-diff | Diff accuracy | Read-only diff |
| get-causal-graph | Service edges and latency data from X-Ray/CloudWatch | Read-only — no write APIs |
| find-root-cause | Correct ranking of upstream suspects | Read-only inference only |

### GCL Prompt

Generator → Critic loop details are in [references/gcl-rubric.md](references/gcl-rubric.md), following the standard AGENTS.md §11 workflow.

## Pre-flight Interaction (User Decisions)

Before running a scan, **MUST** confirm the following options with the user:

```
📋 Topology Scan Configuration:

1. Report mode (required):
   [1] Brief — VPC + Subnet + ELB/EIP + resource count summary (default)
   [2] Detailed — Brief + full attributes and inventory for all EC2/RDS/EKS/Lambda/Security Groups

2. Topology format:
   [1] ASCII tree — terminal-friendly, directly readable (default)
   [2] Mermaid diagram — flow/render support, suitable for embedding in docs
   [3] Both

3. Output structure:
   [1] Single file — all content written to report.md (default)
   [2] Multi-file — split into topology.md + inventory.md + summary.md

4. Project name/identifier (optional):
   [input]: Custom report title prefix (defaults to auto-extract from VPC name)

5. Health overlay (optional, integrates with `aws-aiops-orchestrator`):
   [input]: Inspection JSON report path (automatically overlays health status onto topology)

Reply with option numbers or descriptions to confirm before scanning begins.
```

## Variable Convention

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{env.AWS_ACCESS_KEY_ID}}` | AK ID | From runtime env, NEVER ask user |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | AK Secret | From runtime env, NEVER exposed |
| `{{env.AWS_DEFAULT_REGION}}` | Region | From runtime env |
| `{{env.AWS_SESSION_TOKEN}}` | Session Token | From runtime env, for STS temporary credentials |
| `{{env.AWS_PROFILE}}` | Named Profile | From runtime env, overrides explicit keys |
| `{{user.report_mode}}` | Brief/Detailed | User decision (step 1) |
| `{{user.topology_format}}` | ASCII/Mermaid | User decision (step 2) |
| `{{user.output_structure}}` | Single-file/Multi-file | User decision (step 3) |
| `{{user.project_name}}` | Project name | User input or extracted from VPC name |
| `{{output.topology_data}}` | Scan results | From CLI execution |
| `{{output.vpc_name}}` | VPC name | From DescribeVpcs response |

## Execution Flows

### Phase 1: Pre-flight Safety Check

**MANDATORY before any CLI execution:**

1. Verify credentials exist:
   ```bash
   test -n "$AWS_ACCESS_KEY_ID" && test -n "$AWS_SECRET_ACCESS_KEY" || { echo "ERROR: Credentials not set"; exit 1; }
   ```

2. Check CLI available:
   ```bash
   command -v aws >/dev/null || { echo "ERROR: AWS CLI not found"; exit 1; }
   ```

3. Verify identity (read-only):
   ```bash
   aws sts get-caller-identity --output json
   ```

4. Verify read-only mode:
   - Scan the planned command list
   - Reject any command matching: `(Create|Update|Modify|Delete|Associate|Disassociate|Authorize|Revoke|Stop|Start|Reboot|Run|Terminate|Invoke|Attach|Detach|Release)`
   - If found → HALT and report to user

5. Test API connectivity (read-only):
   ```bash
   aws ec2 describe-regions --region "$AWS_DEFAULT_REGION" --output json >/dev/null 2>&1 || { echo "ERROR: API check failed"; exit 1; }
   ```

#### Output Format (Token Efficiency)

All CLI command JSON output MUST be filtered with `--query` or `jq` to the minimum required fields, avoiding full JSON dumps that waste tokens:

```bash
# Before: full JSON output (potentially 100+ lines)
aws ec2 describe-instances --region $AWS_DEFAULT_REGION --output json

# After: only ID + Name + Type + Status
aws ec2 describe-instances --region $AWS_DEFAULT_REGION --output json \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,InstanceName:Tags[?Key==`Name`].Value|[0],InstanceType:InstanceType,State:State.Name}'
```

Per-API field-filtering rules are in the JSON output path mappings in `references/execution-commands.md`.

### Phase 2: Parallel Data Collection

Execute CLI commands in parallel (background) for speed.

> **Note:** `topo-scan.sh` implements multi-VPC scanning, health overlay, and Mermaid diagram generation; see `scripts/topo-scan.sh` for the full implementation. Commands below write full JSON to `/tmp/topo_*.json` for script consumption. Filter with `--query` or `jq` only when piping JSON directly into agent context (see Phase 1).

```bash
# VPC & Subnet (Foundation) — wait for VPCs before querying Subnets
aws ec2 describe-vpcs --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_vpcs.json &
PID_VPC=$!

# Query ELB/NAT/EIP in parallel
aws elbv2 describe-load-balancers --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_elbs.json &
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=*" --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_nats.json &
aws ec2 describe-addresses --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_eips.json &

# Query Subnets after VPCs return
wait $PID_VPC
FIRST_VPC_ID=$(python3 -c "import json;d=json.load(open('/tmp/topo_vpcs.json'));print(d.get('Vpcs',[{}])[0].get('VpcId',''))" 2>/dev/null)
if [ -n "$FIRST_VPC_ID" ]; then
  aws ec2 describe-subnets --filters "Name=vpc-id,Values=$FIRST_VPC_ID" --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_subnets.json &
fi

# EC2 Instances (Optional for detailed mode)
if [ "$REPORT_MODE" = "detailed" ]; then
  aws ec2 describe-instances --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_ec2.json &
  aws ec2 describe-security-groups --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_sgs.json &
  aws eks list-clusters --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_eks.json &
  aws rds describe-db-instances --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_rds.json &
  aws lambda list-functions --region "$AWS_DEFAULT_REGION" --output json > /tmp/topo_lambda.json &
fi

# Wait for remaining background jobs
wait
```

### Phase 3: Topology Generation (Template Rendering)

`topo-render.py` automatically:

1. Loads `/tmp/topo_*.json` data
2. Builds Subnet → resource mappings (EC2/ELB/RDS grouped by owning subnet)
3. Loads health overlay (when `--health-json` is provided)
4. Generates output:
   - **ASCII tree**: terminal-friendly, `report.md`
   - **Mermaid diagram**: visual topology, render-ready, `topology.mermaid.md`
5. Writes files to the output directory

> Template file `templates/vpc-topology.md` is kept for reference. Full rendering logic is implemented in `topo-render.py`.

### Phase 4: Report Compilation

**Single File Mode:**
```markdown
# {{user.project_name}} - AWS Network Topology & Resource Inventory

> Generated: {{timestamp}}
> Region: {{env.AWS_DEFAULT_REGION}}
> Mode: {{user.report_mode}}

{{topology_output}}

---

{{inventory_output}}

---

{{statistics_output}}
```

**Multi-File Mode:**
- `topology.md`: VPC tree + Mermaid diagram
- `inventory.md`: Full resource inventory table
- `summary.md`: Summary + architecture analysis + risk alerts

### Phase 5: Post-Execution Verification

1. Verify output file exists and size > 0:
   ```bash
   test -s report.md && echo "Report generated successfully"
   ```

2. Check no credentials leaked:
   ```bash
   grep -E 'AKIA|wJalr|SECRET|secret' report.md && { echo "WARNING: Possible credential leak"; exit 1; }
   ```

3. Verify read-only compliance (meta-check, no commands executed):
   - Confirm no write commands were in the execution log

## Failure Recovery

| Error Pattern | Max Retries | Backoff | Agent Action |
|--------------|-------------|---------|--------------|
| `InvalidClientTokenId` / `AuthFailure` | 0 | - | HALT. Credentials invalid. User must provide valid AK. |
| `SignatureDoesNotMatch` | 0 | - | HALT. AK/Secret mismatch or time skew. Check credentials. |
| `AccessDenied` / `UnauthorizedAccess` | 0 | - | HALT. Insufficient permissions. User needs `ReadOnlyAccess` or custom read-only policy. |
| `Throttling` / 429 | 3 | Exponential | Back off 2s, 4s, 8s. Retry. |
| `InternalError` / 5xx | 3 | 2s fixed | Retry; continue with partial data if persistent. |
| `InvalidRegion` / `RegionNotFoundException` | 0 | - | HALT. Check `{{env.AWS_DEFAULT_REGION}}`. |
| `InvalidVpcID.NotFound` | 0 | - | Skip VPC, continue scanning. |
| Command Timeout (>30s) | 1 | - | Kill process; log timeout; continue with other resources. |

---

## Causal Graph Operations

Builds X-Ray trace + CloudWatch ServiceLens topology for cross-service RCA.

### get-causal-graph

Collects X-Ray Service Graph and trace summaries to build causal call-chain topology.

**Input**: `{{user.time_window}}` (default: last 24h), `{{env.AWS_DEFAULT_REGION}}`

**Output**: JSON `{services, edges, anomalies}` — see `assets/causal-graph-template.json`

```bash
# Execute via causal-graph.sh (X-Ray → fallback to CloudWatch metrics if X-Ray disabled)
bash scripts/causal-graph.sh --time-window 86400 --region "$AWS_DEFAULT_REGION"

# Process traces via causal_inference.py
python3 scripts/causal_inference.py \
  --traces /tmp/xray_traces.json \
  --mode build-graph \
  --output /tmp/causal_graph.json
```

**Fallback**: If X-Ray is not enabled, `causal-graph.sh` falls back to CloudWatch Contributor Insights to infer service dependencies from latency/error metrics.

### find-root-cause

Given a target service and error-rate threshold, traces upstream call-chain to rank candidate root causes.

**Input**: `{{user.target_service}}`, `{{user.error_rate_threshold}}` (default: 0.05)

**Output**: JSON `[{service, confidence, reason}, ...]` — top-3 suspects ranked by confidence

```bash
python3 scripts/causal_inference.py \
  --graph /tmp/causal_graph.json \
  --mode find-root-cause \
  --target "{{user.target_service}}" \
  --threshold 0.05 \
  --output /tmp/root_cause.json
```

**Rule coverage**: ALB 5xx · RDS connection timeout · Lambda timeout · ECS task restart · NAT Gateway packet drop — see `references/causal-rules.md`.

### Integration with aws-aiops-orchestrator

`aws-aiops-orchestrator` Layer-3 RCA invokes:
1. `get-causal-graph` → build topology from X-Ray traces
2. `find-root-cause` → rank top-3 candidate services
3. Delegates to product-level skill for targeted diagnosis

## Well-Architected Assessment

This skill's operations are evaluated against AWS [Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/).

### Security

| Area | Guidance |
|------|----------|
| **IAM** | Require: `ReadOnlyAccess` policy only. Principle: least privilege, read-only access |
| **Credentials** | `{{env.*}}` only. All AK/Secret values in output must be masked (e.g., `AKIA***`) |
| **Data Sensitivity** | VPC IDs, instance IDs, and IP ranges are sensitive infrastructure data. Restrict report distribution |

### Reliability

| Area | Guidance |
|------|----------|
| **Failure Isolation** | Skip individual VPCs on error but continue scanning. Partial results are still valuable |
| **Change Tracking** | Regular topology discovery enables change tracking and drift detection |
| **Disaster Recovery** | N/A (read-only skill). Use reports as baseline for post-incident infrastructure comparison |

### Cost Optimization

This skill uses read-only Describe APIs which are free. Minimal API call volume:
- **Optimization:** Use batch APIs where possible. Use `--max-items` for pagination
- **Waste:** N/A for read-only discovery

### Operational Excellence

- **Parallel Collection:** EC2/RDS/ELB/VPC APIs can be queried simultaneously
- **CI/CD Integration:** Run in CI pipeline for regular topology drift detection
- **JSON Output:** Compatible with jq for automated analysis

### Performance

| Operation | Expected API Calls | Time Estimate |
|-----------|-------------------|---------------|
| Full scan (all VPCs, multi-region) | ~10-20 Describe calls | < 30s |
| Brief mode | ~5 Describe calls | < 10s |
| + Health overlay | +0 (reuses existing data) | +0s |
| + CF origin config (detailed/overlay) | +N `get-distribution-config` (parallel, cap 5) | +5–30s |
| + HCL export | ~10-30 API calls | < 60s |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements):
- TE-1: No hardcoded region/CIDR tables — use `describe-vpcs` / `describe-subnets` / `describe-regions`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths centralized in `## Common JSON Paths` above; details in `references/execution-commands.md`
- TE-5: N/A — no `assets/example-config.yaml` (CI templates in `assets/ci-cd-templates/`)
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## See Also

- [aws-skill-generator](../aws-skill-generator/SKILL.md) — Meta-skill rules
- [aws-vpc-ops](../aws-vpc-ops/SKILL.md) — VPC resource operations
- [aws-ec2-ops](../aws-ec2-ops/SKILL.md) — EC2 instance operations
- [aws-aiops-cruise](../aws-aiops-cruise/SKILL.md) — Health cruise + overlay producer
- [references/changelog.md](references/changelog.md) — Version history
