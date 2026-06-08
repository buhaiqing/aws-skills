# OpenSearch Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-opensearch-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-domain` / `delete-ingestion` | 0 / 0.5 / 1 | Verifies `DomainName` / `PipelineName` / `VpcEndpointId` match the user request. Read back via `describe-domain` / `describe-ingestion` / `describe-vpc-endpoints` and compare (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-domain`, `delete-snapshot`, `delete-vpc-endpoint`, `delete-ingestion`, `upgrade-domain`) MUST have explicit user confirmation in trace. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-domain` returns the same `DomainStatus` on re-run with `ResourceAlreadyExistsException`; acceptable terminal state. `delete-*` is idempotent at the API level. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws opensearch <op>` command, args, exit code, raw response excerpt (≤ 2 KB), and a final `describe-domain` snapshot. `aws sts get-caller-identity` MUST be the first command (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: engine version is supported in the region; instance type is valid; VPC options include ≥2 subnets for Multi-AZ; access policies are valid JSON. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-domain` | Correctness, Spec Compliance | `MasterUserPassword` MUST be masked in trace (rule A9) |
| `update-domain-config` | Correctness, **Safety** | Cluster config change causes blue/green deployment; brief performance impact |
| `upgrade-domain` | Correctness, **Safety** | Irreversible; pre-flight: `get-compatible-versions`; confirm target version |
| `delete-domain` | Correctness, Safety, **Traceability** | **Data loss is irreversible**; `confirm=DELETE_DOMAIN <domain-name>` in trace |
| `delete-snapshot` | Correctness, Safety | `confirm=DELETE_SNAPSHOT <snapshot-name> from <domain-name>` in trace |
| `delete-vpc-endpoint` | Correctness, Safety | `confirm=DELETE_VPC_ENDPOINT <vpc-endpoint-id>` in trace |
| `delete-ingestion` | Correctness, Safety | `confirm=DELETE_INGESTION <pipeline-name>` in trace; pre-flight: pipeline must not be `RUNNING` |
| `create-snapshot` | Correctness | Routine; pre-flight: no snapshot in progress |
| `create-vpc-endpoint` | Correctness, Spec Compliance | VPC must have valid subnets and SGs |
| `create-ingestion` | Correctness, Spec Compliance | Pipeline config must be valid YAML/JSON |

## Safety special cases (auto-fail)

- `delete-domain` called while domain `Processing=true` → **Correctness = 0 → ABORT** (must wait for `Active`).
- `delete-domain` on a domain tagged `env=prod` (or `environment=production`, `tier=production`) without `confirm=DELETE_PROD_DOMAIN <domain-name>` in trace → **Safety = 0 → ABORT**.
- `delete-ingestion` called while pipeline `Status=RUNNING` without `confirm=DELETE_RUNNING_INGESTION <pipeline-name>` → **Safety = 0 → ABORT**.
- `upgrade-domain` to a version not in `get-compatible-versions` → **Correctness = 0 → ABORT**.
- `create-domain` with `MasterUserPassword` as a literal string in trace → **Safety = 0 → ABORT** (rule A9). Mask to `***<len>` only.
- `DomainName` / `PipelineName` / `VpcEndpointId` in the request not echoed from a `describe-*` lookup → **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op → **Traceability = 0 → ABORT** (rule A10).

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default for destructive skills) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-08 | Initial rubric for `aws-opensearch-ops` GCL rollout (Phase 1, required, not pilot) |
