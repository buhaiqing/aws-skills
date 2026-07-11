---
name: aws-vpc-ops
description: Use when managing AWS VPC resources, creating/deleting VPCs, subnets,
  security groups, route tables, IGWs, NAT Gateways, or peering connections; even
  if user doesn't mention "VPC" but needs network infrastructure or troubleshooting.
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with EC2/VPC
  permissions.
metadata:
  author: aws
  version: "1.3.0"
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION
  - AWS_SESSION_TOKEN
  cross_skill_deps:
  - aws-elb-ops
  - aws-ec2-ops
  - aws-cloudwatch-ops
  - aws-cloudtrail-ops
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'change-impact']
    produces_facts: ['metric', 'log', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS VPC Ops Skill

## Trigger & Scope

### SHOULD Use When
- VPC/subnet/SG/route table/NAT Gateway/IGW tasks
- VPC Peering setup or teardown
- Network connectivity troubleshooting within VPC scope
- **(AIOps)** Network anomaly detection, VPC Flow Log RCA, SG drift, NAT saturation, cross-AZ traffic analysis
- Keywords: vpc, subnet, cidr, security-group, route, gateway, peering, flow-logs, vpc-diagnostics, sg-drift, nat-monitor, reachability

### SHOULD NOT Use When
- EC2 instance ops → `aws-ec2-ops`
- IAM → `aws-iam-ops`
- Load Balancer → `aws-elb-ops`
- Route53 DNS → `aws-route53-ops`

## Scope & Quick Reference

| Resource | CLI | Gate |
|----------|-----|------|
| VPC | `aws ec2 create-vpc --cidr-block {{cidr}}` | Delete: confirm + deps check |
| Subnet | `aws ec2 create-subnet --vpc-id {{id}} --cidr-block {{cidr}}` | Delete: confirm |
| Security Group | `aws ec2 create-security-group --group-name {{name}} --description {{desc}} --vpc-id {{id}}` | Delete: confirm + ENI check |
| Route Table | `aws ec2 create-route-table --vpc-id {{id}}` | Delete: disassociate first |
| IGW | `aws ec2 create-internet-gateway` | Delete: detach first |
| NAT Gateway | `aws ec2 create-nat-gateway --subnet-id {{id}} --allocation-id {{eip}}` | Delete: confirm |
| VPC Peering | `aws ec2 create-vpc-peering-connection --vpc-id {{id}} --peer-vpc-id {{id}}` | Accept/reject: confirm |

## Variable Convention

| Placeholder | Source | Action |
|-------------|--------|--------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{user.vpc_cidr}}` / `{{user.vpc_name}}` | User input | Ask once; reuse |
| `{{user.subnet_cidr}}` | User input | Ask once; reuse |
| `{{output.vpc_id}}` | Last API response | Parse: `.Vpc.VpcId` |
| `{{output.subnet_id}}` | Last API response | Parse: `.Subnet.SubnetId` |
| `{{output.sg_id}}` | Last API response | Parse: `.GroupId` |

## Execution Flow

### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
# Quota check
aws service-quotas get-service-quota --service-code ec2 --quota-code L-F678F1CE  # VPCs/region
aws service-quotas get-service-quota --service-code ec2 --quota-code L-3633C6E3  # NAT GWs/AZ
```

### Execute
- **Primary**: CLI — see [references/aws-cli-usage.md](references/aws-cli-usage.md)
- **Fallback**: boto3 (after 3 CLI failures) — see [references/boto3-sdk-usage.md](references/boto3-sdk-usage.md)

### Validate
| Operation | Max Wait |
|-----------|----------|
| Create VPC / Subnet / SG | 30s (`vpc_available`, `subnet_available`) |
| Create NAT Gateway | 180s (`nat_gateway_available`) |
| Peering Accept | 60s (`describe-vpc-peering-connections`) |

