# ACM Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-acm-ops`.
> This file is the single source of truth for what the Critic scores against.
>
> GCL implementation. See top-level `AGENTS.md` §11 and
> `aws-skill-generator/references/gcl-spec.md` §10 for the rollout plan.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-certificate` | 0 / 0.5 / 1 | Verifies `CertificateArn` / `DomainName` matches user request (rule A8). Read back via `describe-certificate` and compare against `CertificateArn` or `DomainName`. |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops (`delete-certificate`) MUST have explicit user confirmation (`confirm=DELETE_CERT <arn>`) in trace. Pre-flight `describe-certificate` MUST check `InUseBy` array; if non-empty, warn about HTTPS breakage for those services and require acknowledgement. AWS rules A7, A8, A9, A10 apply. |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `request-certificate` may return existing cert for same `--domain-name` and `--validation-method` (partially idempotent). `delete-certificate` is NOT idempotent — calling again on already-deleted cert returns `ResourceNotFoundException`. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws acm <op>` command with args, exit code, raw response excerpt (≤ 2 KB, no private key material), and final `describe-certificate` snapshot with `InUseBy`, `Status`, and `DomainValidationOptions`. `aws sts get-caller-identity` MUST be first (rule A10). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Conforms to `core-concepts.md`: `--domain-name` is valid FQDN (e.g. `*.example.com` for wildcard), `--validation-method` is `DNS` or `EMAIL`, `--subject-alternative-names` ≤ 10 (default quota), `--key-algorithm` valid (RSA_2048, EC_prime256v1). |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `request-certificate` | Correctness, **Spec Compliance** | Domain must be valid FQDN; DNS validation recommended |
| `delete-certificate` | Correctness, Safety, **Traceability** | MUST check `InUseBy` first; confirm with user; breakage warning |
| `describe-certificate` | Correctness | Read-only; capture Status, InUseBy, NotAfter |
| `list-certificates` | Correctness | Read-only; filter by `--certificate-statuses` |
| `renew-certificate` | Correctness | Only for imported certs; DNS-validated auto-renew |

## Safety special cases (auto-fail)

- `delete-certificate` **without** explicit `confirm=DELETE_CERT <arn>` in trace → **Safety = 0 → ABORT**
- `delete-certificate` when `InUseBy` is non-empty **without** user acknowledging HTTPS breakage → **Safety = 0 → ABORT**
- `CertificateArn` not echoed from `describe-certificate` / `list-certificates` → **Correctness = 0 → ABORT** (rule A8)
- `--region` mismatch → **Correctness = 0 → ABORT** (rule A7)
- Secrets/credentials in `--domain-name`, `--subject-alternative-names`, or `--certificate-arn` in trace → **Safety = 0 → ABORT** (rule A9)
- `aws sts get-caller-identity` not first → **Traceability = 0 → ABORT** (rule A10)

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-acm-ops` GCL |