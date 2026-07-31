---
name: aws-lambda-ops
description: >-
  Use when the user needs to create, deploy, configure, or manage AWS Lambda
  serverless functions; work with Lambda layers, versions, and aliases; set up
  event source mappings with SQS, SNS, DynamoDB, or Kinesis; configure function
  settings like memory, timeout, runtime, and environment variables; invoke
  functions synchronously or asynchronously; configure provisioned concurrency
  or dead-letter queues for error handling; or troubleshoot Lambda invocation
  errors, even if they don't say "Lambda" and instead say "deploy a serverless
  function", "set up an event-driven function", "configure a Lambda function",
  "manage function layers", or "create an event source mapping for AWS".
license: MIT
compatibility: >-
  AWS CLI v2, boto3 SDK (Python 3.10+), valid AWS credentials, network access
  to Lambda endpoints.
metadata:
  author: aws
  version: "1.2.0"
  last_updated: "2026-07-31"
  runtime: Harness AI Agent
  cli_applicability: dual-path
  gcl:
    enabled: true
    class: required
    max_iter: 2
    rubric_version: v1
    rubric_ref: references/rubric.md
    prompts_ref: references/prompt-templates.md
    pilot: false
  destructive_ops_require_confirm: true
  environment:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_DEFAULT_REGION
    - AWS_SESSION_TOKEN
  orchestrator_aware: true
  orchestrator_compat: ">=0.10"
  delegate:
    accepts: ['health-check', 'rca', 'self-heal', 'capacity-forecast']
    produces_facts: ['metric', 'state']
    idempotency_ttl: "PT24H"
    destructive_ops_require_confirm: true

---

# AWS Lambda Operations Skill

Use for Lambda functions, versions, aliases, layers, URLs, permissions, event-source mappings, concurrency, configuration, deployment, and invocation. Detailed commands remain in references.

## Common JSON Paths

Function: .{FunctionName,FunctionArn,Runtime,Role,Handler,State,LastUpdateStatus,Version}
EventSource: .{UUID,State,FunctionArn,EventSourceArn}
Invocation: .{StatusCode,FunctionError,ExecutedVersion}
Layer: .{LayerVersionArn,Version,CompatibleRuntimes}

## Trigger & Scope

### SHOULD Use When
Lambda functions, serverless execution, versions/aliases/layers, event sources, URLs, permissions, concurrency, invocation, or deployment.

### SHOULD NOT Use When
API Gateway → `aws-apigateway-ops`; IAM role policy → `aws-iam-ops`; event bus → `aws-eventbridge-ops`; S3 resources → `aws-s3-ops`.

### Delegation
IAM → `aws-iam-ops`; API Gateway → `aws-apigateway-ops`; metrics → `aws-cloudwatch-ops`; VPC → `aws-vpc-ops`; secrets → `aws-secretsmanager-ops`.

## Variable Convention

| Placeholder | Source | Use |
|---|---|---|
| `{{env.AWS_*}}` | Runtime env | Never ask; fail closed if unset |
| `{{user.function_name}}`, `{{user.execution_role_arn}}` | User input | Function identity/role |
| `{{user.runtime}}`, `{{user.handler}}`, `{{user.s3_bucket}}`, `{{user.s3_key}}` | User input | Deployment configuration |
| `{{user.source_arn}}`, `{{user.payload}}` | User input | Trigger/invocation payload |
| `{{output.*}}` | API response | Reuse function, mapping, layer, version IDs |

## Execution Flow Pattern

Every operation follows **Pre-flight → Execute → Validate → Recover**. Run `aws --version` and `aws sts get-caller-identity --output json`; verify role, package/S3 object, runtime availability, function state, triggers, permissions, and concurrency. Use CLI `--output json`, then boto3 after 3 CLI failures. Poll `State`/`LastUpdateStatus`; recover with bounded throttling retries and halt on missing resources or storage quota. See [aws-cli-usage.md](references/aws-cli-usage.md), [boto3-sdk-usage.md](references/boto3-sdk-usage.md), and [troubleshooting.md](references/troubleshooting.md).

## Operations and Safety

| Operation | Pre-flight / validation | Confirmation |
|---|---|---|
| Create/update code | Verify role, package, runtime; validate Active/Successful | Token for runtime/VPC/role changes |
| Invoke | Echo function/version; mask payload/output secrets | Token when invocation has side effects |
| Create/delete event mapping | Inspect source, mapping state, and blast radius | `confirm=DELETE_EVENT_SOURCE_MAPPING <uuid>` before deletion |
| Delete function | `get-function`; list mappings, aliases and URLs; refuse hidden trigger removal | `confirm=DELETE_FUNCTION <name>`; with mappings `confirm=DELETE_FUNCTION_WITH_TRIGGERS <name>` |
| Delete layer/config/permission | Describe dependency and callers | `confirm=DELETE_LAYER_VERSION <layer>:<version>` or operation-specific `confirm=` |
| Set concurrency to 0 | Explain function is effectively stopped | `confirm=SET_CONCURRENCY_ZERO <name>` |

Never include environment-variable values, literal secrets, function code, payload secrets, or credentials in traces; reference Secrets Manager/SSM ARNs instead.

## Quality Gate (GCL)

Required GCL, `max_iter=2`, rubric `references/rubric.md`, prompts `references/prompt-templates.md`; persist traces under `./audit-results/`. Apply A7–A10; Safety=0 aborts.

## Token Efficiency

TE-1…TE-6 apply; query live runtimes/limits, keep SDK examples comment-only, centralize JSON paths above, use asset anchors, and keep flows single-sourced.

## Reference Files

[aws-cli-usage.md](references/aws-cli-usage.md) · [boto3-sdk-usage.md](references/boto3-sdk-usage.md) · [core-concepts.md](references/core-concepts.md) · [troubleshooting.md](references/troubleshooting.md) · [integration.md](../aws-skill-generator/references/integration.md) · [rubric.md](references/rubric.md) · [prompt-templates.md](references/prompt-templates.md)

## AIOps Delegate Contract

Orchestrator-aware per [delegate-routing.md](../aws-aiops-orchestrator/references/delegate-routing.md): parse `aiops_delegate`; deduplicate writes by `idempotency_key` for 24h; require `confirmation_token` for destructive or side-effecting actions; `MANUAL` never writes, `AI_ASSIST` writes only with token, `AUTO_HEAL` permits non-destructive writes; propagate `trace_id` as `User-Agent: aiops-orchestrator/<trace_id>` and always emit `aiops_context` JSON. Runbooks: [runbook-recipes.md](../aws-aiops-orchestrator/references/runbook-recipes.md).
