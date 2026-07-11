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
---

# AWS ECR Operations Skill

## Overview

AWS Elastic Container Registry (ECR) is a fully managed container image registry for storing, managing, and deploying container images. This skill covers **repository lifecycle, image management, lifecycle policies, and repository policy configuration**.

## Trigger & Scope

### SHOULD Use When
- User mentions "ECR", "container registry", "Docker image", "image repository"
- Task involves CRUD on **ECR resources** (repository, image, lifecycle policy)
- Keywords: ecr, registry, repository, image, docker, container-image, lifecycle-policy
- Pushing/pulling images dependency setup (repository auth, policy)

### SHOULD NOT Use When
- Container orchestration (ECS/EKS) → delegate to: `aws-ecs-ops` or `aws-eks-ops`
- IAM roles/policies for image pull → delegate to: `aws-iam-ops`
- Cluster container metrics → delegate to: `aws-cloudwatch-ops`
- ECR event-driven automation → delegate to: `aws-eventbridge-ops`

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Skip if AWS_PROFILE or IAM Role used |
| `{{env.AWS_SESSION_TOKEN}}` | Runtime env | Required for STS temporary credentials |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{env.AWS_PROFILE}}` | Runtime env | Use named profile (SSO / AssumeRole); overrides explicit keys |
| `{{user.region}}` | User input | Ask once; reuse |
| `{{user.repository_name}}` | User input | ECR repository name |
| `{{output.repository_uri}}` | Last API response | `describe-repositories → .repositories[0].repositoryUri` |

## Config File Placeholders

`assets/example-config.yaml` uses `{{env.*}}` for environment values and `{{user.*}}` for resource-specific values.

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | `.env` or runtime env | Substitute before use |
| `{{user.repository_name}}` | User input | Ask once; substitute |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Pre-flight │ → │   Execute   │ → │   Validate  │ → │   Recover   │
│   Checks    │    │ CLI/SDK     │    │   Polling   │    │  On Error   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Operation: Create Repository

#### Pre-flight
**Step 1: Check CLI & Credentials**
```bash
aws --version && aws sts get-caller-identity --output json
```

**Step 2: Verify ECR access**
```bash
aws ecr describe-repositories --region {{user.region}} --output json | jq '.repositories | length'
```
Log: `[OK] ECR accessible, N existing repositories`

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; guide to integration.md |
| Region valid | `aws ecr describe-repositories --region {{user.region}}` | HALT; suggest valid region |
| Name collision | `aws ecr describe-repositories --repository-names {{user.repository_name}}` | HALT; name already exists |

#### Execute — CLI (Primary)
```bash
aws ecr create-repository \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('ecr', region_name='{{user.region}}')
response = client.create_repository(repositoryName='{{user.repository_name}}')
```

#### Validate
Verify repository exists and is `AVAILABLE`:
```bash
aws ecr describe-repositories \
  --repository-names "{{user.repository_name}}" \
  --region "{{user.region}}" \
  --query 'repositories[0].repositoryUri' --output json
```

#### Recover
| Error | Action |
|-------|--------|
| `RepositoryAlreadyExistsException` | Repository exists — use it or ask to delete & recreate |
| `InvalidParameterException` | Fix repo name format; retry once |
| `LimitExceededException` | HALT — request service quota increase |
| Throttling (429) | Backoff, retry 3x |

---

### Operation: Delete Repository

**Safety Gate**: MUST obtain explicit user confirmation (`confirm=DELETE <repository_name>`) before proceeding.

#### Pre-flight
```bash
# Check if repository contains images
aws ecr list-images --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --query 'imageIds[*]' --output json
```
If non-empty, warn user: `Repository has N images — deletion is irreversible.`
If `--force` equivalent is needed: use `--force` after confirmation only.

#### Execute — CLI (Primary)
```bash
aws ecr delete-repository \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
client.delete_repository(repositoryName='{{user.repository_name}}')
```

#### Validate
```bash
aws ecr describe-repositories \
  --repository-names "{{user.repository_name}}" \
  --region "{{user.region}}" 2>&1
