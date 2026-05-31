# Troubleshooting & Self-Healing — ELB

## AIOps: Decision Type Reference

| Label | Meaning | Response SLA | Examples |
|-------|---------|-------------|----------|
| `[AUTO_HEAL]` | AI executes fix autonomously, notifies after | < 15 min | Target re-registration, cross-zone enable, deletion protection enable |
| `[AI_ASSIST]` | AI recommends, user confirms before executing | 1-4 h | Health check param tuning, EC2 resize, capacity scaling |
| `[MANUAL]` | AI identifies issue, requires human judgment | > 4 h | SG rule changes, delete LB, cost > $100/month changes |

### Auto-Heal Boundary Conditions

| Condition | Degrade To | Reason |
|-----------|-----------|--------|
| Involves data deletion | `[MANUAL]` | Irreversible |
| Cross-account operation | `[MANUAL]` | Needs cross-account auth |
| Cost change > $100/month | `[AI_ASSIST]` | User must be aware |
| First-seen anomaly type | `[AI_ASSIST]` | No historical pattern |
| Auto-heal fails 2 consecutive times | `[MANUAL]` | Prevent crash cascade |
| ALL targets unhealthy | `[AI_ASSIST]` | May indicate app outage, not LB issue |

---

## Self-Healing Actions Matrix

| ID | Scenario | Detection | Auto-Heal Action | Decision Type | Fallback |
|----|----------|-----------|-----------------|---------------|----------|
| **AH-01** | Single target unhealthy, EC2 running | `describe-target-health` → unhealthy | Deregister → 30s wait → Re-register → Verify healthy | `[AUTO_HEAL]` | 2 fails → `[MANUAL]` |
| **AH-02** | Unhealthy due to timeout | Access Logs: `target_processing_time` > health check timeout | Recommend adjusting health check params | `[AI_ASSIST]` | User confirms/rejects |
| **AH-03** | Cross-AZ traffic imbalance | CloudWatch: RequestCount std dev > 30% across AZs | Enable `load_balancing.cross_zone.enabled=true` | `[AUTO_HEAL]` | Already enabled → `[AI_ASSIST]` |
| **AH-04** | Deletion protection disabled | `describe-LB-attributes` → `deletion_protection.enabled=false` | Enable deletion protection | `[AUTO_HEAL]` | N/A |
| **AH-05** | Invalid header dropping disabled | `describe-LB-attributes` → `routing.http.drop_invalid_header_fields.enabled=false` | Enable invalid header dropping | `[AUTO_HEAL]` | N/A |
| **AH-06** | Access logs disabled | `describe-LB-attributes` → `access_logs.s3.enabled=false` | Recommend enabling with existing or new S3 bucket | `[AI_ASSIST]` | User confirms bucket |
| **AH-07** | All targets unhealthy | CloudWatch: `HealthyHostCount = 0` | → Trigger RC-03 RCA flow first; do NOT auto-heal | `[AI_ASSIST]` | See RC-03 |
| **AH-08** | Target flapping (3+ transitions/5min) | Poll `describe-target-health` history | Deregister flapping target; escalate to `[AI_ASSIST]` for root cause | `[AUTO_HEAL]` then `[AI_ASSIST]` | Target stays deregistered |

---

## AIOps: Root Cause Analysis (RCA) Flows

### RC-01: 502 Bad Gateway RCA

