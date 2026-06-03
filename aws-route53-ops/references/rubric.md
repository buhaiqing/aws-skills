# Route 53 Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-route53-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-hosted-zone` | 0 / 0.5 / 1 | Verifies hosted zone id, record name + type. Read back via `get-hosted-zone` / `list-resource-record-sets` (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-hosted-zone`, `delete-health-check`, `delete-reusable-delegation-set`, `change-resource-record-sets: DELETE`) MUST have explicit user confirmation. **DNS cuts are global and immediately visible.** |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `change-resource-record-sets` is **NOT** idempotent — same `DELETE` action applied twice returns success the first time, `InvalidChangeBatch` the second (because the record is already gone). UPSERT is idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws route53 <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and the `ChangeInfo.Status` polling (PENDING → INSYNC). `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Record name is fully-qualified (trailing dot); TTL ≥ 0; alias target is valid (ALB / CloudFront / S3 website / VPC endpoint / another record); health check protocol is one of `HTTP` / `HTTPS` / `HTTP_STR_MATCH` / `HTTPS_STR_MATCH` / `TCP` / `CALCULATED`. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-hosted-zone` | Correctness, Spec Compliance | CallerReference must be unique per call (idempotency key) |
| `change-resource-record-sets: CREATE` (single record) | Correctness, Spec Compliance | Routine |
| `change-resource-record-sets: UPSERT` | Correctness | Idempotent |
| `change-resource-record-sets: DELETE` | Correctness, **Safety** | **DNS cut**; `confirm=DELETE_RECORD <zone>:<name>:<type>`; pre-flight: list the record's current value so the user knows what they're deleting |
| `change-resource-record-sets` (multi-record, > 1) | Correctness, **Safety**, **Traceability** | Trace MUST include the full record batch; pre-flight: list each affected name + type |
| `delete-hosted-zone` (non-empty) | Correctness, Safety, **Traceability** | **GLOBAL DNS CUT**; pre-flight: `list-resource-record-sets` to enumerate all records; refuse if any non-default records exist (NS / SOA cannot be deleted but other records must be); `confirm=DELETE_HOSTED_ZONE <zone-id>` |
| `delete-hosted-zone` (empty, only NS/SOA) | Correctness, Safety | `confirm=DELETE_HOSTED_ZONE <zone-id>` |
| `delete-health-check` | Correctness, Safety | Pre-flight: `list-health-checks` filtered by `HealthCheckId`; verify no CloudWatch alarm uses it (would silently fail); `confirm=DELETE_HEALTH_CHECK <id>` |
| `delete-reusable-delegation-set` | Correctness, Safety | Pre-flight: no hosted zone references it |
| `create-health-check` (with `IPAddress` matching 169.254.169.254) | Correctness, **Safety** | Link-local health check; rare but valid (IMDS reachability); routine |
| `associate-vpc-with-hosted-zone` / `disassociate-vpc-with-hosted-zone` | Correctness, **Safety** | Affects private zone resolution; pre-flight confirm |
| `update-hosted-zone-comment` | Correctness | Routine |
| `tag-resource` / `untag-resource` | Correctness | Routine |

## Safety special cases (auto-fail)

- `delete-hosted-zone` called while `list-resource-record-sets` returns
  any record other than the apex `NS` and `SOA` → **Correctness = 0 → ABORT**
  with the list of records that must be deleted first.
- `change-resource-record-sets: DELETE` without
  `confirm=DELETE_RECORD <zone>:<name>:<type>` → **Safety = 0 → ABORT**.
- `change-resource-record-sets` applied to a record that resolves to a
  resource currently serving prod traffic (e.g. ALB with non-zero
  `RequestCount` in last 5 min) without
  `confirm=DELETE_PROD_DNS_RECORD <name>` → **Safety = 0 → ABORT**.
- `delete-health-check` called while any CloudWatch alarm references
  the health check → **Correctness = 0 → ABORT** (the alarm would
  silently fail to evaluate).
- `delete-reusable-delegation-set` called while any hosted zone
  references it → **Correctness = 0 → ABORT**.
- `disassociate-vpc-with-hosted-zone` while any resource record in
  the zone is referenced by services in that VPC → **Correctness = 0 → ABORT**.
- Hosted zone id / record name in the request not echoed from a
  `get-hosted-zone` / `list-resource-record-sets` lookup →
  **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` (Route 53 is global; the
  only legitimate region is `us-east-1`) → **Correctness = 0 → ABORT**
  (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- Record value (e.g. ALB DNS name) appears un-masked in the trace;
  Route 53 records are not secrets but full value disclosure makes
  post-mortem confusing — mask to `***<len>` only when
  `confirm=MASK_DNS_VALUES` is set (otherwise full value is fine).
- CallerReference missing on `create-hosted-zone` → **Idempotency = 0 → ABORT**
  (required for retry safety).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-route53-ops` GCL rollout (Phase 1, required, not pilot) |
