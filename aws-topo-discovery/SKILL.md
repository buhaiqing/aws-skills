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
  last_updated: "2026-07-31"
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

VPC: .Vpcs[].{VpcId,CidrBlock,State}
Subnets: .Subnets[].{SubnetId,VpcId,CidrBlock,AvailabilityZone}
ELB: .LoadBalancers[].{LoadBalancerName,DNSName,Type,VpcId}
Full jq mappings: [execution-commands.md#json-output-path-mapping](references/execution-commands.md#json-output-path-mapping)

## Overview

Cross-product **read-only** network discovery: scans VPC topology and associated resources (EC2/RDS/ELB/NAT/EIP/EKS/Lambda/S3/SG), generates topology maps and inventory reports. Absolute read-only — see [read-only-principle.md](references/read-only-principle.md) and [safety-gate.md](references/safety-gate.md).

## Trigger & Scope

### SHOULD Use When

- Cross-product network topology mapping (VPC + EC2/RDS/ELB/NAT/EIP/EKS/Lambda/S3/SG)
- Bulk resource inventory across an AWS account
- Compliance audit needing full resource graph
- HCL export, baseline snapshots, or drift comparison

### SHOULD NOT Use When

- Single-resource operations → respective `aws-*-ops`
- Real-time monitoring → `aws-cloudwatch-ops`
- Security findings investigation → `aws-guardduty-ops`

Full criteria: [trigger-scope.md](references/trigger-scope.md). Features: [core-features.md](references/core-features.md). Skill relationships: [relationships.md](references/relationships.md).

## Quality Gate (GCL)

Optional GCL (`max_iter=3`, read-only — Safety must = 1). Rubric: [gcl-rubric.md](references/gcl-rubric.md).

## Pre-flight → Execute → Validate → Recover

User decisions: [preflight-interaction.md](references/preflight-interaction.md). Variables: [variable-convention.md](references/variable-convention.md). Five-phase flows: [execution-flows.md](references/execution-flows.md). Recovery: [failure-recovery.md](references/failure-recovery.md).

## Extended References

Causal graph: [causal-graph-operations.md](references/causal-graph-operations.md) · Well-Architected: [well-architected.md](references/well-architected.md) · Token efficiency: [token-efficiency.md](references/token-efficiency.md)

## See Also

[aws-skill-generator](../aws-skill-generator/SKILL.md) · [aws-vpc-ops](../aws-vpc-ops/SKILL.md) · [aws-ec2-ops](../aws-ec2-ops/SKILL.md) · [aws-aiops-cruise](../aws-aiops-cruise/SKILL.md) · [changelog](references/changelog.md)
