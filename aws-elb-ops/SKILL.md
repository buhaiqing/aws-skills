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
  last_updated: '2026-06-26'
  runtime: Harness AI Agent
  cli_applicability: dual-path
  aiops_level: full-chain
  version: "2.4.0"
  destructive_ops_require_confirm: true
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

AWS Elastic Load Balancing (ELB) distributes incoming traffic across targets. Covers **ALB** (Layer 7), **NLB** (Layer 4), and **CLB** (legacy) with full AIOps closed-loop support.

## Trigger & Scope

### SHOULD Use When
- User mentions "ELB", "Load Balancer", "ALB", "NLB", or "CLB"
- CRUD on **Load Balancers** or **Target Groups**
- Keywords: balance, distribute, health-check, listener, target-group
- **(AIOps)** "502/503/504 errors", "latency spikes", "health check failures"
- **(AIOps)** "why are targets unhealthy", "optimize ELB cost", "auto-heal targets"

### SHOULD NOT Use When
- EC2 instances → `aws-ec2-ops`
- VPC/subnets → `aws-vpc-ops`
- SSL certificates → `aws-acm-ops`
- Route53 DNS → `aws-route53-ops`
- CloudWatch alarms → `aws-cloudwatch-ops`
- CloudTrail analysis → `aws-cloudtrail-ops`

## Load Balancer Types

| Type | Layer | Use Case | CLI Service |
|------|-------|----------|-------------|
| ALB | Layer 7 (HTTP/HTTPS) | Web apps, microservices | `elbv2` |
| NLB | Layer 4 (TCP/UDP) | High performance, gaming, IoT | `elbv2` |
| CLB | Layer 4/7 (legacy) | Legacy apps (deprecated) | `elb` |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | NEVER ask; fail if unset |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | NEVER ask; fail if unset |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default if skill allows |
| `{{user.lb_name}}` | User input | Ask once; reuse |
| `{{user.lb_type}}` | User input | ALB, NLB, or CLB |
| `{{user.vpc_id}}` | User input | Ask once; reuse |
| `{{user.safety_confirm}}` | Explicit confirm | Required for destructive ops |
| `{{output.load_balancer_arn}}` | API response | Parse `.LoadBalancers[0].LoadBalancerArn` |

## Execution Flow Pattern

Every operation: **Pre-flight → Execute → Validate → Recover**
AIOps scenarios add: **Data Collection → Detection → RCA → Decision → Action → Feedback**

## Representative Operation: Create ALB

### Pre-flight

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity --output json` | HALT; log error |
| VPC exists | `aws ec2 describe-vpcs --vpc-ids {{user.vpc_id}}` | HALT; verify VPC |
| Subnets exist | `aws ec2 describe-subnets --subnet-ids {{user.subnet_ids}}` | HALT; verify subnets |
| Quota check | `aws service-quotas get-service-quota --service-code elasticloadbalancing --quota-code L-53DA43FF` | WARN if < 20% |

### Execute — CLI (Primary)
```bash
aws elbv2 create-load-balancer \
  --name "{{user.lb_name}}" --type application \
  --subnets "{{user.subnet_ids}}" --security-groups "{{user.security_group_ids}}" \
  --tags Key=AIOps,Value=true Key=CreatedBy,Value=harness-ai \
  --output json
```

### Validate
```bash
aws elbv2 describe-load-balancers \
  --load-balancer-arns "{{output.load_balancer_arn}}" --output json
```
Poll until `.State.Code` == "active" (max 5 min).

### Recover
| Error | Action |
|-------|--------|
| InvalidSubnet | HALT; verify subnet IDs |
| DuplicateLoadBalancerName | Use different name |
| QuotaExceeded | HALT; request quota increase |
| Throttling (429) | Backoff, retry 3x |

## Legacy Operations: CLB (Deprecated)

> ⚠️ **Classic Load Balancer** is a legacy service **deprecated by AWS**. Use ALB or NLB for new workloads. CLB commands use the `aws elb` CLI service (not `elbv2`).

### Operation: Create CLB

#### Pre-flight
CLB shares the same pre-flight checks as ALB (CLI version, credentials, VPC, subnets).

#### Execute — CLI (Primary)
```bash
aws elb create-load-balancer \
  --load-balancer-name "{{user.lb_name}}" \
  --listeners Protocol=HTTP,LoadBalancerPort=80,InstanceProtocol=HTTP,InstancePort=80 \
  --subnets "{{user.subnet_ids}}" \
  --security-groups "{{user.security_group_ids}}" \
  --output json
