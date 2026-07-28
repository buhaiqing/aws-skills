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
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'change-impact']
    produces_facts: ['metric', 'log', 'event', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Elastic Load Balancing Operations Skill

Use for ALB, NLB, legacy CLB, listeners, rules, target groups, health checks, traffic anomalies, latency/errors, draining, cost, and AIOps remediation. Prefer ALB/NLB for new workloads; detailed commands remain in references.

## Common JSON Paths

LoadBalancers: .LoadBalancers[].{LoadBalancerArn,LoadBalancerName,DNSName,Type,State,VpcId}
LoadBalancer: .LoadBalancers[0].{LoadBalancerArn,LoadBalancerName,DNSName,Type,State,VpcId}
TargetGroups: .TargetGroups[].{TargetGroupArn,TargetGroupName,Protocol,Port,TargetType}
TargetHealth: .TargetHealthDescriptions[].{Target,TargetHealth}
Listeners: .Listeners[].{ListenerArn,Port,Protocol,DefaultActions}
Rules: .Rules[].{RuleArn,Priority,Conditions,Actions,IsDefault}
Classic: .LoadBalancerDescriptions[].{LoadBalancerName,DNSName,Instances,HealthCheck}

## Trigger & Scope

### SHOULD Use When
ALB/NLB/CLB, listeners, rules, target groups, health checks, 502/503/504, unhealthy targets, latency, draining, or load-balancer cost/capacity.

### SHOULD NOT Use When
CloudFront → `aws-cloudfront-ops`; API Gateway → `aws-apigateway-ops`; EC2 lifecycle → `aws-ec2-ops`; DNS → `aws-route53-ops`; VPC/SG → `aws-vpc-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.lb_name}}`, `{{user.lb_type}}`, `{{user.vpc_id}}` | User input | Load balancer identity/type/network |
| `{{user.target_group_arn}}`, `{{user.target_ids}}` | User input | Traffic targets |
| `{{output.*}}` | API response | Reuse LB/listener/rule/TG ARNs |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**; AIOps adds Collect → Detect → RCA → Decide → Act → Feedback. Run `aws --version` and `aws sts get-caller-identity --output json`; verify VPC, subnets, SGs, certificates, quotas, listeners, rules, target health, and traffic impact. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll LB state and target health; recover with bounded retries and halt on invalid network, quota, or ambiguous identity. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/modify LB/listener/TG | Verify network, certs, ports, health checks; validate active | Token for production traffic changes |
| Deregister targets | Count healthy/registered targets and drain impact | `<50%`: `DEREGISTER`; `≥50%`: `DEREGISTER_DRAIN`; `100%`: `DEREGISTER_ALL` |
| Delete ALB/NLB | Verify no listeners and inspect DNS/targets/protection | `DELETE_LB` |
| Delete CLB | Warn legacy and registered instances; validate not found | `DELETE_CLB {{user.lb_name}}` |
| Delete rule | Refuse deletion when `IsDefault=true`; inspect traffic route | Human confirmation |
| Disable deletion protection | Show subsequent deletion risk | `DISABLE_DELETION_PROTECTION` |

Never mutate traffic from health signals alone without decision-tier authorization. Mask auth headers, certificates, tokens, and sensitive request data in traces.

## Quality Gate (GCL)

Recommended GCL, `max_iter=3`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10 and A12 target-drain thresholds; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live quotas/state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[core-concepts.md](references/core-concepts.md) · [aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [troubleshooting.md](references/troubleshooting.md) · [prompt-examples.md](references/prompt-examples.md) · [integration.md](references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for traffic-changing/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
