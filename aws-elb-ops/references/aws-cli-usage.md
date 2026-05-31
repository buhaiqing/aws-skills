# AWS CLI Usage — ELB

## Common JSON Paths (Centralized)

```
# elbv2:
#   Create LB:         .LoadBalancers[0].{LoadBalancerArn,DNSName}
#   Describe LBs:      .LoadBalancers[].{LoadBalancerName,Type,State.Code,VpcId,DNSName}
#   Create TG:         .TargetGroups[0].TargetGroupArn
#   Describe TGs:      .TargetGroups[].{TargetGroupName,Protocol,Port,HealthCheckConfig}
#   Describe Health:   .TargetHealthDescriptions[].{Target.Id,TargetHealth.State}
#   Create Listener:   .Listeners[0].ListenerArn
#   Create Rule:       .Rules[0].RuleArn
# elb (Classic):
#   Create CLB:        .LoadBalancerName
#   Describe CLBs:     .LoadBalancerDescriptions[].{LoadBalancerName,DNSName}
```

## Command Map (elbv2 for ALB/NLB)

| Goal | CLI Command |
|------|-------------|
| Create ALB/NLB | `aws elbv2 create-load-balancer` |
| Describe LBs | `aws elbv2 describe-load-balancers` |
| Delete LB | `aws elbv2 delete-load-balancer` |
| Create Target Group | `aws elbv2 create-target-group` |
| Describe Target Groups | `aws elbv2 describe-target-groups` |
| Delete Target Group | `aws elbv2 delete-target-group` |
| Register/Deregister Targets | `aws elbv2 register/deregister-targets` |
| Create Listener | `aws elbv2 create-listener` |
| Describe Listeners | `aws elbv2 describe-listeners` |
| Delete Listener | `aws elbv2 delete-listener` |
| Describe Target Health | `aws elbv2 describe-target-health` |
| Modify LB | `aws elbv2 modify-load-balancer-attributes` |

## Classic Load Balancer (elb)

| Goal | CLI Command |
|------|-------------|
| Create CLB | `aws elb create-load-balancer` |
| Describe CLBs | `aws elb describe-load-balancers` |
| Delete CLB | `aws elb delete-load-balancer` |
| Configure Health Check | `aws elb configure-health-check` |
| Register Instances | `aws elb register-instances-with-load-balancer` |

## Key CLI Conventions

### Global Service
ELB is **regional** — region parameter required.

### Output Format
Always use `--output json` for agent parsing.

### Load Balancer Types (elbv2)
- `application` — ALB (Layer 7)
- `network` — NLB (Layer 4)

## Common Patterns

### Create Application Load Balancer
```bash
aws elbv2 create-load-balancer \
  --name my-alb \
  --type application \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-xxx \
  --output json
```

### Create Network Load Balancer
```bash
aws elbv2 create-load-balancer \
  --name my-nlb \
  --type network \
  --subnets subnet-aaa subnet-bbb \
  --output json
```

### Create Target Group (HTTP)
```bash
aws elbv2 create-target-group \
  --name my-targets \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxx \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --output json
```

### Create Target Group (TCP for NLB)
```bash
aws elbv2 create-target-group \
  --name my-tcp-targets \
  --protocol TCP \
  --port 8080 \
  --vpc-id vpc-xxx \
  --output json
```

### Register EC2 Instances as Targets
```bash
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --targets Id=i-aaa Id=i-bbb \
  --output json
```

### Register Lambda as Target (ALB only)
```bash
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-lambda-tg/xxx \
  --targets Id=arn:aws:lambda:region:account:function:my-function \
  --output json
```

### Create Listener (HTTP)
```bash
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Create Listener (HTTPS with SSL)
```bash
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:region:account:certificate/xxx \
  --ssl-policy ELBSecurityPolicy-2016-08 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Describe Load Balancers
```bash
aws elbv2 describe-load-balancers --output json
# Filter by ARN
aws elbv2 describe-load-balancers \
  --load-balancer-arns arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --output json
```

### Describe Target Health
```bash
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Describe Listeners
```bash
aws elbv2 describe-listeners \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --output json
```

### Modify Load Balancer Attributes
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --attributes Key=deletion_protection.enabled,Value=true \
  --output json
```

### Delete Listener (Required before LB delete)
```bash
aws elbv2 delete-listener \
  --listener-arn arn:aws:elasticloadbalancing:region:account:listener/app/my-alb/xxx/yyy \
  --output json
```