### Recover
| Error | Action |
|-------|--------|
| InvalidParameter / CIDR Conflict | HALT — fix params |
| QuotaExceeded | HALT — request increase |
| ResourceDependencyViolation | HALT — cleanup deps |
| Throttling / 5xx | Retry 3x (backoff); then HALT |

## Safety Gates

### VPC Deletion
```
⚠️ Irreversible. Dependencies must be removed in order:
Instances → NAT GWs → Detach/Delete IGW → Delete RTs (skip main) → Delete Subnets → Delete VPC
```
Confirm: `DELETE {{user.vpc_id}}`

### Dependency Cleanup
```bash
aws ec2 describe-instances --filters Name=vpc-id,Values={{id}}      # instances
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values={{id}}    # NAT GWs
aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values={{id}}  # IGWs
aws ec2 describe-route-tables --filters Name=vpc-id,Values={{id}}   # RTs (skip main)
aws ec2 describe-subnets --filters Name=vpc-id,Values={{id}}        # subnets
```

## Output Convention

All commands use `--output json`. Key JSON paths:
```
Create:       .Vpc.{VpcId,CidrBlock,State}  /  .Subnet.{SubnetId,CidrBlock,VpcId,State,AvailabilityZone}
              .GroupId  /  .RouteTable.RouteTableId  /  .InternetGateway.InternetGatewayId
              .NatGateway.{NatGatewayId,State}  /  .VpcPeeringConnection.{VpcPeeringConnectionId,Status.Code}
Describe:     .Vpcs[].{VpcId,CidrBlock,State,Tags}  /  .Subnets[]  /  .SecurityGroups[].{GroupId,GroupName,IpPermissions}
              .RouteTables[].{RouteTableId,Routes,Associations}  /  .NatGateways[].{NatGatewayId,State,SubnetId}
              .InternetGateways[].{InternetGatewayId,Attachments}  /  .VpcPeeringConnections[].{VpcPeeringConnectionId,Status}
```

## Delegation
| Condition | Skill |
|-----------|-------|
| EC2 instance in subnet | `aws-ec2-ops` |
| RDS in VPC | `aws-rds-ops` |
| Lambda VPC config | `aws-lambda-ops` |
| VPN connection | this skill |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md). Key points:
- TE-1: No hardcoded CIDR/limits — use `describe-*` / `get-service-quota`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables
- TE-4: JSON paths centralized in Output Convention (above)
- TE-5: YAML anchors in `assets/example-config.yaml`
- TE-6: Flows only in SKILL.md (no duplicates in references/)

## Reference Files
- `references/aws-cli-usage.md` — CLI commands
- `references/boto3-sdk-usage.md` — SDK patterns
- `references/core-concepts.md` — Architecture, CIDR, quotas
- `references/troubleshooting.md` — Error codes, cleanup, connectivity
- `assets/example-config.yaml` — Configuration templates

---

## AIOps: Network Diagnostics for Load Balancer Integration

### AIOps Data Collection
| Data Source | Namespace | AIOps Use |
|-------------|-----------|-----------|
| NAT GW `ActiveConnectionCount` / `PacketsDropCount` | AWS/NATGateway | Connection saturation → ELB timeout; packet loss → latency |
| VPC Flow Logs | S3 / CloudWatch Logs | Connection timeout RCA, traffic pattern analysis |
| SG / NACL changes | CloudTrail | Drift detection → health check failure |
| VPC Reachability Analyzer | EC2 API | Path validation between LB and targets |

### AIOps Diagnostic Flows

#### NF-01: NLB Connection Timeout Network RCA
1. **Check NAT Gateway metrics** — `get-metric-statistics ActiveConnectionCount` > 80% → saturation; `PacketsDropCount` > 0 → drops
2. **VPC Flow Log REJECT analysis** — query `action = "REJECT"` between LB subnet and target subnet
3. **Check SG/NACL changes** — `cloudtrail lookup-events SecurityGroup` (last 60 min)
4. **Action**: NAT saturated → [AI_ASSIST] Add NAT GW or redistribute subnets; Flow Log REJECT → check SG/NACL; SG changed → [MANUAL] review

