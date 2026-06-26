# Config Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-config-ops`. This
> file is the single source of truth for what the Critic scores against.
>
> GCL recommended skill (max_iter=3). See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-*` operations | 0 / 0.5 / 1 | Verifies config rule name, recorder name, delivery channel name, conformance pack name, aggregator name, and region match the user request. Read back via `describe-*` operations and compare (rule A8). Resource ARNs must be echoed from a prior `describe-*` lookup. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-config-rule`, `delete-configuration-recorder`, `delete-delivery-channel`, `delete-conformance-pack`, `delete-configuration-aggregator`, `delete-organization-config-rule`, `stop-configuration-recorder`) MUST have explicit user confirmation captured in trace. AWS-specific rules A7, A8, A9, A10 in `gcl-spec.md` §8 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `put-*` operations (`put-config-rule`, `put-configuration-recorder`, `put-delivery-channel`, `put-conformance-pack`, `put-configuration-aggregator`) are idempotent at the API level (upsert semantics). `delete-*` operations return success on re-delete of non-existent resources. Score 0 if a create-style operation lacks idempotency markers where applicable. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws configservice` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-*` snapshot of the affected resource(s). `aws sts get-caller-identity` MUST be the first command in the trace (rule A10). Score 1 only if all elements are present. |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: region supports AWS Config, service-linked role `AWSServiceRoleForConfig` exists for recorder operations, S3 bucket for delivery channel exists and has correct policy, SNS topic ARN is valid, IAM permissions for `config:*` actions are allowed (per rule A10), rule identifiers are valid AWS managed rule names or valid Lambda ARNs for custom rules. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `put-configuration-recorder` (Create/Update) | Correctness, **Spec Compliance** | Must verify service-linked role exists; role ARN must be valid; recording group must be well-formed |
| `put-delivery-channel` (Create/Update) | Correctness, **Spec Compliance** | Pre-flight MUST verify S3 bucket exists via `aws s3api head-bucket`; S3 bucket policy must allow Config service |
| `start-configuration-recorder` | Correctness | Delivery channel must exist first; recorder must exist |
| `stop-configuration-recorder` | Correctness, **Safety** | Pauses ALL compliance evaluations; requires `confirm=STOP_RECORDER <name>` |
| `delete-configuration-recorder` | Correctness, Safety, **Traceability** | MUST stop recorder first via `describe-configuration-recorder-status`; `confirm=DELETE_RECORDER <name>` required |
| `delete-delivery-channel` | Correctness, Safety | `confirm=DELETE_CHANNEL <name>` required; will stop configuration recording if no channel exists |
| `put-config-rule` (Managed Rule) | Correctness, Spec Compliance | SourceIdentifier must be valid AWS managed rule name; Scope resource types must be valid |
| `put-config-rule` (Custom Rule) | Correctness, Spec Compliance, **Safety** | SourceDetails Lambda ARN must exist; verify Lambda has `config:Put*` permissions |
| `delete-config-rule` | Correctness, Safety | `confirm=DELETE_RULE <name>` required; verify rule exists via `describe-config-rules` |
| `start-config-rules-evaluation` | Correctness | Rule must be in ACTIVE state; verify via `describe-config-rule-evaluation-status` |
| `deploy-conformance-pack` | Correctness, Spec Compliance | Template URI must be accessible S3 URI or valid YAML/JSON body; pack name must be unique |
| `delete-conformance-pack` | Correctness, Safety | `confirm=DELETE_PACK <name>` required; deletes all pack rules and evaluations |
| `put-configuration-aggregator` (Create/Update) | Correctness, Spec Compliance | Account IDs must be valid 12-digit AWS account IDs; Organization source requires Organizations trusted access |
| `delete-configuration-aggregator` | Correctness, Safety | `confirm=DELETE_AGGREGATOR <name>` required; removes multi-account aggregation |
| `deploy-organization-config-rule` | Correctness, Spec Compliance | Requires Organizations master account; rule parameters must be valid JSON |
| `delete-organization-config-rule` | Correctness, Safety | `confirm=DELETE_ORG_RULE <name>` required; affects all member accounts |
| `put-retention-configuration` | Correctness, **Safety** | RetentionPeriodInDays < 2557 (7 years) should confirm; affects compliance history deletion |
| `delete-retention-configuration` | Correctness, Safety | `confirm=DELETE_RETENTION` required; reverts to default 7 years |
| `delete-aggregation-authorization` | Correctness, Safety | `confirm=DELETE_AUTH <authorized-account>` required; breaks cross-account aggregation |