### Delete Target Group (After deregistering targets)
```bash
aws elbv2 delete-target-group \
  --target-group-arn arn:aws:elasticloadbalancing:region:account:targetgroup/my-targets/xxx \
  --output json
```

### Delete Load Balancer
```bash
# Safety Gate: Confirm with user before deletion
aws elbv2 delete-load-balancer \
  --load-balancer-arn arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-alb/xxx \
  --output json
```

### Classic Load Balancer Operations
```bash
# Create CLB (legacy)
aws elb create-load-balancer \
  --load-balancer-name my-clb \
  --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80 \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-xxx \
  --output json

# Configure health check
aws elb configure-health-check \
  --load-balancer-name my-clb \
  --health-check Target=HTTP:80/health,Interval=30,Timeout=5,UnhealthyThreshold=2,HealthyThreshold=10 \
  --output json

# Register instances
aws elb register-instances-with-load-balancer \
  --load-balancer-name my-clb \
  --instances i-aaa i-bbb \
  --output json

# Describe CLBs
aws elb describe-load-balancers --output json

# Delete CLB
aws elb delete-load-balancer --load-balancer-name my-clb --output json
```

## ARN Format

| Resource | ARN Pattern |
|----------|-------------|
| ALB | `arn:aws:elasticloadbalancing:region:account:loadbalancer/app/name/id` |
| NLB | `arn:aws:elasticloadbalancing:region:account:loadbalancer/net/name/id` |
| CLB | `arn:aws:elasticloadbalancing:region:account:loadbalancer/name` |
| Target Group | `arn:aws:elasticloadbalancing:region:account:targetgroup/name/id` |
| Listener | `arn:aws:elasticloadbalancing:region:account:listener/app/name/id/port` |

## Waiters

ELB state transitions require polling:

| Operation | Wait Command | Terminal State |
|-----------|--------------|----------------|
| Create ALB | Poll describe | `available` |
| Create NLB | Poll describe | `active` |
| Delete LB | Poll describe | Not found |
| Register targets | Poll target health | `healthy` |

## CLI vs API Coverage

| Operation (API) | CLI Available | Notes |
|-----------------|---------------|-------|
| CreateLoadBalancer | ✅ | `create-load-balancer` (elbv2) |
| DescribeLoadBalancers | ✅ | `describe-load-balancers` (elbv2) |
| DeleteLoadBalancer | ✅ | `delete-load-balancer` (elbv2) |
| CreateTargetGroup | ✅ | `create-target-group` (elbv2) |
| RegisterTargets | ✅ | `register-targets` (elbv2) |
| DescribeTargetHealth | ✅ | `describe-target-health` (elbv2) |
| CreateListener | ✅ | `create-listener` (elbv2) |
| DeleteListener | ✅ | `delete-listener` (elbv2) |
| CreateRule | ✅ | `create-rule` (elbv2) |
| ModifyListener | ✅ | `modify-listener` (elbv2) |

## Credential Handling

CLI reads credentials in priority order:
1. Environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
2. Config file: `~/.aws/credentials`
3. IAM role (EC2/Lambda)

Verify:
```bash
aws sts get-caller-identity --output json
```

---

## AIOps: Data Collection & Diagnostic Commands

### CloudWatch Metrics Collection

#### ALB Latency & Error Analysis
```bash
# Get TargetResponseTime p50/p90/p99 over last hour (for latency anomaly)
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"p50","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p50"},"Label":"p50"},
    {"Id":"p90","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p90"},"Label":"p90"},
    {"Id":"p99","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":300,"Stat":"p99"},"Label":"p99"},
    {"Id":"ad","Expression":"ANOMALY_DETECTION_BAND(m1,2)","Label":"Anomaly Band"}
  ]' \
  --start-time "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Get error rate (5XX / total requests * 100)
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"HTTPCode_Target_5XX"},"Period":300,"Stat":"Sum"}},
    {"Id":"m2","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"RequestCount"},"Period":300,"Stat":"Sum"}},
    {"Id":"e1","Expression":"m1/m2*100","Label":"Error Rate %"}
  ]' \
  --start-time "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

#### Health Trending (Flapping Detection)
```bash
# Compare Minimum vs Average HealthyHostCount — divergence indicates flapping
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value={{tg_arn}} \
  --statistics Minimum --period 60 \
  --start-time "$(date -d '-30 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Also compare with Average: if Minimum << Average consistently, targets are flapping
```

#### Connection Pool Saturation
```bash
# Get ActiveConnectionCount and RejectedConnectionCount
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name ActiveConnectionCount \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistics Maximum --period 60 \
  --start-time "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# RejectedConnectionCount should always be 0
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name RejectedConnectionCount \
  --statistics Sum --period 3600 \
  --start-time "$(date -d '-24 hours' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# If Sum > 0 → capacity exhausted; recommend scaling or adding targets
