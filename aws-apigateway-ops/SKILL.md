---
name: aws-apigateway-ops
description: >-
  Use when operating AWS API Gateway resources via AWS CLI or boto3 SDK;
  user mentions API Gateway, REST API, HTTP API, API endpoint, or stage.
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to AWS endpoints.
metadata:
  author: aws
  version: "1.0.0"
  last_updated: "2026-07-06"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_SESSION_TOKEN
    - AWS_DEFAULT_REGION
    - AWS_PROFILE
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  cross_skill_deps:
    - aws-iam-ops
    - aws-lambda-ops
    - aws-kms-ops
    - aws-vpc-ops            # VPC links and networking
    - aws-cloudwatch-ops     # API Gateway metrics and alarms
    - aws-cloudfront-ops     # CloudFront + API GW edge integration
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ["health-check", "rca"]
    produces_facts: ["state", "metric", "event"]
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true
---

# AWS API Gateway Operations Skill

Use for API Gateway REST/HTTP APIs, resources, methods, integrations, deployments, stages, usage plans, and lifecycle management. Detailed CLI/SDK commands remain in references.

## Common JSON Paths

CreateApi: .{id,name,endpointConfiguration}
RootResource: .items[?path==`/`].id
CreateResource: .{id,parentId,path,pathPart}
CreateDeployment: .{id,createdDate}
GetStage: .{deploymentId,stageName,cacheClusterStatus}

## Trigger & Scope

### SHOULD Use When
API Gateway, REST/HTTP APIs, endpoints, resources, methods, integrations, deployments, stages, or usage plans.

### SHOULD NOT Use When
Lambda CRUD → `aws-lambda-ops`; ALB entry → `aws-elb-ops`; CloudFront → `aws-cloudfront-ops`; custom-domain DNS → `aws-route53-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.api_id}}`, `{{user.api_name}}`, `{{user.stage_name}}` | User input | API/stage identity |
| `{{user.resource_path}}`, `{{user.lambda_arn}}` | User input | Resource/integration |
| `{{output.*}}` | API response | Reuse API, resource, root, deployment IDs |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify API uniqueness/identity, Lambda ARN and permission, resources, methods, stages, and deployment dependencies. Use CLI `--output json`, then boto3 after 3 CLI failures. Validate via get/read-back and endpoint invocation; recover with bounded throttling retries and halt on access, quota, or ambiguous identifiers. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create API | Check similar names and endpoint type; read back ID | — |
| Create resource/method | Verify parent/root, authorization, request settings | — |
| Put Lambda integration | Verify Lambda ARN, invoke permission, URI, response mapping | — |
| Deploy API | Verify methods/integrations; create deployment and validate stage | Production confirmation when replacing live deployment |
| Delete stage | Inspect deployment, cache, traffic, and custom domains | `DELETE_STAGE {{user.stage_name}}` |
| Delete API | List stages/resources/deployments and display blast radius | `DELETE_API {{user.api_id}}` |

Mask authorization headers, API keys, request bodies, and integration credentials in traces. Deletion is irreversible and must never infer confirmation from intent.

## Recover

`ConflictException` → update existing resource; `NotFoundException` → re-describe IDs; `LimitExceededException` → halt/request quota; `ThrottlingException` → bounded backoff; `AccessDeniedException` → halt and fix IAM.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live endpoint types/quotas, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive or production deployment actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