## Config-specific Safety special cases (auto-fail)

- `delete-configuration-recorder` while recorder status is `recording=true` **without**
  first stopping via `stop-configuration-recorder` → **Safety = 0 → ABORT**
- `delete-configuration-recorder` **without** explicit `confirm=DELETE_RECORDER <recorder-name>`
  in the trace → **Safety = 0 → ABORT**
- `delete-delivery-channel` **without** explicit `confirm=DELETE_CHANNEL <channel-name>`
  in the trace → **Safety = 0 → ABORT**
- `delete-delivery-channel` when it is the **only** delivery channel and recorder is
  active → **Safety = 0 → ABORT** (breaks all Config delivery)
- `stop-configuration-recorder` **without** explicit `confirm=STOP_RECORDER <recorder-name>`
  in the trace → **Safety = 0 → ABORT**
- `delete-config-rule` on a rule that is part of an active **Conformance Pack**
  **without** deleting the pack first → **Correctness = 0 → ABORT**
- `delete-config-rule` **without** explicit `confirm=DELETE_RULE <rule-name>` in the trace
  → **Safety = 0 → ABORT**
- `delete-conformance-pack` **without** explicit `confirm=DELETE_PACK <pack-name>` in the trace
  → **Safety = 0 → ABORT**
- `delete-configuration-aggregator` **without** explicit `confirm=DELETE_AGGREGATOR <name>`
  in the trace → **Safety = 0 → ABORT**
- `delete-organization-config-rule` **without** explicit `confirm=DELETE_ORG_RULE <name>`
  in the trace → **Safety = 0 → ABORT**
- `delete-aggregation-authorization` **without** explicit `confirm=DELETE_AUTH <account-id>`
  in the trace → **Safety = 0 → ABORT**
- `put-delivery-channel` pointing to an **non-existent S3 bucket** without prior
  verification → **Correctness = 0 → ABORT**
- `put-configuration-recorder` with an **invalid or non-existent role ARN**
  without prior IAM verification → **Correctness = 0 → ABORT**
- `put-config-rule` (custom) with a **non-existent Lambda function ARN**
  without prior verification → **Correctness = 0 → ABORT**
- `put-retention-configuration` with `RetentionPeriodInDays < 30`
  **without** explicit `confirm=SHORT_RETENTION <days>` → **Safety = 0 → ABORT**
- Any operation whose resource name was not echoed back from a
  `describe-*` lookup → **Correctness = 0 → ABORT** (rule A8)
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` →
  **Correctness = 0 → ABORT** (rule A7)
- S3 bucket name, SNS topic ARN, or Lambda function ARN containing credentials
  appears in the trace unmasked → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10)

## Reference to AWS Rules A1–A10

This rubric enforces the following rules from `aws-skill-generator/references/gcl-spec.md` §8:

| Rule | Applicability to Config Ops |
|---|---|
| **A1** | `terminate-instances` equivalent not applicable; destructive Config ops use explicit `confirm=` patterns |
| **A2** | Versioned bucket handling not directly applicable; see `aws-s3-ops` rubric for delivery channel S3 bucket concerns |
| **A3** | IAM policy attachment checks: `delete-config-rule` on custom rules should verify Lambda permissions are not orphaned |
| **A4** | KMS key deletion window not directly applicable to Config; retention configuration has its own guards |
| **A5** | Final snapshot equivalent: `delete-configuration-recorder` and `delete-conformance-pack` should capture pre-delete state |
| **A6** | Empty array refusal: `put-config-rule` Scope with empty `ComplianceResourceTypes` must be rejected |
| **A7** | Region match: All `--region` flags must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` |
| **A8** | Resource echo-back: All resource names (recorder, channel, rule, pack, aggregator) must be echoed from `describe-*` lookups |
| **A9** | Secret masking: Any S3 credentials, SNS topic ARNs with embedded keys, or Lambda function environment variables must be masked as `***<len>` |
| **A10** | Identity provenance: `aws sts get-caller-identity` MUST be the first command in every trace |

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | `gcl-spec.md` §10 (recommended class default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Expanded rubric to match aws-ec2-ops/aws-s3-ops depth: added detailed dimension descriptions, comprehensive operation-specific overrides for all Config operations, Config-specific Safety special cases, and A1–A10 rule references |