```
Trigger: HTTPCode_ELB_5XX > 0
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1 — Collect Evidence (within this module)                      │
├─────────────────────────────────────────────────────────────────────┤
│ # Check which targets returned 502                                  │
│ aws elbv2 describe-target-health --target-group-arn {{tg_arn}}      │
│                                                                      │
│ # Check error timing via CloudWatch                                 │
│ aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB │
│   --metric-name HTTPCode_ELB_5XX                                    │
│   --dimensions Name=LoadBalancer,Value={{lb_arn}}                   │
│   --statistics Sum --period 60                                      │
│   --start-time "{{T0-30m}}" --end-time "{{T0+5m}}"                  │
│                                                                      │
│ Step 2 — Delegate to Backend Check (aws-ec2-ops)                    │
│ # Check EC2 StatusCheck & CPU                                       │
│ aws ec2 describe-instance-status --instance-ids {{target_id}}       │
│ aws cloudwatch get-metric-statistics --namespace AWS/EC2            │
│   --metric-name CPUUtilization --dimensions Name=InstanceId,Value=i │
│                                                                      │
│ Step 3 — Delegate to Network Check (aws-vpc-ops)                    │
│ # Check SG rules allow health check traffic                         │
│ aws ec2 describe-security-groups --group-ids {{sg_id}}              │
│ # Check NACL for deny rules                                         │
│                                                                      │
│ Step 4 — Check for Recent Changes (aws-cloudtrail-ops)              │
│ # Look for LB/TG/SG changes around T0                               │
│ aws cloudtrail lookup-events --lookup-attributes                    │
│   AttributeKey=ResourceName,AttributeValue={{lb_arn}}               │
│   --start-time "{{T0-60m}}" --end-time "{{T0+5m}}"                  │
│                                                                      │
│ Step 5 — Generate RCA Report                                        │
│ ╔═══════════════════════════════════════════════════════════╗       │
│ ║ [RCA] 502 Error Report                                      ║       │
│ ║   T0: 2026-05-31T10:23:00Z                                 ║       │
│ ║   Root Cause: EC2 i-xxx CPUUtilization = 97% →            ║       │
│ ║     target processing timeout → 502                        ║       │
│ ║   Contributing: No CloudTrail changes found               ║       │
│ ║   Recommendation: [AI_ASSIST] Scale EC2 to larger type    ║       │
│ ║     or add more targets to target group                   ║       │
│ ╚═══════════════════════════════════════════════════════════╝       │
└─────────────────────────────────────────────────────────────────────┘
```

### RC-02: High Latency RCA

```
Trigger: TargetResponseTime p99 > 1000ms (baseline-dependent)
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1 — Quantify Latency                                           │
│ # Get p99 latency over last hour                                    │
│ aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB │
│   --metric-name TargetResponseTime                                  │
│   --statistics p99 --period 300                                     │
│                                                                      │
│ Step 2 — Cross-module Correlation                                   │
│ # Check EC2 CPU/Memory for same period                              │
│ # Check RDS slow queries if DB is target (aws-rds-ops)              │
│ # Check EKS pod metrics if K8s target (aws-eks-ops)                 │
│ # Check CloudTrail for deployment events                            │
│ aws cloudtrail lookup-events --lookup-attributes                    │
│   AttributeKey=EventName,AttributeValue=CreateDeployment            │
│                                                                      │
│ Step 3 — Access Log Deep Dive                                       │
│ # Analyze latency distribution by URL path                           │
│ aws logs start-query ... --query-string '                           │
│   fields request_url, target_processing_time * 1000 as t_ms        │
│   | stats avg(t_ms) as avg, pct(t_ms, 99) as p99 by request_url   │
│   | sort p99 desc | limit 10'                                       │
│                                                                      │
│ Step 4 — RCA Conclusion                                              │
│ Pattern Mapping:                                                     │
│   - ALL URLs slow → backend capacity or infra issue                  │
│   - Specific URL slow → application code issue                       │
│   - Gradual over time → capacity saturation                          │
│   - Sudden → deployment or config change                             │
└─────────────────────────────────────────────────────────────────────┘
```

### RC-03: Unhealthy Target RCA

