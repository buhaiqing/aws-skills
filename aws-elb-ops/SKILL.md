---
name: aws-elb-ops
description: 'Use when the user needs to set up, configure, or manage load balancers
  to distribute traffic across multiple targets; create or modify target groups, listeners,
  or health checks; configure ALB for HTTP/HTTPS web traffic, NLB for high-performance
  TCP/UDP workloads, or CLB for legacy applications; even if they don''t say "ELB"
  and instead say "balance traffic", "set up a load balancer", "configure health checks",
  or "route requests to my servers".

  (AIOps) Use when detecting ELB anomalies (latency spikes, error rates, connection
  exhaustion), performing root cause analysis across ELB/EC2/VPC, executing self-healing
  actions for unhealthy targets, predicting capacity saturation, or optimizing ELB
  cost and configuration.'
license: MIT
compatibility: AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network
  access to AWS endpoints. CloudWatch, CloudTrail, AWS Config access required for
  AIOps scenarios.
metadata:
  author: aws
  version: "2.2.0"
  last_updated: '2026-06-04'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  aiops_level: full-chain
  environment:
  - AWS_ACCESS_KEY_ID
  - AWS_SECRET_ACCESS_KEY
  - AWS_DEFAULT_REGION
  cross_skill_deps:
  - aws-cloudwatch-ops
  - aws-cloudtrail-ops
  - aws-ec2-ops
  - aws-vpc-ops
  - aws-route53-ops
  - aws-acm-ops
  - aws-s3-ops
  gcl:
    enabled: true
    class: recommended
    max_iter: 3
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'log', 'event', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS ELB Operations Skill

## Overview

AWS Elastic Load Balancing (ELB) automatically distributes incoming application traffic across multiple targets. This skill covers **Application Load Balancer (ALB)**, **Network Load Balancer (NLB)**, and **Classic Load Balancer (CLB)** operations, with full AIOps closed-loop support for **anomaly detection, predictive analysis, root cause diagnosis, self-healing, cost optimization, and change management**.

## Trigger & Scope

### SHOULD Use When
- User mentions "ELB", "Load Balancer", "ALB", "NLB", or "CLB"
- Task involves CRUD on **Load Balancers** or **Target Groups**
- Keywords: balance, distribute, health-check, listener, target-group
- **(AIOps)** User reports "502/503/504 errors", "latency spikes", "health check failures"
- **(AIOps)** User asks "why are targets unhealthy", "what changed on the LB", "is traffic abnormal"
- **(AIOps)** User asks "can this handle more traffic", "when will we run out of capacity", "is the LB idle"
- **(AIOps)** User asks "optimize ELB cost", "find unused load balancers", "right-size my LB configuration"
- **(AIOps)** User wants "auto-heal unhealthy targets", "auto-adjust health checks", "auto-scale listener rules"

### SHOULD NOT Use When
- EC2 instances → delegate to: `aws-ec2-ops`
- VPC/subnets → delegate to: `aws-vpc-ops`
- SSL certificates → delegate to: `aws-acm-ops`
- Route53 DNS → delegate to: `aws-route53-ops`
- CloudWatch alarms/metrics setup → delegate to: `aws-cloudwatch-ops`
- CloudTrail event analysis → delegate to: `aws-cloudtrail-ops`

## Load Balancer Types

| Type | Layer | Use Case | CLI Service |
|------|-------|----------|-------------|
| ALB | Layer 7 (HTTP/HTTPS) | Web apps, microservices | `elbv2` |
| NLB | Layer 4 (TCP/UDP) | High performance, gaming, IoT | `elbv2` |
| CLB | Layer 4/7 (legacy) | Legacy apps (being deprecated) | `elb` |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask user; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default only if skill allows |
| `{{user.lb_name}}` | User input | Ask once; reuse |
| `{{user.lb_type}}` | User input | ALB, NLB, or CLB |
| `{{user.vpc_id}}` | User input | Ask once; reuse |
| `{{output.load_balancer_arn}}` | Last API response | Parse `.LoadBalancers[0].LoadBalancerArn` |

## Execution Flow Pattern

Every operation follows: **Pre-flight → Execute → Validate → Recover**
AIOps scenarios additionally follow: **Data Collection → Detection → RCA → Decision → Action → Feedback**