```

#### Execute — boto3 (Fallback)
```python
clb_client = boto3.client('elb')
response = clb_client.create_load_balancer(
    LoadBalancerName='{{user.lb_name}}',
    Listeners=[
        {'Protocol': 'HTTP', 'LoadBalancerPort': 80,
         'InstanceProtocol': 'HTTP', 'InstancePort': 80}
    ],
    Subnets=['{{user.subnet_ids}}'],
    SecurityGroups=['{{user.security_group_ids}}']
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
```bash
aws elb describe-load-balancers \
  --load-balancer-names "{{user.lb_name}}" --output json
```
Check `.LoadBalancerDescriptions[0].HealthCheck.Target` is set.

#### Recover
| Error | Action |
|-------|--------|
| DuplicateLoadBalancerName | Use different name |
| CertificateNotFound | Verify SSL cert ARN |
| InvalidSubnet | HALT; verify subnet IDs |
| Throttling | Backoff, retry 3x |

### Operation: Configure Health Check

#### Execute — CLI (Primary)
```bash
aws elb configure-health-check \
  --load-balancer-name "{{user.lb_name}}" \
  --health-check Target=HTTP:80/health,Interval=30,Timeout=5,UnhealthyThreshold=2,HealthyThreshold=10 \
  --output json
```

#### Execute — boto3 (Fallback)
```python
clb_client.configure_health_check(
    LoadBalancerName='{{user.lb_name}}',
    HealthCheck={
        'Target': 'HTTP:80/health',
        'Interval': 30, 'Timeout': 5,
        'UnhealthyThreshold': 2, 'HealthyThreshold': 10
    }
)
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
```bash
aws elb describe-load-balancers \
  --load-balancer-names "{{user.lb_name}}" --output json \
  --query ".LoadBalancerDescriptions[0].HealthCheck"
```

#### Recover
| Error | Action |
|-------|--------|
| AccessPointNotFound | HALT — verify CLB name exists |
| InvalidConfigurationRequest | Check health check target format (Protocol:Port/Path) |
| Throttling | Backoff, retry 3x |

### Operation: Delete CLB
**Safety Gate**: must obtain explicit `confirm=DELETE_CLB {{user.lb_name}}` before execution.

#### Pre-flight
```bash
aws elb describe-load-balancers --load-balancer-names "{{user.lb_name}}" --output json
```
Check if instances are registered; warn if any exist.

#### Execute — CLI (Primary)
```bash
aws elb delete-load-balancer --load-balancer-name "{{user.lb_name}}" --output json
```

#### Execute — boto3 (Fallback)
```python
clb_client.delete_load_balancer(LoadBalancerName='{{user.lb_name}}')
```
See `references/boto3-sdk-usage.md` for full patterns.

#### Validate
```bash
aws elb describe-load-balancers --load-balancer-names "{{user.lb_name}}" --output json
```
Expect `LoadBalancerNotFound` error — confirmed deleted.

#### Recover
| Error | Action |
|-------|--------|
| AccessPointNotFound | Already deleted — OK |
| DependencyThrottle | Backoff, retry 3x |
| OperationNotPermitted | HALT — check if CLB has registered instances |

## Quality Gate (GCL)

| Setting | Value |
|---|---|
| Class | `recommended` |
| `max_iterations` | `3` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops require `{{user.safety_confirm}}`:
- `deregister-targets` — ratio < 50%: `confirm=DEREGISTER`; ≥ 50%: `confirm=DEREGISTER_DRAIN`; 100%: `confirm=DEREGISTER_ALL`
- `delete-load-balancer` — ALB/NLB: must have no listeners; `confirm=DELETE_LB`
- `delete-load-balancer` — CLB: `confirm=DELETE_CLB <name>`
- `delete-rule` (default rule is **undeletable**)
- `modify-load-balancer-attributes` disabling deletion protection — `confirm=DISABLE_DELETION_PROTECTION`

See `references/rubric.md` and `references/prompt-templates.md` for full GCL details.

## AIOps Delegate Contract

Orchestrator-aware. Accepts: health-check, rca, self-heal, change-impact. Rules: idempotency (24h TTL), destructive ops require `confirmation_token`, decision tier respect (MANUAL/AI_ASSIST/AUTO_HEAL), trace propagation via User-Agent. Full contract: `aws-aiops-orchestrator/references/delegate-routing.md`

## Token Efficiency

- TE-1: No hardcoded tables — use `describe-*` APIs
- TE-2: Inline comments only in boto3 (no docstrings)
- TE-3: Compact error tables
- TE-4: JSON paths centralized at top of `references/aws-cli-usage.md`
- TE-5: YAML anchors in `assets/example-config.yaml`
- TE-6: Complete flows only in SKILL.md

## Reference Files

- [Core Concepts & AIOps](references/core-concepts.md) — metrics, scenarios, cost, compliance
- [AWS CLI Usage](references/aws-cli-usage.md) — all commands + JSON paths
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Troubleshooting & Self-Healing](references/troubleshooting.md) — RCA flows, AH actions, errors
- [Prompt Examples](references/prompt-examples.md)
- [Integration](references/integration.md)
- [Example Configs](assets/example-config.yaml)
- [GCL Rubric](references/rubric.md)
- [GCL Prompts](references/prompt-templates.md)