```
Trigger: UnHealthyHostCount > 0
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1 — Characterize the failure                                    │
│ # Are ALL targets or just SOME unhealthy?                           │
│ aws elbv2 describe-target-health --target-group-arn {{tg_arn}}      │
│                                                                      │
│ ALL unhealthy → likely application/SG issue                          │
│ SOME unhealthy → likely target-specific issue                        │
│                                                                      │
│ Step 2 — Check Health Check Configuration                          │
│ aws elbv2 describe-target-groups --target-group-arns {{tg_arn}}     │
│   --query "TargetGroups[0].HealthCheckConfig"                        │
│ # Verify path returns 200: curl -I http://target:port/health        │
│                                                                      │
│ Step 3 — Check Target Instance (aws-ec2-ops)                        │
│ aws ec2 describe-instance-status --instance-ids {{target_id}}       │
│ # StatusCheckFailed? → EC2 issue                                    │
│ # System reachability check passed? → Application issue              │
│                                                                      │
│ Step 4 — Check Network (aws-vpc-ops)                                │
│ # SG allows health check traffic from LB?                           │
│ aws ec2 describe-security-groups --group-ids {{sg_id}}              │
│ # Check for recent SG/ACL changes via CloudTrail                    │
│                                                                      │
│ Step 5 — Check for Recent Changes (aws-cloudtrail-ops)             │
│ # Any SG, listener, or TG changes within last hour?                 │
│ aws cloudtrail lookup-events --lookup-attributes                    │
│   AttributeKey=ResourceType,AttributeValue=AWS::EC2::SecurityGroup  │
│                                                                      │
│ Step 6 — Action                                                     │
│ If single target unhealthy + EC2 running → [AUTO_HEAL] AH-01        │
│ If all targets unhealthy → [AI_ASSIST] application/SG issue         │
│ If recent SG change found → [MANUAL] review and revert              │
└─────────────────────────────────────────────────────────────────────┘
```

### RC-04: NLB Connection Timeout RCA

```
Trigger: ActiveFlowCount > 80% of limit or connection timeouts reported
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1 — Check NLB Metrics                                          │
│ aws cloudwatch get-metric-statistics --namespace AWS/NetworkELB     │
│   --metric-name ActiveFlowCount                                     │
│   --statistics Maximum --period 60                                  │
│                                                                      │
│ Step 2 — Check NAT Gateway (aws-vpc-ops)                            │
│ # High ActiveConnectionCount can cause packet drop                  │
│ aws cloudwatch get-metric-statistics --namespace AWS/NATGateway     │
│   --metric-name ActiveConnectionCount --statistics Maximum          │
│                                                                      │
│ Step 3 — Check Target Port Reachability                             │
│ # From within VPC, test port connectivity                           │
│ nc -zv {{target_ip}} {{target_port}}                                │
│                                                                      │
│ Step 4 — VPC Flow Log Analysis                                      │
│ # Look for REJECT or incomplete flows                               │
│                                                                      │
│ Step 5 — Action                                                     │
│ If NAT GW saturated → [AI_ASSIST] add NAT GW or distribute subnets  │
│ If target unreachable → delegate EC2/VPC                             │
│ If Flow Log shows REJECT → check SG/NACL                             │
└─────────────────────────────────────────────────────────────────────┘
```

### RC-05: Cost Anomaly RCA

```
Trigger: Billing spike detected (via CloudWatch AWS/Billing EstimatedCharges)
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1 — Check ConsumedLCU trend                                    │
│ aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB │
│   --metric-name ConsumedLCUs                                        │
│   --dimensions Name=LoadBalancer,Value={{lb_arn}}                   │
│   --statistics Sum --period 86400                                   │
│   --start-time "$(date -d '-30 days' ...)"                          │
│                                                                      │
│ Step 2 — Check traffic increase                                     │
│ aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB │
│   --metric-name RequestCount --statistics Sum                       │
│                                                                      │
│ Step 3 — Check if LBs were added/modified                           │
│ aws cloudtrail lookup-events --lookup-attributes                    │
│   AttributeKey=EventName,AttributeValue=CreateLoadBalancer          │
│   --start-time "$(date -d '-30 days' ...)"                          │
│                                                                      │
│ Step 4 — Action                                                     │
│ If traffic organic → [AI_ASSIST] forecast & budget alert             │
│ If LB added → review if new LB is needed                            │
│ If traffic spike but no value → [AI_ASSIST] investigate              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Change Impact Analysis & Rollback

### CM-01: Pre-Change Impact Analysis

Before any destructive or high-risk operation, assess blast radius:

```bash
# Check all resources referencing this LB
aws route53 list-resource-record-sets --hosted-zone-id {{zone_id}} \
  --query "ResourceRecordSets[?AliasTarget.DNSName.contains(@, '{{dns_name}}')]"
aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?DomainName.contains(@, '{{dns_name}}')]]"
aws autoscaling describe-auto-scaling-groups \
  --query "AutoScalingGroups[?LoadBalancerNames.contains(@, '{{lb_name}}')]"
aws elbv2 describe-target-groups \
  --load-balancer-arn {{lb_arn}}
```

Impact Report Format:
```
[IMPACT ANALYSIS] Operation: {{operation}} on {{resource}}
  Risk Level: [HIGH|MEDIUM|LOW]
  Dependencies:
    - Route53 alias records: N
    - CloudFront origins: M
    - Auto Scaling groups: K
    - Target groups: P
  If this operation fails:
    - Traffic loss: {{estimate}}
    - Recovery time: {{estimate}}
  Safety Gate: Confirm with user before proceeding
```

### CM-03: Automatic Rollback

When a post-change validation fails, execute rollback:

```bash
# Rollback target group configuration
# 1. Remember previous target registrations
aws elbv2 describe-target-health --target-group-arn {{tg_arn}} \
  --query "TargetHealthDescriptions[].Target" > /tmp/targets_before.json

# 2. Execute change (e.g., modify health check)
aws elbv2 modify-target-group --target-group-arn {{tg_arn}} \
  --health-check-path /new-path

# 3. Validate: check if targets become unhealthy
# If unhealthy within 2 min → rollback
if [ "$(aws elbv2 describe-target-health --target-group-arn {{tg_arn}} \
  --query "TargetHealthDescriptions[?TargetHealth.State=='unhealthy'] | length(@)")" -gt 0 ]; then
  echo "[ROLLBACK] Reverting health check configuration"
  aws elbv2 modify-target-group --target-group-arn {{tg_arn}} \
    --health-check-path /health
