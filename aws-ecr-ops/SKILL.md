---
name: aws-ecr-ops
description: >-
  Use when operating AWS ECR (Elastic Container Registry) resources via AWS CLI
  or boto3 SDK; user mentions ECR, container registry, Docker image, repository,
  image lifecycle, or image scanning.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-11"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: required
    max_iter: 2
  cross_skill_deps:
    - aws-ecs-ops            # Task container images
    - aws-iam-ops            # Repository policies, pull/push auth
    - aws-cloudwatch-ops     # ECR metric monitoring
    - aws-eventbridge-ops    # ECR event-driven workflows
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'self-heal', 'change-impact']
    produces_facts: ['state', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS ECR Operations Skill

Use for ECR repositories, images, tags, lifecycle policies, repository policies, scanning, replication, pull-through cache, and container registry operations. Detailed commands remain in references.

## Common JSON Paths

Repository: .repository.{repositoryArn,registryId,repositoryName,repositoryUri,createdAt,imageTagMutability,encryptionConfiguration}
Repositories: .repositories[].{repositoryArn,repositoryName,repositoryUri,imageTagMutability}
Images: .imageDetails[].{imageDigest,imageTags,imageSizeInBytes,imagePushedAt,imageScanStatus}
DeleteImages: .imageIds[].{imageDigest,imageTag}
ScanFindings: .imageScanFindings.{findingSeverityCounts,findings}

## Trigger & Scope

### SHOULD Use When
ECR repositories/images, push/pull, tags, lifecycle policies, scanning, replication, repository policies, or registry configuration.

### SHOULD NOT Use When
ECS workloads → `aws-ecs-ops`; EKS workloads → `aws-eks-ops`; IAM principal policies → `aws-iam-ops`; KMS key lifecycle → `aws-kms-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.repository_name}}`, `{{user.image_tag}}`, `{{user.image_digest}}` | User input | Repository/image identity |
| `{{user.policy_text}}`, `{{user.lifecycle_policy_text}}` | User input | Policy payloads |
| `{{output.*}}` | API response | Reuse URI, ARN, digest, counts |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify registry/repository identity, images/tags/digests, policy diff, scan status, replication, encryption, and downstream deployments. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back repository/images/policies; recover with bounded retries and halt on access, dependency, quota, or ambiguous image scope. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update repository | Validate encryption, mutability, scanning, replication | Token for disruptive policy/mutability changes |
| Delete repository | List images and downstream ECS/EKS references; avoid force by default | `DELETE <repository_name>`; force requires stronger confirmation |
| Batch delete images | Resolve explicit digests/tags, count and total bytes; no wildcard/empty list | `DELETE <count> images` |
| Lifecycle policy | Preview affected images; protect deployed/recent tags | Human confirmation before destructive expiry |
| Repository policy | Diff principals/actions; reject public or broad cross-account access unless approved | Public/cross-account confirmation |
| Delete scan/replication/cache config | Show security/supply-chain impact | Human confirmation |

Mask registry tokens, image layer contents, vulnerability details that expose secrets, and credentials in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10 and public-access safeguards; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live repository/image state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for image/repository deletion and access-policy changes; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