```
         ┌──────────────────────────────────────────────────────┐
         │           AIOps Full-Chain Closed-Loop              │
         └──────────────────────────────────────────────────────┘

Manual Ops:  Pre-flight → Execute → Validate → Recover
                    │
                    ▼
AIOps Loop:  Data Collection → Detection → RCA → Decision → Action → Feedback
                                       ↕           ↕           ↕
                              CloudWatch      AWS Config    Auto-heal
                              CloudTrail      Tagging       SSM/CLI
                              VPC Flow Logs   Health        Rollback
```

***

## AIOps Data Collection

### CloudWatch Metrics — ALB (AWS/ApplicationELB)

| Metric | AIOps Use | Collection Command |
|--------|-----------|-------------------|
| `TargetResponseTime` | Latency anomaly detection (p50/p90/p99 trending) | `get-metric-statistics --namespace AWS/ApplicationELB --metric-name TargetResponseTime` |
| `HTTPCode_Target_5XX` | Error rate spike detection & RCA | `get-metric-statistics ... --metric-name HTTPCode_Target_5XX` |
| `HTTPCode_ELB_5XX` | ELB infrastructure issue detection (502/503/504) | `get-metric-statistics ... --metric-name HTTPCode_ELB_5XX` |
| `HealthyHostCount` | Target health flapping detection | `get-metric-statistics --statistic Minimum ... --metric-name HealthyHostCount` |
| `UnHealthyHostCount` | Health degradation trending | `get-metric-statistics ... --metric-name UnHealthyHostCount` |
| `RequestCount` | Traffic anomaly & capacity prediction | `get-metric-statistics ... --metric-name RequestCount` |
| `ActiveConnectionCount` | Connection pool exhaustion detection | `get-metric-statistics ... --metric-name ActiveConnectionCount` |
| `RejectedConnectionCount` | Capacity saturation alert | `get-metric-statistics ... --metric-name RejectedConnectionCount` |
| `ConsumedLCUs` | Cost anomaly & capacity planning | `get-metric-statistics ... --metric-name ConsumedLCUs` |

### CloudWatch Metrics — NLB (AWS/NetworkELB)

| Metric | AIOps Use | Collection Command |
|--------|-----------|-------------------|
| `ActiveFlowCount` | Flow capacity prediction | `get-metric-statistics --namespace AWS/NetworkELB --metric-name ActiveFlowCount` |
| `NewFlowCount` | Traffic surge detection | `get-metric-statistics ... --metric-name NewFlowCount` |
| `ProcessedBytes` | Throughput anomaly detection | `get-metric-statistics ... --metric-name ProcessedBytes` |
| `HealthyHostCount` | Target health trending | `get-metric-statistics ... --metric-name HealthyHostCount` |
| `UnHealthyHostCount` | Health degradation detection | `get-metric-statistics ... --metric-name UnHealthyHostCount` |
| `ConsumedLCUs` | Cost optimization | `get-metric-statistics ... --metric-name ConsumedLCUs` |

### ELB Access Logs

Access logs stored in S3, analyzed via Athena or CloudWatch Logs Insights.

```bash
# Enable access logs for AIOps analysis
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --attributes Key=access_logs.s3.enabled,Value=true \
               Key=access_logs.s3.bucket,Value=elb-logs-{{env.AWS_ACCOUNT_ID}} \
               Key=access_logs.s3.prefix,Value=alb-logs

# Analyze via Logs Insights
aws logs start-query \
  --log-group-names "/aws/elb/{{user.lb_name}}" \
  --start-time "$(date -d '-1 hour' +%s)" --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, elb_status_code, target_status_code, target_processing_time, request_processing_time
                  | filter elb_status_code >= 500
                  | stats count() by target_status_code
                  | sort count desc'
```

### CloudTrail Configuration Change Events

Track all LB configuration changes for change anomaly detection and rollback.

```
Tracks: CreateLoadBalancer, DeleteLoadBalancer, ModifyLoadBalancerAttributes,
        SetSecurityGroups, SetSubnets, CreateListener, DeleteListener,
        CreateRule, DeleteRule, RegisterTargets, DeregisterTargets,
        CreateTargetGroup, DeleteTargetGroup, ModifyTargetGroup,
        ModifyTargetGroupAttributes
```

### Resource Health & Compliance (AWS Config)

```
Config Rules Applicable: alb-desync-mitigation-mode, alb-http-drop-invalid-header-enabled,
                          alb-waf-enabled, elb-deletion-protection-enabled, elb-logging-enabled
```

***

