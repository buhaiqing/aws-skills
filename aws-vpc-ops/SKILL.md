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
  last_updated: '2026-07-31'
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
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'change-impact']
    produces_facts: ['metric', 'log', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS VPC Operations Skill

Use for VPCs, subnets, route tables, internet/NAT gateways, endpoints, peering, NACLs, security groups, and network diagnostics. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

VPC: .Vpcs[0].{VpcId,CidrBlock,State,IsDefault}
Subnets: .Subnets[].{SubnetId,VpcId,AvailabilityZone,CidrBlock,State}
Routes: .RouteTables[].{RouteTableId,VpcId,Associations,Routes}
Gateways: .NatGateways[].{NatGatewayId,State,VpcId,SubnetId}; .InternetGateways[].{InternetGatewayId,Attachments}
Endpoints: .VpcEndpoints[].{VpcEndpointId,VpcId,State,ServiceName}

## Trigger & Scope

### SHOULD Use When
VPCs, subnets, routes, gateways, endpoints, peering, NACLs, security groups, or network connectivity.

### SHOULD NOT Use When
EC2 lifecycle → `aws-ec2-ops`; ELB → `aws-elb-ops`; DNS → `aws-route53-ops`; IAM → `aws-iam-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.vpc_id}}`, `{{user.subnet_id}}`, `{{user.route_table_id}}` | User input | Network IDs |
| `{{user.gateway_id}}`, `{{user.endpoint_id}}`, `{{user.peering_id}}` | User input | Dependency resources |
| `{{output.*}}` | API response | Reuse IDs/state/associations |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify ownership, subnets/ENIs, routes, gateways, endpoints, peering, NACLs, SGs, and dependency consumers. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back state and associations; recover with bounded retries and halt on non-empty dependencies or ambiguous identity. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/modify network | Validate CIDR overlap, AZ, route and SG impact | `confirm=MODIFY_PROD_<OP> <id>` (prod-tagged) |
| Delete VPC | Run 8 describes: subnets, IGWs, NATs, RTs, SGs, endpoints, peering, NACLs; require empty | `confirm=DELETE_VPC <vpc-id>` |
| Delete subnet | Verify no ENI/resources | `confirm=DELETE_SUBNET <subnet-id>` |
| Delete route table | Main table cannot be deleted; custom table must have no associations | `confirm=DELETE_ROUTE_TABLE <rt-id>` |
| Delete IGW/NAT | Detach IGW first; record released EIP for NAT | `confirm=DELETE_IGW <igw-id>` / `confirm=DELETE_NAT_GATEWAY <nat-id>` |
| Delete endpoint/peering/SG | Inspect consumers, ENIs, routes, and default SG constraints | `confirm=DELETE_VPC_ENDPOINT <vpce-id>` / `confirm=DELETE_VPC_PEERING <pcx-id>` / `confirm=DELETE_SECURITY_GROUP <sg-id>` |

Never infer network deletion consent from a generic “cleanup” request.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10 and A13 (8-describe VPC pre-flight); Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live topology/quotas, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for network/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive diagnostics; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
