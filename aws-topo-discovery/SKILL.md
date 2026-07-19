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

See [references/execution-commands.md §JSON Output Path Mapping](references/execution-commands.md#json-output-path-mapping) for all jq paths.


Full jq mappings: `references/execution-commands.md` §JSON Output Path Mapping.

## READ-ONLY PRINCIPLE

See [references/read-only-principle.md](references/read-only-principle.md).


## Overview

`aws-topo-discovery` is a **cross-product network discovery tool** that automatically scans VPC network structures and associated resources (EC2/RDS/ELB/NAT/Elastic IP/EKS/Lambda/S3/Security Groups) under an AWS account, and generates structured network topology maps and resource inventory reports.

### Core Features

See [references/core-features.md](references/core-features.md) for all feature descriptions.

### Relationship with Existing Skills

See [references/relationships.md](references/relationships.md).



## Trigger & Scope

See [references/trigger-scope.md](references/trigger-scope.md) for SHOULD/SHOULD NOT criteria.

## Delegation Rules

| Capability | Delegate To | Notes |
|------------|-------------|-------|
| GCL quality gate | Self (`references/gcl-rubric.md`) | Optional per AGENTS.md §11.5; `max_iter=3`; read-only — Safety must = 1 |

## Quality Gate (GCL)

This Skill follows the AGENTS.md §11 Generator-Critic-Loop quality gate (**optional**, `max_iter=3`).

### Rubric Dimensions

See [references/gcl-rubric.md](references/gcl-rubric.md) for full rubric.
### GCL Prompt

Generator → Critic loop details are in [references/gcl-rubric.md](references/gcl-rubric.md), following the standard AGENTS.md §11 workflow.

## Pre-flight Interaction (User Decisions)

See [references/preflight-interaction.md](references/preflight-interaction.md) for the full configuration checklist.

## Variable Convention

See [references/variable-convention.md](references/variable-convention.md) for all placeholders.

## Execution Flows

See [references/execution-flows.md](references/execution-flows.md) for all 5 phases (pre-flight → data collection → rendering → report → verification).

## Failure Recovery

See [references/failure-recovery.md](references/failure-recovery.md) for the full error table.


---

## Causal Graph Operations

See [references/causal-graph-operations.md](references/causal-graph-operations.md) for `get-causal-graph` and `find-root-cause` operations.

## Well-Architected Assessment

See [references/well-architected.md](references/well-architected.md) for Security / Reliability / Cost / Operational Excellence / Performance guidance.

## Token Efficiency

See [references/token-efficiency.md](references/token-efficiency.md).

## See Also

[aws-skill-generator](../aws-skill-generator/SKILL.md) · [aws-vpc-ops](../aws-vpc-ops/SKILL.md) · [aws-ec2-ops](../aws-ec2-ops/SKILL.md) · [aws-aiops-cruise](../aws-aiops-cruise/SKILL.md) · [changelog](references/changelog.md)