## AIOps Scenario Coverage

This module supports the full AIOps lifecycle across **6 domains and 31 scenarios**.
See [references/core-concepts.md](references/core-concepts.md) → AIOps Scenarios Map for details.

| Domain | Scenarios | Example | Decision Type |
|--------|-----------|---------|---------------|
| **Fault Detection** (6) | Health flapping, latency spikes, error rate surges, connection exhaustion, cross-AZ imbalance, traffic anomalies | FD-01: Target 3x/min state flapping → `[AUTO_HEAL]` | `[AUTO_HEAL]` / `[AI_ASSIST]` |
| **Predictive Analysis** (5) | Capacity saturation, quota exhaustion, cert expiry, cost overrun, traffic peaks | PA-01: Connection count forecast exceeds limit in 7 days → `[AI_ASSIST]` | `[AI_ASSIST]` / `[MANUAL]` |
| **Auto-Healing** (8) | Target re-registration, health check tuning, cross-AZ rebalance, EC2 restore, SG drift, cert renewal, DNS failover, DDoS mitigation | AH-01: Unhealthy target → auto-deregister → wait → re-register → verify | `[AUTO_HEAL]` / `[AI_ASSIST]` |
| **Root Cause Analysis** (5) | 502 error, high latency, unhealthy target, connection timeout, cost anomaly | RC-01: 502 → check target → EC2 CPU/StatusCheck → VPC SG → CloudTrail | `[AUTO_HEAL]` / `[AI_ASSIST]` |
| **Change Management** (4) | Pre-change impact, post-change validation, auto-rollback, compliance scanning | CM-01: Delete LB → list dependencies (Route53, CloudFront, ASG) → warn user | `[AI_ASSIST]` / `[MANUAL]` |
| **Cost Optimization** (3) | Idle LB detection, overspec recommendation, cross-AZ cost analysis | CO-01: LB with 0 connections for 24h → suggest deletion | `[AI_ASSIST]` |

### Decision Type Reference

| Label | Meaning | Response SLA | When Used |
|-------|---------|-------------|-----------|
| `[AUTO_HEAL]` | AI executes fix autonomously, notifies after | < 15 min | Healthy target re-registration, cross-zone enable, cert renewal trigger |
| `[AI_ASSIST]` | AI recommends, user confirms before execution | 1-4 h | Health check param tuning, EC2 resize, capacity scaling |
| `[MANUAL]` | AI identifies issue, requires human judgment | > 4 h | SG rule changes, delete resources, cost > $100/month changes |

### Auto-Heal Boundary Conditions

| Condition | Degrade To | Reason |
|-----------|-----------|--------|
| Involves data deletion | `[MANUAL]` | Irreversible |
| Cross-account operation | `[MANUAL]` | Needs cross-account auth |
| Cost change > $100/month | `[AI_ASSIST]` | User must be aware |
| First-seen anomaly type | `[AI_ASSIST]` | No historical pattern |
| Auto-heal fails 2 consecutive times | `[MANUAL]` | Prevent crash cascade |

***

## Cross-Skill Orchestration

### AIOps RCA Chains

| Scenario | Chain | Delegation |
|----------|-------|------------|
| **502 Error RCA** | ELB 502 → check target response → EC2 CPU/StatusCheck → VPC SG → CloudTrail events | `aws-elb-ops` → `aws-ec2-ops` → `aws-vpc-ops` → `aws-cloudtrail-ops` |
| **High Latency RCA** | TargetResponseTime ↗ → EC2 CPU/Mem → RDS slow queries → EKS Pod state | `aws-elb-ops` → `aws-ec2-ops` → (`aws-rds-ops`|`aws-eks-ops`) → `aws-cloudwatch-ops` |
| **Unhealthy Target RCA** | Health check fail → verify path → EC2 StatusCheck → SG/ACL → recent CloudTrail changes | `aws-elb-ops` → `aws-ec2-ops` → `aws-vpc-ops` → `aws-cloudtrail-ops` |
| **Connection Timeout RCA (NLB)** | NLB connection timeout → NAT Gateway conn count → EC2 port reachability → Flow Log drops | `aws-elb-ops` → `aws-vpc-ops` → `aws-ec2-ops` |
| **Cost Anomaly RCA** | Billing spike → split by service/region → find contributor → check CloudTrail for changes | `aws-cloudtrail-ops` → `aws-cloudwatch-ops` → `aws-elb-ops` |

