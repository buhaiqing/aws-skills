# AWS AIOps Reference Stack — aws-aiops-cruise

> AWS-native patrol layers. Each layer maps to specific APIs — not 1:1 Aliyun ports.

## Layer model

```
Internet
   │
   ▼
[Edge]     Route53 Health Check → CloudFront → AWS WAFv2
   │
   ▼
[Entry]    ALB/NLB (ELBv2) + ACM TLS + Target Groups
   │
   ▼
[Compute]  EC2 / ECS Fargate / EKS / Lambda (+ API Gateway)
   │
   ▼
[Data]     RDS/Aurora (PI) / RDS Proxy / ElastiCache / DynamoDB
   │
   ▼
[Egress]   NAT Gateway / Transit Gateway
   │
   ▼
[Security] VPC SG + NACL + GuardDuty + Security Hub + AWS Config
   │
   ▼
[Observe]  CloudWatch (metrics/alarms/anomaly) + DevOps Guru + X-Ray*
```

*X-Ray: read via `aws xray get-service-graph` when enabled — optional deep mode.

## AWS-native AIOps signals (prefer over raw thresholds alone)

| Signal source | AIOps value | CLI entry |
|---------------|-------------|-----------|
| **CloudWatch Alarm** `ALARM` | Already customer-tuned | `cloudwatch describe-alarms --state-value ALARM` |
| **DevOps Guru** insights | ML-backed RDS/Lambda anomalies | `devops-guru list-insights` |
| **Performance Insights** | DB wait events / load | `pi get-resource-metrics` |
| **Compute Optimizer** | Right-sizing / headroom | `compute-optimizer get-*-recommendations` |
| **Security Hub** ASFF | Centralized CRITICAL findings | `securityhub get-findings` |
| **AWS Config** | Compliance drift | `config describe-compliance-by-config-rule` |
| **Route53 HC** | DNS-level availability | `route53 get-health-check-status` |
| **WAFv2 BlockedRequests** | Attack vs misconfig | CloudWatch `AWS/WAFV2` |
| **ECS running/desired** | Container fleet health | `ecs describe-services` |
| **EKS nodegroup health** | K8s capacity plane | `eks describe-nodegroup` |
| **ASG desired/max** | Scale ceiling risk | `autoscaling describe-auto-scaling-groups` |
| **CloudFront** | CDN edge vs origin faults | `AWS/CloudFront` `5xxErrorRate`, `OriginLatency` |
| **RDS Proxy** | Connection pooling layer | `AWS/RDS` dim `ProxyName` |
| **X-Ray service graph** | Distributed trace hotspots | `xray get-service-graph` |

## Typical product combinations (patrol scope)

| Workload pattern | Resources to include in scope |
|------------------|-------------------------------|
| **Classic 3-tier** | ALB + EC2 ASG + RDS + ElastiCache + NAT + SG |
| **Container (ECS)** | ALB + ECS cluster/services + RDS + NAT |
| **Kubernetes (EKS)** | NLB/ALB + EKS cluster/nodegroups + RDS |
| **Serverless** | API Gateway + Lambda + DynamoDB + WAF |
| **Static + CDN** | CloudFront + S3 (origin) + WAF + ACM + **OriginLatency metrics** |

Scope via **Resource Groups** (tag/query-based) or **tag filter** — equivalent to Aliyun Resource Group.

## Delegation to aws-*-ops skills

| Finding type | Skill |
|--------------|-------|
| ALB 5xx / target drain | `aws-elb-ops` |
| RDS PI / slow query (instance) | `aws-rds-ops` |
| Aurora cluster (lag, failover, Serverless) | `aws-aurora-ops` |
| ASG scale policy | `aws-autoscaling-ops` |
| WAF rule tuning | `aws-waf-ops` |
| Config remediation | `aws-config-ops` |
| Multi-service RCA | `aws-aiops-orchestrator` |

## vs Aliyun cruise mapping

| Aliyun | AWS native |
|--------|------------|
| CloudMonitor | CloudWatch Metrics + Alarms |
| DAS | RDS Performance Insights + DevOps Guru |
| CloudAssistant | SSM Run Command (`aws-ssm-ops`) |
| ActionTrail | CloudTrail (`aws-cloudtrail-ops`) |
| Cloud Firewall | WAFv2 + Security Groups |
| Advisor | Trusted Advisor + Compute Optimizer |
| ResourceCenter | Resource Groups Tagging API + Resource Explorer |