```

### FORECAST Capacity Planning

```bash
# Predict TargetResponseTime 7 days ahead
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/ApplicationELB","MetricName":"TargetResponseTime"},"Period":3600,"Stat":"p99"},"Label":"p99 Latency"},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}
  ]' \
  --start-time "$(date -d '-14 days' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Predict ActiveConnectionCount for NLB
aws cloudwatch get-metric-data \
  --metric-data-queries '[
    {"Id":"m1","MetricStat":{"Metric":{"Namespace":"AWS/NetworkELB","MetricName":"ActiveFlowCount"},"Period":3600,"Stat":"Maximum"}},
    {"Id":"fc","Expression":"FORECAST(m1, \"linear\", 168)","Label":"7-Day Forecast"}
  ]' \
  --start-time "$(date -d '-14 days' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Cross-AZ Traffic Distribution Analysis

```bash
# Get RequestCount per AZ per TargetGroup
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} Name=TargetGroup,Value={{tg_arn}} Name=AvailabilityZone,Value=us-east-1a \
  --statistics Sum --period 3600 \
  --start-time "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Repeat per AZ. If std dev > 30% of mean → cross-zone imbalance.

# Check if cross-zone is enabled
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn "{{lb_arn}}" \
  --query "Attributes[?Key=='load_balancing.cross_zone.enabled']"
```

### CloudTrail Configuration Change Tracking

```bash
# Look for LB-related API events in last hour
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::ElasticLoadBalancing::LoadBalancer \
  --start-time "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --query "Events[].{Time:EventTime,Name:EventName,User:Username,Resource:Resources[0].ResourceName}"

# Look for SG changes around anomaly time
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
  --start-time "$(date -d '-2 hours' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Quota Utilization Check (Predictive)

```bash
# Check remaining ALB quota
aws service-quotas get-service-quota \
  --service-code elasticloadbalancing \
  --quota-code L-53DA43FF

# Check ALB usage count
aws elbv2 describe-load-balancers --query "length(LoadBalancers[?Type=='application'])"

# Predict quota exhaustion based on creation rate
# Usage: X of Y, growth: N/month, expected exhaustion: in M months
```

### Cost Analysis

```bash
# Check LCU consumption for cost optimization
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name ConsumedLCUs \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistics Average --period 86400 \
  --start-time "$(date -d '-30 days' -u +%Y-%m-%dT00:00:00Z)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Identify idle LBs (0 connections for 24h)
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name ActiveConnectionCount \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} \
  --statistics Sum --period 86400 \
  --start-time "$(date -d '-7 days' -u +%Y-%m-%dT00:00:00Z)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Compliance Check Commands

```bash
# Check deletion protection
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --query "Attributes[?Key=='deletion_protection.enabled']"

# Check access logs
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --query "Attributes[?Key=='access_logs.s3.enabled']"

# Check invalid header dropping (security)
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --query "Attributes[?Key=='routing.http.drop_invalid_header_fields.enabled']"
```

## AIOps: Auto-Remediation Command Sequences

### AH-01: Target Re-registration (AUTO_HEAL)

```bash
# Step 1: Verify target ID
TARGET_ID=i-xxx
TG_ARN=arn:aws:elasticloadbalancing:region:account:targetgroup/name/id
PORT=80

# Step 2: Deregister
aws elbv2 deregister-targets \
  --target-group-arn "$TG_ARN" \
  --targets Id=$TARGET_ID

# Step 3: Wait for deregistration (poll until gone)
while true; do
  STATE=$(aws elbv2 describe-target-health \
    --target-group-arn "$TG_ARN" \
    --targets Id=$TARGET_ID \
    --query "TargetHealthDescriptions[0].TargetHealth.State" \
    --output text 2>/dev/null)
  if [ "$STATE" == "unused" ] || [ -z "$STATE" ]; then
    echo "Deregistration complete"
    break
  fi
  echo "Waiting... state=$STATE"
  sleep 5
done

# Step 4: Wait 30s for stabilization
sleep 30

# Step 5: Re-register
aws elbv2 register-targets \
  --target-group-arn "$TG_ARN" \
  --targets Id=$TARGET_ID,Port=$PORT

# Step 6: Wait for healthy (max 3 min)
for i in $(seq 1 36); do
  STATE=$(aws elbv2 describe-target-health \
    --target-group-arn "$TG_ARN" \
    --targets Id=$TARGET_ID \
    --query "TargetHealthDescriptions[0].TargetHealth.State" \
    --output text)
  if [ "$STATE" == "healthy" ]; then
    echo "Target healthy after $((i * 5))s"
    break
  fi
  sleep 5
done

# Step 7: Verify via CloudWatch
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name HealthyHostCount \
  --dimensions Name=TargetGroup,Value="$TG_ARN" \
  --statistics Average --period 300 \
  --start-time "$(date -d '-10 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### AH-03: Enable Cross-Zone Load Balancing (AUTO_HEAL)

```bash
# Enable cross-zone
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true