### Layered Inspection Integration

See `aws-cloudwatch-ops/references/layered-inspection-template.md` for the three-layer deep inspection:
```
Network Layer    ← aws-elb-ops + aws-vpc-ops
Resource Layer   ← aws-ec2-ops + aws-rds-ops + aws-elasticache-ops + aws-dynamodb-ops
Application Layer← aws-eks-ops
```

***

## Operations

### Operation: Create Application Load Balancer

#### Pre-flight

**Step 1: Check CLI**
```bash
aws --version
```
Log: `[OK] AWS CLI v2.x.x detected` or `[FAIL] AWS CLI not found. Install: uv pip install awscli`

**Step 2: Load & Verify Credentials**
```bash
aws sts get-caller-identity --output json
```

Log format:
```
[SKILL] Loading AWS credentials...
[OK]   AWS_DEFAULT_REGION={{env.AWS_DEFAULT_REGION}} (from .env)
[OK]   AWS_ACCESS_KEY_ID=**** (from .env, masked)
[OK]   Credential verification passed
[OK]   Identity: arn:aws:iam::{{env.AWS_ACCOUNT_ID}}:user/xxx
```

On failure:
```
[FAIL] AWS credential verification failed.
AWS Error: <exact error message>
Action: See references/integration.md → Error Messages for diagnosis.
```

**Step 3 — AIOps: Pre-flight quota check (predictive)**
```bash
# Check remaining quota before creating
aws service-quotas get-service-quota \
  --service-code elasticloadbalancing \
  --quota-code L-53DA43FF \
  --output json | jq '.Quota.Value'
```
```
Remaining ALB quota: N. WARN if < 20% — creation may fail soon.
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log precise error; guide user to integration.md |
| VPC exists | `aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}` | HALT; verify VPC |
| Subnets exist | `aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}}` | HALT; verify subnets |
| **(AIOps) Quota check** | `aws service-quotas get-service-quota` | WARN; predict exhaustion |
| **(AIOps) Resource check** | `aws elbv2 describe-load-balancers` | Check if name collides with existing; suggest unique name |
| **(AIOps) Access logs** | Verify S3 bucket exists for logs | WARN; create bucket if needed |

#### Execute — CLI (Primary)
```bash
aws elbv2 create-load-balancer \
  --name "{{user.lb_name}}" \
  --type application \
  --subnets "{{user.subnet_ids}}" \
  --security-groups "{{user.security_group_ids}}" \
  --tags Key=AIOps,Value=true Key=CreatedBy,Value=harness-ai \
  --output json
```

**AIOps: Tag for automated lifecycle management**
Always add AIOps tags for resource tracking and cost analysis.

#### Execute — boto3 (Fallback)
```python
import boto3
client = boto3.client('elbv2', region_name='{{user.region}}')
response = client.create_load_balancer(
    Name='{{user.lb_name}}',
    Type='application',
    Subnets=['subnet-1', 'subnet-2'],
    SecurityGroups=['sg-1'],
    Tags=[{'Key': 'AIOps', 'Value': 'true'}]
)
```

#### Validate
```bash
aws elbv2 describe-load-balancers \
  --load-balancer-arns "{{output.load_balancer_arn}}" \
  --output json
```
Poll until `.State.Code` == "active" (max wait: 5 min).

**AIOps: Post-creation validation**
```bash
# Create initial monitoring baseline
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount --dimensions \
    Name=LoadBalancer,Value={{output.load_balancer_arn}} \
  --statistics Average --period 300 \
  --start-time "$(date -d '-5 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
Baseline recorded. Will be used for anomaly detection thresholds.

#### Recover
| Error | Action |
|-------|--------|
| InvalidSubnet | HALT; verify subnet IDs and availability zones |
| DuplicateLoadBalancerName | Use different name |
| QuotaExceeded | HALT; request quota increase |
| Throttling (429) | Backoff, retry 3x |

### Operation: Create Target Group

#### Execute — CLI (Primary)
```bash
aws elbv2 create-target-group \
  --name "{{user.tg_name}}" \
  --protocol HTTP \
  --port 80 \
  --vpc-id "{{user.vpc_id}}" \
  --health-check-path "/health" \
  --tags Key=AIOps,Value=true \
  --output json
```

**AIOps: Adaptive health check recommendation**
Based on the application type (detected via context or user input), recommend optimal health check parameters:

