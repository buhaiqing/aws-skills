# AWS ECR — Core Concepts

## Service Architecture

| Concept | Description |
|---------|-------------|
| **Registry** | Per-account per-region namespace; `{{output.registry_id}}.dkr.ecr.{{user.region}}.amazonaws.com` |
| **Repository** | Named container for related images; supports immutable tags and scanning-on-push |
| **Image** | Docker/OCI container image; referenced by tag (`:latest`) or digest (`sha256:...`) |
| **Lifecycle Policy** | Rules to expire unused images (age-based or count-based); reduces storage cost |
| **Repository Policy** | IAM-like resource policy controlling cross-account access |
| **Image Scanning** | CVE vulnerability scanning per image; basic (default) or enhanced (Inspector) |

## Repository Lifecycle

```
create-repository → describe-repositories → (CRUD images) → delete-repository
```

## Key Quotas (verify at runtime)

| Resource | Default Limit | CLI Query |
|----------|--------------|-----------|
| Max repositories per region | 10,000 | `aws ecr describe-repositories --region {{user.region}} | jq '.repositories \| length'` |
| Max lifecycle policies per repo | 10 | Query from `put-lifecycle-policy` error on exceeded |
| Max tags per image | 100 | n/a |
| Image scanning | 1 scan / 5 min per repo per `start-image-scan` | n/a |

Always query current limits at runtime; static values may change.

## Image URL Format

```
{{output.registry_id}}.dkr.ecr.{{user.region}}.amazonaws.com/{{user.repository_name}}:{{tag}}
```

## Authentication Methods

| Method | Use Case | Command |
|--------|----------|---------|
| AWS CLI credential helper | Docker push/pull | `aws ecr get-login-password \| docker login --username AWS --password-stdin <registry>` |
| IAM Role (EC2/ECS/EKS) | Instance-level pull | Attach `AmazonEC2ContainerRegistryReadOnly` or custom policy |
| Cross-account | Another AWS account | Repository policy + IAM role in target account |
| ECR credential helper | Docker config | `credHelpers: {"{{output.registry_id}}.dkr.ecr.{{user.region}}.amazonaws.com": "ecr-login"}` |

## Image Tag Mutability

| Mode | Behavior | Setting |
|------|----------|---------|
| **Mutable** (default) | Tags can be overwritten | `imageTagMutability: MUTABLE` |
| **Immutable** | Tags cannot be overwritten | `imageTagMutability: IMMUTABLE`; set at repo creation |
