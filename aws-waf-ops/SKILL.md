---
name: aws-waf-ops
description: >-
  Use when the user needs to create, configure, or manage AWS WAF Web ACLs to
  protect ALB, CloudFront, API Gateway, or AppSync resources from common web
  exploits; configure AWS managed rule groups, rate-based rules, IP set, regex
  pattern sets, or custom rules; associate or disassociate Web ACLs with AWS
  resources; set up WAF logging, metrics, and sampled requests for monitoring;
  detect and mitigate DDoS or application-layer attacks.

  (AIOps) Use when detecting anomalous traffic patterns (request rate spikes,
  unusual source IP distribution, high block rates), automatically enabling
  rate limiting or AWS Managed Rules for DDoS mitigation, auditing WAF rule
  effectiveness via CloudWatch metrics, or correlating WAF blocks with ALB
  error rates.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials with WAFv2,
  WAF Regional permissions. Requires ALB, CloudFront, or API Gateway resource
  for Web ACL association.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-05-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  aiops_level: full-chain
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-elb-ops             # WAF ACL association with ALB
    - aws-cloudfront-ops      # WAF ACL association with CloudFront
    - aws-cloudwatch-ops      # WAF metrics, anomaly detection
    - aws-cloudtrail-ops      # ACL change audit
  orchestrator_aware: true
  orchestrator_compat: ">=0.1.0"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal']
    produces_facts: ['metric', 'log', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS WAF Operations Skill

## Overview

AWS WAF (Web Application Firewall) protects web applications from common web exploits that could affect availability, compromise security, or consume excessive resources. This skill covers **Web ACLs, rule groups, rate-based rules, IP sets, regex pattern sets, logging, and AIOps-driven DDoS mitigation**.

## Trigger & Scope

### SHOULD Use When
- User mentions "WAF", "Web ACL", "firewall", "rate limit", "block IP"
- Task involves creating or managing Web ACLs
- User needs to protect ALB, CloudFront, or API Gateway from web attacks
- Keywords: waf, webacl, rule-group, rate-limit, ip-set, block, allow
- **(AIOps)** Traffic anomaly detected on ALB — possible DDoS
- **(AIOps)** WAF blocked request rate suddenly changes
- **(AIOps)** Audit WAF rule effectiveness or cost

### SHOULD NOT Use When
- ALB/load balancer configuration → delegate to: `aws-elb-ops`
- CloudFront distribution config → delegate to: `aws-cloudfront-ops`
- API Gateway config → out of scope; use API Gateway CLI/SDK directly
- Shield Advanced → out of scope; use Shield CLI/SDK directly
- EC2 security group → delegate to: `aws-vpc-ops`

## WAF Version

This skill targets **WAF v2** (`wafv2` CLI / API). Classic WAF (`waf`) is deprecated.

| Feature | WAF Classic (deprecated) | WAF v2 (current) |
|---------|-------------------------|------------------|
| Scope | Regional only | Regional + CloudFront |
| Rule capacity | Fixed 1,500 WCU | 1,500–50,000 WCU |
| Rule groups | Limited | AWS Managed + Custom |
| Rate-based rules | Basic | Advanced (IP, cookie, header) |
| Logging | CloudWatch Logs only | CloudWatch + S3 + Firehose |

## Variable Convention

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Use default; allow override |
| `{{user.web_acl_name}}` | User input | Ask once; reuse |
| `{{user.scope}}` | User input | REGIONAL or CLOUDFRONT |
| `{{user.resource_arn}}` | User input | ALB/CloudFront/API GW ARN |
| `{{output.web_acl_arn}}` | API response | Parse: `.Summary.ARN` or `.WebACL.ARN` |
| `{{output.web_acl_id}}` | API response | Parse: `.Summary.Id` or `.WebACL.Id` |

***

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**:

1. **Pre-flight**: `aws --version` + `aws sts get-caller-identity --output json`; verify WCU quota via `check-capacity`; CLOUDFRONT scope requires `us-east-1`
2. **Execute**: CLI primary (`--output json`); boto3 fallback after 3 CLI failures
3. **Validate**: `get-web-acl` / `list-web-acls` / `get-web-acl-for-resource` to confirm
4. **Recover**: See per-operation Recover table below

***

## Operations

### Operation: Create Web ACL

#### Pre-flight
```bash
aws --version && aws sts get-caller-identity --output json
```

| Check | Method | On Failure |
|-------|--------|------------|
| CLI available | `aws --version` | Install AWS CLI v2 |
| Credentials | `aws sts get-caller-identity` | HALT; log error |
| Scope | REGIONAL or CLOUDFRONT | CLOUDFRONT requires us-east-1 |
| WCU quota | `aws wafv2 check-capacity` | HALT; reduce rule count |

#### Execute — CLI
```bash
# Create Web ACL with AWS Managed Rules + rate-based rule
aws wafv2 create-web-acl \
  --name "{{user.web_acl_name}}" \
  --scope {{user.scope}} \
  --default-action Allow={} \
  --description "AIOps: WAF Web ACL for {{user.web_acl_name}}" \
  --rules '[
    {
      "Name": "AWS-AWSManagedRulesCommonRuleSet",
      "Priority": 0,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": {"None": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "AWSManagedRulesCommonRuleSet"
      }
    },
    {
      "Name": "RateBasedRule",
      "Priority": 1,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateBasedRule"
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName={{user.web_acl_name}} \
  --tags Key=AIOps,Value=true \
  --output json
```

#### Validate
```bash
aws wafv2 get-web-acl --name "{{user.web_acl_name}}" --scope {{user.scope}} --id {{output.web_acl_id}}
```

#### Recover
| Error | Action |
|-------|--------|
| WAFInternalErrorException | Retry 3x; HALT |
| WAFInvalidParameterException | Fix parameter; retry once |
| WAFLimitsExceededException | HALT; reduce WCU or request increase |
| WAFDuplicateItemException | Use different name |

***

### Operation: Secure Existing ALB with WAF (端到端流程)

这是最常见的场景：用户有一个已经在运行的 ALB，需要给它加上 WAF 保护。Agent 自动完成以下流程：

#### Step 1 — 发现 ALB

先列出用户的 ALB，让用户选择要保护的 LB：

```bash
# 列出所有 ALB
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?Type=='application'].{Name:LoadBalancerName,Arn:LoadBalancerArn,DNS:DNSName,Scheme:Scheme}" \
  --output table
```

```
输出示例：
|        Name        |          Arn          |         DNS         | Scheme |
|--------------------|-----------------------|---------------------|--------|
|  my-web-alb        |  arn:aws:...app/...   |  my-web-alb-xxx.elb | internet-facing |
|  internal-api-alb  |  arn:aws:...app/...   |  internal-api-xxx   | internal |
```

#### Step 2 — 创建 Web ACL

根据 ALB 类型（internet-facing / internal）自动选择合适的规则：

```bash
# Internet-facing ALB → AWS Managed Rules + IP Reputation + Rate Limit
# Internal ALB → AWS Managed Rules (basic) + Rate Limit

aws wafv2 create-web-acl \
  --name "{{user.web_acl_name}}" \
  --scope REGIONAL \
  --default-action Allow={} \
  --description "WAF protection for {{user.lb_name}}" \
  --rules '[
    {
      "Name": "AWS-AWSManagedRulesCommonRuleSet",
      "Priority": 0,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "OverrideAction": {"Count": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSet"
      }
    },
    {
      "Name": "RateLimit-2000",
      "Priority": 1,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit-2000"
      }
    }
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName={{user.web_acl_name}} \
  --tags Key=AIOps,Value=true Key=ProtectedLB,Value={{user.lb_name}} \
  --output json
```

**AIOps: Adaptive rule selection**

| ALB Type | Internet-Facing | Internal |
|----------|----------------|----------|
| AWS Managed Rules CommonRuleSet | ✅ Count mode (tune before block) | ✅ Count mode |
| AWS Managed Rules IP Reputation | ✅ Block | ❌ Skip (internal IPs) |
| Rate-Based Rule | ✅ Block (2000/min) | ✅ Block (10000/min) |
| AWS Managed Rules Bot Control | ✅ Recommend | ❌ Skip |

#### Step 3 — 关联到 ALB

```bash
aws wafv2 associate-web-acl \
  --web-acl-arn {{output.web_acl_arn}} \
  --resource-arn {{user.lb_arn}}
```

#### Step 4 — 验证

```bash
# 验证关联
aws wafv2 get-web-acl-for-resource --resource-arn {{user.lb_arn}}

# 验证规则已生效（检查 CloudWatch 指标）
aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=WebACL,Value={{user.web_acl_name}} Name=Rule,Value=All \
  --statistics Sum --period 300
```

#### 完整一键脚本

```bash
# 一键：选择 ALB → 创建 Web ACL → 关联 → 验证
LB_NAME="my-web-alb"
LB_ARN="arn:aws:elasticloadbalancing:region:account:loadbalancer/app/my-web-alb/xxx"
WAF_NAME="waf-${LB_NAME}"

# 创建 Web ACL
WAF_ID=$(aws wafv2 create-web-acl --name "$WAF_NAME" --scope REGIONAL \
  --default-action Allow={} \
  --rules '[
    {"Name":"CommonRuleSet","Priority":0,"Statement":{"ManagedRuleGroupStatement":{"VendorName":"AWS","Name":"AWSManagedRulesCommonRuleSet"}},"OverrideAction":{"Count":{}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"CommonRuleSet"}},
    {"Name":"RateLimit","Priority":1,"Statement":{"RateBasedStatement":{"Limit":2000,"AggregateKeyType":"IP"}},"Action":{"Block":{}},"VisibilityConfig":{"SampledRequestsEnabled":true,"CloudWatchMetricsEnabled":true,"MetricName":"RateLimit"}}
  ]' \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName="$WAF_NAME" \
  --query 'Summary.Id' --output text)

# 获取 ARN
WAF_ARN=$(aws wafv2 get-web-acl --name "$WAF_NAME" --scope REGIONAL --id "$WAF_ID" --query 'WebACL.ARN' --output text)

# 关联 ALB
aws wafv2 associate-web-acl --web-acl-arn "$WAF_ARN" --resource-arn "$LB_ARN"

# 验证
echo "✅ Web ACL $WAF_NAME created and associated with $LB_NAME"
echo "   ARN: $WAF_ARN"
```

Validate:
```bash
aws wafv2 get-web-acl-for-resource --resource-arn {{user.resource_arn}}
```

***

### Operation: Add Rate-Based Rule

```bash
aws wafv2 update-web-acl \
  --name "{{user.web_acl_name}}" \
  --scope {{user.scope}} \
  --id {{output.web_acl_id}} \
  --rules '[
    ...existing rules...,
    {
      "Name": "RateLimit-5000",
      "Priority": 10,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 5000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimit-5000"
      }
    }
  ]' \
  --visibility-config ... \
  --output json
```

***

### Operation: Enable WAF Logging

```bash
aws wafv2 put-logging-configuration \
  --logging-configuration '{
    "ResourceArn": "{{output.web_acl_arn}}",
    "LogDestinationConfigs": ["arn:aws:firehose:{{region}}:{{account}}:deliverystream/aws-waf-logs-{{user.web_acl_name}}"],
    "RedactedFields": [{"SingleHeader": {"Name": "authorization"}}]
  }'
```

***

### Operation: List Web ACLs

```bash
aws wafv2 list-web-acls --scope {{user.scope}}
```

***

### Operation: Delete Web ACL

**Safety Gate**: MUST obtain user confirmation. Must disassociate from all resources first.

```bash
# Step 1: Check associations
aws wafv2 get-web-acl --name {{user.web_acl_name}} --scope {{user.scope}} --id {{web_acl_id}}
# Check `.WebACL.AssociatedResources`

# Step 2: Disassociate
aws wafv2 disassociate-web-acl --resource-arn {{resource_arn}}

# Step 3: Delete
aws wafv2 delete-web-acl --name {{user.web_acl_name}} --scope {{user.scope}} --id {{web_acl_id}} --lock-token {{lock_token}}
```

***

## AIOps: DDoS Detection & Auto-Mitigation

### AH-08: Rate Limit Auto-Enable [AUTO_HEAL]

When ALB detects traffic anomaly (RequestCount > ANOMALY_DETECTION_BAND + 3σ):

```
Trigger: aws-elb-ops FD-06 traffic anomaly detected
┌──────────────────────────────────────────────────────────────────┐
│ Step 1 — Verify anomaly is not a legitimate spike                 │
│ Check source IP diversity (many unique IPs → DDoS-like)         │
│ aws wafv2 get-sampled-requests ...                              │
│                                                                   │
│ Step 2 — Apply rate-based rule threshold                         │
│ If baseline = 500 req/s → set rate limit at 2x = 1000 req/s    │
│ aws wafv2 update-web-acl ...                                    │
│                                                                   │
│ Step 3 — Enable AWS Managed Rules if not already active          │
│ Check if AWSManagedRulesCommonRuleSet is associated              │
│ If not → update Web ACL to add it                                │
│                                                                   │
│ Step 4 — Verify mitigation                                       │
│ Check CloudWatch `BlockedRequests` metric rises                  │
│ Check ALB RequestCount returns to normal                         │
│                                                                   │
│ Step 5 — Notify                                                  │
│ "DDoS mitigation auto-enabled: rate limit set to 1000 req/s"    │
└──────────────────────────────────────────────────────────────────┘
```

**Decision**: `[AUTO_HEAL]`
**Boundary**: Only if traffic spike + high source IP diversity + no prior false positive.

### AIOps: WAF Effectiveness Monitoring

| Metric | Namespace | AIOps Use |
|--------|-----------|-----------|
| `AllowedRequests` | AWS/WAFV2 | Legitimate traffic volume |
| `BlockedRequests` | AWS/WAFV2 | Attacked traffic volume |
| `CountedRequests` | AWS/WAFV2 | Rules in count mode (test) |
| `BlockedRequests` per Rule | AWS/WAFV2 | Per-rule effectiveness |

```bash
# WAF metrics for AIOps analysis
aws cloudwatch get-metric-statistics --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=Rule,Value=RateBasedRule Name=WebACL,Value={{web_acl_name}} \
  --statistics Sum --period 300
```

***

## Cross-Skill Orchestration

| Scenario | Chain |
|----------|-------|
| DDoS Mitigation (AH-08) | `aws-elb-ops` FD-06 → `aws-waf-ops` AH-08 → `aws-cloudwatch-ops` verify |
| ALB Security Hardening | `aws-elb-ops` create ALB → `aws-waf-ops` create+associate Web ACL |
| WAF Effectiveness Report | `aws-waf-ops` list rules → `aws-cloudwatch-ops` metrics → `aws-cloudtrail-ops` changes |

## Token Efficiency

All 6 TE rules applied (see `aws-skill-generator` SKILL.md §Token Efficiency Requirements). Key points:
- TE-1: No hardcoded WCU limits/rule capacity — use `check-capacity` / `list-web-acls`
- TE-2: Inline comments only in boto3 code (no docstrings)
- TE-3: Compact error tables throughout
- TE-4: JSON paths declared inline (no centralized block in this skill)
- TE-5: YAML anchors in `assets/example-config.yaml` where applicable
- TE-6: Flows only in SKILL.md (no duplicate in references/)

## Quality Gate (GCL)

> Phase 1 GCL rollout (2026-06-04, required). Every execution of
> `aws-waf-ops` MUST be wrapped by the Generator-Critic-Loop defined in
> `aws-skill-generator/references/gcl-spec.md`.

| Setting | Value |
|---|---|
| Class | `required` |
| `max_iterations` | `2` |
| Rubric | `references/rubric.md` (v1) |
| Prompts | `references/prompt-templates.md` (v1) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

Destructive ops requiring `{{user.safety_confirm}}` in trace:

- `delete-web-acl` — IRREVERSIBLE; MUST disassociate from all resources first (pre-flight `get-web-acl`); confirm `DELETE_WEB_ACL <name>`
- `delete-rule-group` — removes custom rule group; check Web ACLs using it
- `delete-ip-set` / `delete-regex-pattern-set` — removes IP/pattern set; confirm
- `update-web-acl` when adding blocking rules — treat as destructive; confirm with user

Relevant AWS rules from `gcl-spec.md` §8: A7 (region; CLOUDFRONT scope requires `us-east-1`), A8 (resource echoed from `get-*`/`list-*`), A9 (no secrets in rules / logging), A10 (sts first command).

### See also

- `aws-skill-generator/references/gcl-spec.md` — full GCL specification
- `references/rubric.md` — this skill's 5-dimension rubric
- `references/prompt-templates.md` — G/C/O skeletons
- Top-level `AGENTS.md` §11 — rollout index and Per-Skill Defaults

## Reference Files

- [Core Concepts](references/core-concepts.md)
- [AWS CLI Usage](references/aws-cli-usage.md)
- [boto3 SDK Usage](references/boto3-sdk-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Prompt Examples](references/prompt-examples.md)
- [Example Configurations](assets/example-config.yaml)

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