| Scenario | Recommended Health Check | Reason |
|----------|------------------------|--------|
| API service (latency-sensitive) | Interval=10s, Timeout=3s, HealthyThreshold=3, UnhealthyThreshold=2 | Fast detection & recovery |
| Batch processing | Interval=60s, Timeout=10s, HealthyThreshold=5, UnhealthyThreshold=3 | Reduce overhead, tolerate normal variance |
| Database / Critical service | TCP check, Interval=15s, Timeout=5s, HealthyThreshold=2 | Precise detection, fast failover |
| Lambda target | Interval=30s, Timeout=5s, HealthyThreshold=3, Matcher=200-499 | Handle cold start variance |

#### Validate
Poll until target group created (immediate).

### Operation: Register Targets

#### Execute — CLI (Primary)
```bash
aws elbv2 register-targets \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id=i-xxx Id=i-yyy \
  --output json
```

**AIOps: Canary registration (recommended for production)**
```bash
# Phase 1: Register 1 target first, validate health
aws elbv2 register-targets \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id=i-xxx
# Validate: poll target health
aws elbv2 describe-target-health \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id=i-xxx
# If healthy: proceed with remaining targets
# If unhealthy: HALT and diagnose before proceeding
```

### Operation: Create Listener

#### Execute — CLI (Primary)
```bash
aws elbv2 create-listener \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn="{{output.target_group_arn}}" \
  --output json
```

### Operation: Delete Load Balancer

**Safety Gate**: MUST obtain explicit user confirmation before deletion.

**AIOps: Pre-delete impact analysis (change management)**
```bash
# 1. Check Route53 references
aws route53 list-resource-record-sets --hosted-zone-id {{zone_id}} \
  --query "ResourceRecordSets[?AliasTarget.DNSName.contains(@, '{{output.dns_name}}')]"
# 2. Check CloudFront origins
aws cloudfront list-distributions --query \
  "DistributionList.Items[?Origins.Items[?DomainName.contains(@, '{{output.dns_name}}')]]"
# 3. Check Auto Scaling groups referencing this LB
aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?LoadBalancerNames.contains(@, '{{user.lb_name}}')]"
```

Impact Report:
```
[DEPENDENCIES] Deleting this LB affects:
  - Route53 alias records: N records (DNS resolution will break)
  - CloudFront origins: M distributions (CDN will 503)
  - Auto Scaling groups: K groups (new instances won't register)
[RISK LEVEL] {{HIGH|MEDIUM|LOW}}
```

#### Pre-delete Checks
1. List listeners: `aws elbv2 describe-listeners --load-balancer-arn {{output.load_balancer_arn}}`
2. Delete listeners first
3. Wait for listeners deleted (poll)

#### Execute — CLI (Primary)
```bash
aws elbv2 delete-load-balancer \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --output json
```

#### Validate
Poll until `.LoadBalancers` empty (max wait: 10 min).

**AIOps: Post-delete validation**
```bash
# Verify downstream references updated
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value={{output.target_group_arn}} \
  --statistics Average --period 300 \
  --start-time "$(date -d '-5 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
```
[INFO] No HealthyHostCount data — LB deletion confirmed.
[NOTE] Remember to clean up Route53 alias records and CloudFront origins if no longer needed.
```

### Operation: Describe Load Balancers

#### Execute — CLI
```bash
aws elbv2 describe-load-balancers --output json
# JSON path: .LoadBalancers[].{Name,LoadBalancerArn,State,VpcId,Type}
```

### Classic Load Balancer Operations

CLB uses `aws elb` commands (legacy):
- `aws elb create-load-balancer` (Classic)
- `aws elb describe-load-balancers`
- `aws elb delete-load-balancer`

***

## Health Check Configuration

| Parameter | ALB/NLB | CLB |
|-----------|---------|-----|
| HealthCheckPath | `/health` | TCP port or HTTP path |
| HealthCheckIntervalSeconds | 30 (default) | 30 |
| HealthCheckTimeoutSeconds | 5 | 5 |
| HealthyThresholdCount | 5 | 10 |
| UnhealthyThresholdCount | 2 | 2 |

### AIOps: Adaptive Health Check Adjustment

When repeated health check failures are detected, recommend parameter tuning:

| Failure Pattern | Suspected Cause | Recommended Adjustment |
|----------------|----------------|----------------------|
| Timeout errors | Application response too slow | Increase `TimeoutSeconds` (5→10), increase `IntervalSeconds` (30→60) |
| 404 errors | Wrong health check path | Change `HealthCheckPath` to `/` or `/healthz` |
| Flapping (alternating healthy/unhealthy) | Thresholds too tight | Increase `HealthyThresholdCount` (5→10), decrease `UnhealthyThresholdCount` (2→3) |
| All targets unhealthy simultaneously | Application outage or SG change | → trigger RC-03 RCA flow; do NOT adjust health checks |
| Slow recovery after deployment | Cold start / warmup period | Increase `HealthyThresholdCount` temporarily during rollout |

***

## Self-Healing Actions

### AH-01: Target Re-registration `[AUTO_HEAL]`

When single target is unhealthy but its EC2 instance is running:
```bash
# Step 1: Deregister
aws elbv2 deregister-targets \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id={{target_id}}