fi
```

---

## Common Error Codes

| Error | Agent Action |
|-------|-------------|
| DuplicateLoadBalancerName (400) | HALT; use different name |
| InvalidSubnet (400) | HALT; verify subnets |
| InvalidSecurityGroup (400) | HALT; verify SG |
| InvalidVpcId (400) | HALT; verify VPC |
| InvalidParameterValue (400) | Fix parameter; retry once |
| QuotaExceeded (400) | HALT; request quota increase |
| ListenerNotFound (404) | HALT; verify ARN |
| LoadBalancerNotFound (404) | HALT; verify ARN |
| TargetGroupNotFound (404) | HALT; verify ARN |
| ResourceInUse (409) | Remove dependencies first |
| InvalidConfigurationRequest (400) | Review config; retry once |
| ThrottlingException (429) | Backoff; retry 3x |
| ServiceUnavailable (500) | Retry 3x; HALT if persists |

## Diagnostic Order

1. **Verify credentials**: `aws sts get-caller-identity`
2. **Verify VPC**: `aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}`
3. **Verify subnets**: `aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}}`
4. **Verify security groups**: `aws ec2 describe-security-groups --group-ids {{user.sg_ids}}`
5. **Verify load balancer exists**: `aws elbv2 describe-load-balancers --load-balancer-arns {{arn}}`
6. **Verify target group exists**: `aws elbv2 describe-target-groups --target-group-arns {{arn}}`
7. **Check target health**: `aws elbv2 describe-target-health --target-group-arn {{arn}}`

### AIOps Enhanced Diagnostic Order

For anomaly scenarios, extend with:

8. **Check CloudWatch metrics trend** (30 min window): TargetResponseTime, HTTPCode_5XX, HealthyHostCount
9. **Check CloudTrail events** (60 min window): Any LB/SG/TG changes around anomaly time
10. **Cross-module check**: EC2 status, VPC SG audit (via delegation)
11. **Pattern match**: Compare against known failure patterns (see RC flows above)

---

## Common Issues

### DuplicateLoadBalancerName

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create LB | Name already in use | Use different name (names are unique per region) |
| Name reused after delete | ELB retains deleted LB name for protection period | Wait or use different name |

### InvalidSubnet

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Subnet not found | Wrong subnet ID | Verify subnet exists in region |
| Subnets not same VPC | Subnets from different VPCs | Use subnets from same VPC |
| Subnet not in valid AZ | Availability Zone mismatch | Use subnets in same AZs as LB |

### InvalidSecurityGroup

| Symptom | Cause | Resolution |
|---------|-------|------------|
| SG not found | Wrong security group ID | Verify SG exists in region |
| SG not same VPC | SG from different VPC | Use SG from same VPC as subnets |
| NLB with SG | NLB does not support SG | Remove SG parameter for NLB |

### LoadBalancerNotFound

| Symptom | Cause | Resolution |
|---------|-------|------------|
| ARN not found | Wrong ARN format | Verify full ARN including region and account |
| LB deleted | LB already deleted | Recreate LB if needed |
| Wrong region | LB in different region | Check correct region |

### ResourceInUse (Delete Conflict)

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot delete LB | Listeners attached | Delete listeners first |
| Cannot delete LB | Target groups referenced | Delete listeners referencing TG |
| Cannot delete TG | Targets registered | Deregister targets first |
| Cannot delete TG | Referenced by listener | Delete listener or modify default action |

### Target Health Issues

| Symptom | Cause | Resolution | AIOps Action |
|---------|-------|------------|--------------|
| All targets unhealthy | Health check path invalid | Verify health check path returns 200 | `[AI_ASSIST]` → Check app status |
| Targets timing out | Port mismatch | Verify target port matches health check port | `[AI_ASSIST]` → Verify port config |
| Targets draining | Deregistration in progress | Wait for draining to complete | `[AUTO_HEAL]` → Wait and verify |
| Targets unavailable | Health check disabled | Enable health checks | `[AUTO_HEAL]` → Re-enable |
| Single target flapping | Application transient | Deregister→Re-register | `[AUTO_HEAL]` → AH-01 |
| Gradual degradation | Capacity saturation | Scale up targets | `[AI_ASSIST]` → Recommend scaling |

### Listener Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot create HTTPS listener | Certificate not found | Verify ACM certificate ARN |
| Cannot create HTTPS listener | Certificate not in region | Use certificate in same region |
| Listener redirect fails | Invalid redirect URL | Fix redirect URL format |
| Authentication fails | Cognito/OIDC config wrong | Verify IdP configuration |

### Cross-Zone Load Balancing

| Symptom | Cause | Resolution | AIOps Action |
|---------|-------|------------|--------------|
| Uneven traffic distribution | Cross-zone disabled | Enable cross-zone load balancing | `[AUTO_HEAL]` → AH-03 |
| Targets in single AZ overloaded | Cross-zone disabled | Enable or distribute targets across AZs | `[AUTO_HEAL]` → AH-03 |

### NLB Specific Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Cannot resolve DNS | NLB not yet provisioned | Wait for NLB to become active |
| High latency | Cross-zone disabled | Enable cross-zone for balanced distribution |
| Connection resets | Health check too aggressive | Adjust health check thresholds |
| Source IP not visible | Check target type | Use instance or IP target type |

### ALB Specific Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| 502 Bad Gateway | Target not responding | → Trigger RC-01 RCA flow |
| 503 Service Unavailable | No healthy targets | Register targets and verify health |
| 504 Gateway Timeout | Idle timeout too short | Increase idle_timeout attribute |
| HTTP/2 not working | HTTP/2 disabled | Enable routing.http2.enabled attribute |

---

## AIOps: Predictive Issue Detection

### Pre-emptive Checks During Normal Operation

Run periodically (e.g., weekly) to catch issues before they affect users:

```bash
# 1. Check pending target deregistrations
# 2. Check certificate expiry (via aws-acm-ops)
# 3. Check quota utilization trends
# 4. FORECAST capacity for next 7 days
# 5. Check compliance: deletion_protection, access_logs
```

```
[AIOPS_PREVENTIVE] Check Report:
  ✅ Quota utilization: ALB 12/20 (60%), TG 45/3000 (1.5%) — OK
  ✅ Capacity forecast: No saturation predicted in next 7 days
  ✅ Compliance: deletion_protection=true, access_logs=false ⚠️
    → [AI_ASSIST] Enable access logs for observability
