# ECS Core Concepts

## Launch Types

| Type | Description | Billing |
|------|-------------|---------|
| **Fargate** | Serverless; no EC2 management | Pay per task vCPU/memory |
| **EC2** | Run tasks on managed EC2 instances | Pay for EC2 instances |

## Key Concepts

- **Cluster**: Logical group of container tasks/services. Region-scoped.
- **Service**: Maintains desired count of tasks; integrates with ALB/ELB.
- **Task Definition**: Blueprint — container image, CPU, memory, port mappings, IAM role, env vars.
- **Task**: Single running instance of a task definition. Fargate tasks run in `awsvpc` network mode.
- **Container Instance** (EC2 type): EC2 instance registered to a cluster running ECS agent.

## Networking

- **awsvpc**: Each task gets its own ENI. Required for Fargate.
- **bridge/host**: EC2 launch type only; legacy Docker networking.

## IAM Roles

| Role | Purpose |
|------|---------|
| **Task Execution Role** | Pulls images from ECR, sends logs to CloudWatch |
| **Task Role** | Grants permissions to the application running in the container |

## Limits

| Resource | Default Limit |
|----------|--------------|
| Clusters per region | 10 |
| Services per cluster | 500 |
| Tasks per service | 1000 |
| Task definitions (soft) | 100 per family, 1000 total |

## Quota Check

```bash
aws service-quotas get-service-quota \
  --service-code ecs \
  --quota-code L-12345678 \
  --output json
```