# Step 2: Wait for deregistration completion
aws elbv2 describe-target-health \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id={{target_id}}
# Poll until State == "unused" or target disappears

# Step 3: Wait 30s
sleep 30

# Step 4: Re-register
aws elbv2 register-targets \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id={{target_id}} Port={{port}}

# Step 5: Verify health
aws elbv2 describe-target-health \
  --target-group-arn "{{output.target_group_arn}}" \
  --targets Id={{target_id}}
# Poll until State == "healthy" or max 3 min
```
**Boundary**: If fails 2x → downgrade to `[MANUAL]`. If ALL targets unhealthy → trigger RC-03 first.

### AH-03: Cross-AZ Rebalance `[AUTO_HEAL]`

When traffic distribution across AZs is imbalanced (>30% std dev):
```bash
# Enable cross-zone load balancing
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true

# Verify
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn "{{output.load_balancer_arn}}" \
  --query "Attributes[?Key=='load_balancing.cross_zone.enabled']"
```
**Boundary**: If already enabled → delegate to `[AI_ASSIST]` to suggest adding targets in under-loaded AZ.

### AH-02: Health Check Parameter Tuning `[AI_ASSIST]`

Analyze failure pattern from access logs, then recommend:
```
Based on the last N health check failures:
- Pattern: timeout (XX%) / HTTP error (YY%) / connection refused (ZZ%)
- Analysis: [diagnosis text]
- Recommended: [specific param changes]
- Impact: faster detection / fewer false positives
- Confirm: Y/N
```

***

## Cost Optimization

### CO-01: Idle LB Detection

```bash
# Check if any LB has zero traffic
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name ActiveConnectionCount \
  --dimensions Name=LoadBalancer,Value={{output.load_balancer_arn}} \
  --statistics Sum --period 86400 \
  --start-time "$(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
```
Idle detection: if ActiveConnectionCount = 0 for 24h+:
→ [AI_ASSIST] "LB {{name}} has had 0 connections for 24h.
   Estimated monthly cost: $XX. Recommend deletion if no longer needed."
```

### CO-03: Overspec Detection

```bash
# Check if ALB is used but only L4 features needed
aws elbv2 describe-load-balancers --load-balancer-arns {{arn}} \
  --query "LoadBalancers[0].Type"
aws elbv2 describe-listeners --load-balancer-arn {{arn}} \
  --query "Listeners[].Protocol"
```
```
Overspec check: if ALB but all listeners are TCP-only:
→ [AI_ASSIST] "This ALB only uses TCP listeners. NLB could save ~XX%/month."
```

***

## Compliance & Security

### CM-04: Config Baseline Scan

```yaml
config_rules:
  - rule: deletion_protection.enabled
    check: "aws elbv2 describe-load-balancer-attributes --load-balancer-arn {{arn}} | jq '.Attributes[] | select(.Key==\"deletion_protection.enabled\") | .Value'"
    expected: "true"
    severity: HIGH
    action: "[AUTO_HEAL] enable if false"

  - rule: access_logs.s3.enabled
    check: "aws elbv2 describe-load-balancer-attributes ..."
    expected: "true"
    severity: MEDIUM
    action: "[AI_ASSIST] recommend enable"

  - rule: routing.http.drop_invalid_header_fields.enabled
    check: "..."
    expected: "true"
    severity: MEDIUM
    action: "[AUTO_HEAL] enable if false"

  - rule: waf protection
    check: "Check if WAF ACL is associated via CloudFront or ALB"
    expected: "associated"
    severity: HIGH
    action: "[MANUAL] requires WAF policy decision"
```

***