# Verify
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --query "Attributes[?Key=='load_balancing.cross_zone.enabled']"

# Check traffic distribution improves after 5 min
sleep 300
aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value={{lb_arn}} Name=TargetGroup,Value={{tg_arn}} Name=AvailabilityZone,Value={{az}} \
  --statistics Sum --period 300 \
  --start-time "$(date -d '-5 minutes' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Compliance Fix: Enable Deletion Protection (AUTO_HEAL)

```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn {{lb_arn}} \
  --attributes Key=deletion_protection.enabled,Value=true
```

### Health Check Parameter Adjustment (AI_ASSIST)

```bash
# Current config
aws elbv2 describe-target-groups \
  --target-group-arns {{tg_arn}} \
  --query "TargetGroups[0].HealthCheckConfig"

# Modify (example: increase timeout for slow responses)
aws elbv2 modify-target-group \
  --target-group-arn {{tg_arn}} \
  --health-check-timeout-seconds 10

# Revert on failure
# If targets remain unhealthy after change:
# aws elbv2 modify-target-group --target-group-arn {{tg_arn}} \
#   --health-check-timeout-seconds 5
```

## AIOps: Cross-Module Diagnostic Command Sequences

### RC-01: 502 Error Diagnostic Chain

```bash
# 1. Local: Check LB status
echo "=== LB Status ==="
aws elbv2 describe-load-balancers \
  --load-balancer-arns {{lb_arn}} \
  --query "LoadBalancers[0].{Name,State:State.Code,DNSName}"

# 2. Local: Check target health
echo "=== Target Health ==="
aws elbv2 describe-target-health \
  --target-group-arn {{tg_arn}} \
  --query "TargetHealthDescriptions[].{Target:Target.Id,State:TargetHealth.State,Reason:TargetHealth.Description}"

# 3. Cross-module: Check EC2 status (aws-ec2-ops)
echo "=== EC2 Status ==="
aws ec2 describe-instance-status \
  --instance-ids {{target_id}} \
  --query "InstanceStatuses[].{Id:InstanceId,Check:InstanceStatus.Status,System:SystemStatus.Status}"

# 4. Cross-module: Check EC2 CPU (aws-ec2-ops / aws-cloudwatch-ops)
echo "=== EC2 CPU ==="
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value={{target_id}} \
  --statistics Average --period 300 \
  --start-time "$(date -d '-1 hour' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 5. Cross-module: Check for recent SG changes (aws-cloudtrail-ops)
echo "=== Recent Changes ==="
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::EC2::SecurityGroup \
  --start-time "$(date -d '-2 hours' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --query "Events[].{Time:EventTime,Name:EventName,Resource:Resources[0].ResourceName}"
```

### Health Check Path Verification

```bash
# From an instance in the same VPC, test the health check endpoint
# For HTTP health checks
curl -s -o /dev/null -w "%{http_code}" http://{{target_ip}}:{{target_port}}/health

# For HTTPS health checks
curl -sk -o /dev/null -w "%{http_code}" https://{{target_ip}}:{{target_port}}/health

# For TCP health checks
nc -zv {{target_ip}} {{target_port}} 2>&1
```

### Full Inventory Audit (Weekly)

```bash
# List all LBs with key metadata for cost and compliance audit
aws elbv2 describe-load-balancers --query \
  "LoadBalancers[].{Name:LoadBalancerName,Type:Type,Scheme:Scheme,State:State.Code,VpcId:VpcId,Created:CreationTime}"

# For each LB, check attributes
for lb_arn in $(aws elbv2 describe-load-balancers --query "LoadBalancers[].LoadBalancerArn" --output text); do
  echo "=== $lb_arn ==="
  aws elbv2 describe-load-balancer-attributes \
    --load-balancer-arn "$lb_arn" \
    --query "Attributes[?Key=='deletion_protection.enabled' || Key=='access_logs.s3.enabled' || Key=='load_balancing.cross_zone.enabled']"
done
```