```

---

## Permissions Required

| Action | Minimum IAM Permissions |
|--------|-------------------------|
| Create LB | `elasticloadbalancing:CreateLoadBalancer` |
| Describe LB | `elasticloadbalancing:DescribeLoadBalancers` |
| Delete LB | `elasticloadbalancing:DeleteLoadBalancer` |
| Create Target Group | `elasticloadbalancing:CreateTargetGroup` |
| Register Targets | `elasticloadbalancing:RegisterTargets` |
| Describe Target Health | `elasticloadbalancing:DescribeTargetHealth` |
| Create Listener | `elasticloadbalancing:CreateListener` |
| Delete Listener | `elasticloadbalancing:DeleteListener` |
| Create Rule | `elasticloadbalancing:CreateRule` |
| Modify LB Attributes | `elasticloadbalancing:ModifyLoadBalancerAttributes` |
| Describe VPC/Subnets | `ec2:DescribeVpcs`, `ec2:DescribeSubnets` |
| Describe Security Groups | `ec2:DescribeSecurityGroups` |
| **(AIOps)** Describe CloudWatch | `cloudwatch:GetMetricStatistics`, `cloudwatch:GetMetricData` |
| **(AIOps)** Describe CloudTrail | `cloudtrail:LookupEvents` |
| **(AIOps)** Describe Service Quotas | `service-quotas:GetServiceQuota` |

## Cleanup Sequence (Delete Load Balancer)

```
1. List listeners: describe-listeners --load-balancer-arn {{lb_arn}}
2. Delete each listener: delete-listener --listener-arn {{listener_arn}}
3. List target groups: describe-target-groups --load-balancer-arn {{lb_arn}}
4. Deregister targets: deregister-targets for each TG
5. Delete target groups: delete-target-group for each
6. Delete load balancer: delete-load-balancer --load-balancer-arn {{lb_arn}}
```

### AIOps Cleanup Enhancement
Before step 1, run CM-01 impact analysis to warn about downstream dependencies.

## Cleanup Sequence (Delete Target Group)

```
1. Deregister all targets: deregister-targets --target-group-arn {{tg_arn}}
2. Verify no targets: describe-target-health should return empty
3. Delete target group: delete-target-group --target-group-arn {{tg_arn}}
```

## Health Check Troubleshooting

```bash
# Check target health status
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/name/id \
  --output json

# Common health check issues:
# 1. Path returns 404: Fix health check path
# 2. Timeout: Increase timeout or fix application
# 3. Wrong port: Verify target port matches config

# Verify health check configuration
aws elbv2 describe-target-groups \
  --target-group-arns arn:aws:elasticloadbalancing:region:account:targetgroup/name/id \
  --output json | jq '.TargetGroups[0].HealthCheckConfig'
```

### AIOps Health Diagnosis

```bash
# Advanced health trend analysis
# Check flapping (targets changing state frequently)
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value={{tg_arn}} \
  --statistics Minimum --period 60 \
  --start-time "$(date -d '-30 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
```
Flapping Detection: if Minimum differs from Average significantly over short windows
→ "Target group {{name}} shows health flapping pattern (min=3, avg=4.2 over 30 min)"
→ "3 targets transitioning between healthy/unhealthy states"
→ Action: [AUTO_HEAL] AH-01 for affected targets
```

## Listener Troubleshooting

