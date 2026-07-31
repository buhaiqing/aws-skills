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
  last_updated: "2026-07-31"
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
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal']
    produces_facts: ['metric', 'log', 'config']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---
# AWS WAF Operations Skill

Use for WAFv2 web ACLs, rules, rule groups, IP/regex sets, logging, associations, rate limiting, and DDoS mitigation. Detailed CLI/SDK patterns remain in references.

## Common JSON Paths

WebACL: .WebACL.{Id,Name,ARN,LockToken,DefaultAction,Rules}
WebACLs: .WebACLs[].{Id,Name,ARN,Scope}
RuleGroups: .RuleGroups[].{Id,Name,ARN,Capacity,Rules}
IPSets: .IPSets[].{Id,Name,ARN,Addresses,IPAddressVersion}
RegexSets: .RegexPatternSets[].{Id,Name,ARN}

## Trigger & Scope

### SHOULD Use When
WAF web ACLs, rules, rule groups, IP/regex sets, logging, ALB/CloudFront/API Gateway associations, rate limits, or DDoS signals.

### SHOULD NOT Use When
CloudFront → `aws-cloudfront-ops`; ALB → `aws-elb-ops`; API Gateway → `aws-apigateway-ops`; IAM/KMS → respective skills.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.web_acl_name}}`, `{{user.web_acl_id}}`, `{{user.scope}}` | User input | ACL identity/scope |
| `{{user.rule_group_id}}`, `{{user.ip_set_id}}`, `{{user.lock_token}}` | User input/output | Resource/version controls |
| `{{output.*}}` | API response | Reuse ARN, lock token, rule/set IDs |

## Execution Flow

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify scope, associated resources, lock token, rule capacity, IP/regex set, logging destination, and production traffic. Use CLI `--output json`, then boto3 after 3 CLI failures. Read back ACL/rule association; recover with bounded retries and halt on lock mismatch, capacity, or ambiguous resource. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update ACL/rule | Validate lock token, capacity, default action and rule order | Token for production traffic changes |
| Rate limit auto-mitigation | Correlate WAF metrics and attack signals; cap scope/duration | AUTO_HEAL only within approved bounds |
| Delete web ACL | Disassociate from every resource first; fetch current lock token | `confirm=DELETE_WEB_ACL <name>` |
| Delete rule group | List ACL references and capacity consumers | `confirm=DELETE_RULE_GROUP <name>` |
| Delete IP/regex set | Inspect rule references and traffic impact | `confirm=DELETE_IP_SET <name>` |
| Disable logging/association | Show observability or protection impact | Human confirmation |

Mask request bodies, IP lists where sensitive, tokens, and logging credentials in traces.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live capacity/association state, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for traffic/destructive actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits bounded non-destructive rate mitigation; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).