## Feedback & Learning

After each AIOps action, record outcome:
```
[AIOPS_FEEDBACK] Action: AH-01 target-re-registration
  LB: {{arn}}, Target: {{target_id}}
  Result: SUCCESS (healthy after 45s)
  Decision: [AUTO_HEAL]
  Previous failures: 0
  Learned: target was temporarily overloaded; re-registration resolved
  Knowledge: Add to pattern library for future similar cases
```

***

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded ELB types/LCU limits — use `describe-load-balancers` / `describe-target-groups`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths declared inline (no centralized block in this skill)
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Reference Files

- [Core Concepts & AIOps Guide](references/core-concepts.md)
- [AWS CLI Usage & AI Data Collection](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Troubleshooting & Self-Healing](references/troubleshooting.md)
- [Prompt Examples — AIOps Scenarios](references/prompt-examples.md)
- [AIOps Automation Engine — 全链路自动编排](references/aiops-automation-engine.md)
- [Integration Guide — CloudTrail & AWS Config](references/integration.md)
- [Example Configurations](assets/example-config.yaml)
- [Cross-Skill: Layered Inspection](../aws-cloudwatch-ops/references/layered-inspection-template.md)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, **recommended**). Every execution of
> `aws-elb-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `recommended` |
| `max_iterations` | `3` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `deregister-targets` — pre-flight MUST compute `count/healthy` ratio
  - ratio < 50%: `confirm=DEREGISTER <tg-arn> count=<n>`
  - ratio ≥ 50%: `confirm=DEREGISTER_DRAIN <tg-arn> count=<n>/<total>`
  - ratio == 100%: `confirm=DEREGISTER_ALL <tg-arn>` (total outage)
- `delete-load-balancer` — must have no listeners
- `delete-listener` — must have no rules
- `delete-rule` (default rule is **undeletable**; refuse)
- `delete-target-group` — must not be referenced
- `delete-trust-store` (mTLS) — must not be referenced
- `modify-load-balancer-attributes` disabling `deletion_protection` —
  `confirm=DISABLE_DELETION_PROTECTION <lb-arn>`

Relevant AWS rules from `gcl-spec.md` §8: A7 (region), A8 (resource
echo-back), A9 (no literal secrets in LB Tags), A10 (sts first
command).

See `references/rubric.md` for the 5-dimension rubric and `references/prompt-templates.md` for G/C/O skeletons.

## AIOps Delegate Contract

This skill is orchestrator-aware. When invoked by
`aws-aiops-orchestrator`, it MUST honor the delegate contract.

### Recognition

If the incoming prompt contains an `aiops_delegate:` block (see
[aws-aiops-orchestrator/references/delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md)),
parse and validate:

- `request_id` — non-empty string
- `parent_intent` — one of: health-check | rca | self-heal
  | cost-forecast | capacity-forecast | change-impact
  | compliance-scan | forensic
- `action_mode` — observe | recommend | auto-heal | manual
- `decision_tier` — AUTO_HEAL | AI_ASSIST | MANUAL
- `scope.resource_ids` — array (may be empty for discovery)

### Behavior rules

1. **Idempotency**: every write operation MUST accept an
   `idempotency_key` parameter. If the same key was executed within
   the last 24h, return the cached result with
   `aiops_context.status: "ok"` and
   `aiops_context.facts[*].deduplicated: true`.
2. **Confirmation gate**: any destructive operation (delete, terminate,
   deregister, detach, disable, rotate) MUST require a
   `confirmation_token`. If absent, refuse and return
   `aiops_context.status: "failed"` with summary
   `"confirmation_token required for destructive op"`.
3. **Decision tier respect**:
   - `decision_tier: MANUAL` — never execute writes; recommendations only.
   - `decision_tier: AI_ASSIST` — recommendations; execute only if
     `confirmation_token` is present.
   - `decision_tier: AUTO_HEAL` — execute non-destructive writes
     directly; destructive ones still require `confirmation_token`.
4. **Trace propagation**: every AWS CLI / boto3 call MUST include the
   `trace_id` from the delegate block in the User-Agent header
   (`User-Agent: aiops-orchestrator/<trace_id>`).
5. **Output format**: always include a final `aiops_context:` JSON
   block in the response, even on failure.

### Cross-reference

This skill participates in the orchestrator's runbook library. See
[aws-aiops-orchestrator/references/runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md)
for which runbooks invoke this skill.

