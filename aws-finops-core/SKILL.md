---
name: aws-finops-core
description: >-
  Unified FinOps composite skill: cost anomaly detection, idle resource discovery,
  and tag-compliance reporting. Orchestrates aws-ec2-ops, aws-rds-ops, aws-elb-ops,
  aws-s3-ops, and aws-lambda-ops. Read-only — no destructive AWS operations.
license: MIT
compatibility:
  aws-services:
    - cost-explorer
    - cloudwatch
    - ec2
    - rds
    - elb
    - s3
    - lambda
  prerequisites:
    - AWS Cost Explorer enabled
    - CloudWatch metrics enabled on target resources
metadata:
  type: composite
  version: "1.0.0"
  provides:
    - cost-anomaly-detection
    - idle-resource-discovery
    - tag-compliance-reporting
    - ri-sp-coverage-analysis
    - ecs-idle-service-discovery
    - ecs-fargate-rightsizing
    - ecs-fargate-spot-optimization
    - app-autoscaling-ecs-targets
    - app-autoscaling-policies
    - budget-alert-review
  delegate:
    ec2-idle: aws-ec2-ops
    ec2-ri: aws-ec2-ops
    ebs-idle: aws-ec2-ops
    rds-idle: aws-rds-ops
    rds-ri: aws-rds-ops
    elb-idle: aws-elb-ops
    s3-anomaly: aws-s3-ops
    lambda-idle: aws-lambda-ops
    ecs-idle: aws-ecs-ops
    ecs-rightsizing: aws-ecs-ops
    ecs-fargate-spot: aws-ecs-ops
    app-autoscaling-ecs-targets: aws-application-autoscaling-ops
    app-autoscaling-policies: aws-application-autoscaling-ops
---

## Trigger & Scope

### SHOULD Use When

- Monthly/weekly cost review before finance close
- Unplanned cost spike investigation
- Idle resource cleanup sweep (quarterly or on cost alert)
- Tag compliance audit for chargeback/showback
- RI/SP coverage review before renewal date

### SHOULD NOT Use When

- Real-time cost control during deployment (use `aws-cost-anomaly-ops`)
- Budget enforcement or auto-scaling actions (no write ops here)
- Service-level cost optimization requiring specific service skills

## Variable Convention

| Variable | Source | Default | Description |
|---|---|---|---|
| `{{user.cost_period}}` | user input | `LAST_30_DAYS` | Analysis window: `LAST_7_DAYS`, `LAST_30_DAYS`, `YYYY-MM,YYYY-MM` |
| `{{user.threshold_pct}}` | user input | `130` | Anomaly alert threshold % of 7-day baseline |
| `{{user.idle_days}}` | user input | `7` | Days of zero activity before marking idle |
| `{{env.AWS_ACCOUNT_ID}}` | env / STS | — | For ARN construction in reports |
| `{{env.AWS_DEFAULT_REGION}}` | env | `us-east-1` | Target region |

## Execution Flow Pattern

```
Pre-flight
  └─ verify Cost Explorer enabled  (aws ce get-cost-and-usage --time-period ...)
  └─ confirm region / account context  (aws sts get-caller-identity)

Query Cost Explorer
  ├─ get-cost-and-usage (DAILY, by SERVICE)
  ├─ get-cost-forecast
  └─ get-reservation-coverage / get-savings-plans-coverage

Idle Detection (delegate to base skills)
  ├─ ALB/NLB  → aws-elb-ops  (CloudWatch RequestCount=0 ≥ {{user.idle_days}} days)
  ├─ EBS Vol  → aws-ec2-ops  (Status=available, unattached ≥ 30 days)
  ├─ Snapshot → aws-ec2-ops  (orphaned snapshots)
  ├─ Lambda   → aws-lambda-ops (Invocations=0 ≥ 30 days)
  └─ RDS      → aws-rds-ops  (DatabaseConnections=0 ≥ {{user.idle_days}} days)
  ├─ ECS Service       → aws-ecs-ops  (desiredCount=0 & runningCount=0)
  ├─ Fargate Right-Sizing → aws-ecs-ops  (Compute Optimizer ECS recommendations)
  └─ Fargate Spot      → aws-ecs-ops  (capacity provider weight tuning)

Anomaly Analysis
  └─ 7-day baseline → flag cost > threshold_pct

Report
  └─ Summary: top anomaly services, idle resources, tag compliance %, RI/SP coverage
```

## Quality Gate (GCL)

| Field | Value |
|---|---|
| **GCL Tier** | recommended |
| **max_iterations** | 3 |
| **Safety threshold** | Safety = 0 → ABORT |
| **Notes** | Read-only composite; no destructive ops. Delegate to base skills handles safety gates internally. |