```bash
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name ActiveConnectionCount --dimensions Name=NatGatewayId,Value={{nat_id}} --statistics Maximum --period 60
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway --metric-name PacketsDropCount --statistics Sum --period 300
aws logs start-query --log-group-name /aws/vpc/flow-logs/{{name}} --query-string 'filter action = "REJECT" | stats count() by dstaddr, dstport | sort count desc | limit 20' --start-time "{{T0-60m}}"
```

#### NF-02: Security Group Drift Detection [AI_ASSIST]
```bash
aws ec2 describe-security-groups --group-ids {{sg_id}} --query "SecurityGroups[0].{GroupId:GroupId,IpPermissions:IpPermissions,IpPermissionsEgress:IpPermissionsEgress}" > /tmp/sg_baseline.json
# Later: same cmd > /tmp/sg_current.json; diff /tmp/sg_baseline.json /tmp/sg_current.json
```

#### NF-03: VPC Reachability Analysis
```bash
aws ec2 create-network-insights-path --source {{lb_eni}} --destination {{target_eni}} --protocol TCP --destination-port {{health_check_port}}
aws ec2 start-network-insights-analysis --network-insights-path-id {{path_id}}
```

### Cross-Module Integration
| Condition | Delegate To |
|-----------|-------------|
| ELB connection timeout diagnosis | `aws-elb-ops` (RCA coordination) |
| EC2 instance-level network check | `aws-ec2-ops` (SSM diagnostics) |
| CloudWatch metrics setup | `aws-cloudwatch-ops` (alarms) |
| CloudTrail audit | `aws-cloudtrail-ops` (event analysis) |

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-vpc-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}`:
- `delete-vpc` — **HIGH BLAST RADIUS**; pre-flight runs **8 describe-\*** (subnets/IGWs/NATs/RTs/SGs/endpoints/peering/NACLs); refuse if any non-empty
- `delete-security-group` — ENI check; default SG undeletable while VPC has instances
- `delete-subnet` — must have no ENI
- `delete-route-table` — main RT undeletable; custom RT must have no associations
- `delete-internet-gateway` — must be detached first
- `delete-nat-gateway` — capture released EIP allocation id
- `delete-vpc-endpoint` / `delete-vpc-peering-connection`
- `authorize-security-group-ingress` adding `0.0.0.0/0` on sensitive ports (22, 3389, 5432, 3306, 27017, 6379, 9200, 11211, 25)

AWS rules: A7 (region), A8 (resource echo-back), A9 (no secrets in trace), A10 (sts first).

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by `aws-aiops-orchestrator`, honor the delegate contract.

### Recognition
Parse `aiops_delegate:` block fields: `request_id` (non-empty), `parent_intent` (health-check | rca | self-heal | cost-forecast | capacity-forecast | change-impact | compliance-scan | forensic), `action_mode` (observe | recommend | auto-heal | manual), `decision_tier` (AUTO_HEAL | AI_ASSIST | MANUAL), `scope.resource_ids`.

### Behavior Rules
1. **Idempotency**: write ops accept `idempotency_key`; same key within 24h returns cached result with `aiops_context.facts[*].deduplicated: true`
2. **Confirmation gate**: destructive ops require `confirmation_token`; if absent, refuse with `status: "failed"`
3. **Decision tier**: `MANUAL` → recommendations only; `AI_ASSIST` → execute only with `confirmation_token`; `AUTO_HEAL` → execute non-destructive writes directly
4. **Trace propagation**: every AWS CLI/boto3 call includes `User-Agent: aiops-orchestrator/<trace_id>`
5. **Output**: always include `aiops_context:` JSON block

### Cross-reference
See [aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md) for runbooks invoking this skill.