```bash
# Check listener configuration
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id \
  --output json

# Verify SSL certificate
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:region:account:certificate/id \
  --output json

# Check listener rules
aws elbv2 describe-rules \
  --listener-arn arn:aws:elasticloadbalancing:region:account:listener/app/name/id/port \
  --output json
```

## Recovery Actions

| Error | Max Retries | Action |
|-------|-------------|--------|
| 5xx ServiceUnavailable | 3 | Backoff 2s, 4s, 8s; HALT after 3 |
| 429 ThrottlingException | 3 | Exponential backoff |
| 400 InvalidParameterValue | 1 | Fix; retry once |
| 400 DuplicateLoadBalancerName | 0 | HALT; use different name |
| 409 ResourceInUse | 0 | HALT; clean dependencies first |
| 404 LoadBalancerNotFound | 0 | HALT; verify ARN |
| 404 TargetGroupNotFound | 0 | HALT; verify ARN |

## CloudWatch Metrics for Troubleshooting

| Metric | Description |
|--------|-------------|
| TargetResponseTime (ALB) | Backend latency |
| HTTPCode_Target_4XX/5XX (ALB) | Backend response codes |
| HTTPCode_ELB_5XX (ALB) | ELB errors (502, 503, 504) |
| ActiveConnectionCount (NLB) | Connection count |
| HealthyHostCount (ALB/NLB) | Healthy target count |
| UnHealthyHostCount (ALB/NLB) | Unhealthy target count |

## Diagnostic Commands

```bash
# Full LB status
aws elbv2 describe-load-balancers \
  --load-balancer-arns {{lb_arn}} \
  --output json | jq '.LoadBalancers[0].{Name,State,Type,DNSName}'

# Full target group status
aws elbv2 describe-target-groups \
  --target-group-arns {{tg_arn}} \
  --output json | jq '.TargetGroups[0].{TargetGroupName,Protocol,Port,HealthCheckConfig}'

# Target health breakdown
aws elbv2 describe-target-health \
  --target-group-arn {{tg_arn}} \
  --output json | jq '.TargetHealthDescriptions[].{TargetId,TargetHealth}'

# LB attributes
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --output json
```

## Access Logs

Enable access logs for troubleshooting:
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --attributes Key=access_logs.s3.enabled,Value=true Key=access_logs.s3.bucket,Value={{bucket_name}} \
  --output json
```

### AIOps: Access Log Analysis for Error Diagnosis

```bash
# Analyze 5XX errors by target IP
aws logs start-query \
  --log-group-name "/aws/elb/{{lb_name}}" \
  --start-time "$(date -d '-1 hour' +%s)" --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, client_ip, target_ip, target_processing_time
    | filter elb_status_code >= 500
    | stats count() as errors, avg(target_processing_time) as avg_latency by target_ip
    | sort errors desc'

# Analyze latency by path
aws logs start-query --log-group-name "/aws/elb/{{lb_name}}" \
  --start-time "$(date -d '-1 hour' +%s)" --end-time "$(date +%s)" \
  --query-string 'fields @timestamp, request_url, target_processing_time
    | stats avg(target_processing_time) as avg_latency,
             max(target_processing_time) as max_latency by request_url
    | sort avg_latency desc
    | limit 20'
```

---

## AIOps: Feedback Recording

After each AIOps action, record the result for model improvement:

```
[AIOPS_FEEDBACK]
  Timestamp: {{now}}
  Scenario: RC-03 (Unhealthy Target RCA)
  LB ARN: {{lb_arn}}
  Target: {{target_id}}
  Root Cause: EC2 CPU 97% → target timed out
  Action: [AI_ASSIST] Recommended EC2 t3.medium→t3.large
  User Decision: Approved
  Outcome: After resize, target returned healthy, latency dropped from 2500ms to 120ms
  Success: true
  Learnings:
    - Add EC2 CPU > 90% as early trigger for capacity RCA
    - Threshold for timeout should be 2000ms not 5000ms for this app
```