# Expect: RepositoryNotFoundException → delete confirmed
```

#### Recover
| Error | Action |
|-------|--------|
| `RepositoryNotEmptyException` | Ask user: force delete? Use `--force` if confirmed |
| `RepositoryNotFoundException` | Already deleted — idempotent success |
| Throttling (429) | Backoff, retry 3x |

---

### Operation: List & Manage Images

#### List Images
```bash
aws ecr list-images --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" --output json
```
**JSON Path**: `.imageIds[].{tag: imageTag, digest: imageDigest}`

#### Batch Delete Images
**Safety Gate**: User must confirm `confirm=DELETE <count> images`.
```bash
aws ecr batch-delete-image \
  --repository-name "{{user.repository_name}}" \
  --image-ids imageTag=v1.0.0 imageTag=v0.9.0 \
  --region "{{user.region}}" \
  --output json
```

#### Recover
| Error | Action |
|-------|--------|
| `ImageNotFoundException` | Skip — idempotent |
| `InvalidParameterException` | Fix image identifier; retry once |

---

### Operation: Manage Lifecycle Policy

#### Pre-flight
Verify repository supports lifecycle policies (private repositories only).

#### Put Lifecycle Policy
```bash
aws ecr put-lifecycle-policy \
  --repository-name "{{user.repository_name}}" \
  --lifecycle-policy-text file://policy.json \
  --region "{{user.region}}" \
  --output json
```

#### Get Lifecycle Policy
```bash
aws ecr get-lifecycle-policy \
  --repository-name "{{user.repository_name}}" \
  --region "{{user.region}}" \
  --output json
```

#### Recover
| Error | Action |
|-------|--------|
| `LifecyclePolicyNotFoundException` | No policy exists — create one |
| `InvalidParameterException` | Fix policy JSON; retry once |

---

### Operation: Set Repository Policy

**Safety Gate**: Warn if policy grants cross-account or public access.

```bash
aws ecr set-repository-policy \
  --repository-name "{{user.repository_name}}" \
  --policy-text file://policy.json \
  --region "{{user.region}}" \
  --output json
```

## Common JSON Paths

> Declared once per resource type. File-top block — see TE-4.

```json
// describe-repositories
{ "repositories": [{ "repositoryName": "my-repo", "repositoryUri": "123.dkr.ecr.us-east-1.amazonaws.com/my-repo" }] }
// → .repositories[0].repositoryUri

// list-images
{ "imageIds": [{ "imageDigest": "sha256:...", "imageTag": "latest" }] }
// → .imageIds[].imageTag

// describe-images
{ "imageDetails": [{ "imageDigest": "sha256:...", "imageSizeInBytes": 12345, "imagePushedAt": "2026-01-01" }] }
// → .imageDetails[0].imageSizeInBytes
```

## Reference Files

- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)
- [Example Config](assets/example-config.yaml)

## Token Efficiency (TE)

- **TE-1**: Use `aws ecr describe-repositories` to query limits/quotas at runtime; no static table.
- **TE-2**: boto3 code uses inline comments, no docstrings (see `references/boto3-sdk-usage.md`).
- **TE-3**: Error tables compact — common errors only; see per-operation Recover tables.
- **TE-4**: JSON paths centralized in Common JSON Paths block above.
- **TE-5**: YAML anchors in `assets/example-config.yaml` for shared fields.

## Quality Gate (GCL)

GCL is **required** for `aws-ecr-ops` (max_iter=2) per `AGENTS.md` §11.5. See [`references/rubric.md`](references/rubric.md) for the 5-dimension scoring rubric and [`references/prompt-templates.md`](references/prompt-templates.md) for Generator/Critic/Orchestrator prompt templates.
