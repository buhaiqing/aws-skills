# VPC Ops Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-vpc-ops`.

## Rubric version

`v1` — see `aws-skill-generator/references/gcl-spec.md` §11.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for `delete-vpc` / `delete-security-group` / `delete-subnet` / `delete-route-table` / `delete-internet-gateway` / `delete-nat-gateway` / `delete-vpc-endpoint` | 0 / 0.5 / 1 | Verifies resource id matches; read back via matching `describe-*` and confirm dependencies (rule A8). |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive VPC ops MUST have explicit user confirmation. `delete-vpc` and `delete-security-group` are particularly high-blast-radius (cross-resource references). |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-vpc` / `create-subnet` / `create-security-group` return `*AlreadyExists` on name collision; acceptable. `delete-*` is idempotent. |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain: full `aws ec2 <op>` command (VPC uses the ec2 namespace), args, exit code, raw response excerpt (≤ 2 KB), and dependency snapshot (rule A10 — sts first). |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | CIDR blocks are valid IPv4/IPv6 ranges; subnets are within VPC CIDR; route table / SG rules are well-formed JSON; VPC endpoints have valid service names. |

## Operation-specific overrides

| Operation | Required dimensions = 1.0 | Notes |
|---|---|---|
| `create-vpc` | Correctness, Spec Compliance | `CidrBlock` must be valid RFC1918 or non-overlapping public range |
| `create-subnet` | Correctness, Spec Compliance | Subnet CIDR must be within VPC CIDR; AZ specified |
| `create-security-group` | Correctness | Default outbound rule is `0.0.0.0/0:all`; capture for review |
| `authorize-security-group-ingress` / `egress` (widening to `0.0.0.0/0`) | Correctness, **Safety** | Public exposure; `confirm=AUTHORIZE_SG_PUBLIC <sg-id>` |
| `delete-security-group` (still referenced by ENI) | Correctness, Safety, **Traceability** | Pre-flight: `describe-network-interfaces --filters Name=group-id,Values=<sg-id>`; refuse if any ENI references it; **special: cannot delete default SG if any instance in VPC uses it** |
| `delete-security-group` (default SG) | Correctness, **Safety** | Refuse if any instance is in the VPC (default SG cannot be deleted while VPC has any instance) |
| `delete-subnet` (still has ENIs) | Correctness, **Safety** | Pre-flight: `describe-network-interfaces` filtered by subnet; refuse if any ENI; refuse if subnet has `MapPublicIpOnLaunch` and was the source of public IPs |
| `delete-route-table` (main route table) | Correctness, **Safety** | Refuse — main route table cannot be deleted, only replaced |
| `delete-route-table` (custom, in use) | Correctness, **Safety** | Pre-flight: `describe-route-tables` for associations; refuse if any subnet associates with it |
| `delete-internet-gateway` (attached) | Correctness, **Safety** | Pre-flight: must `detach-internet-gateway` first; refuse if still attached |
| `delete-nat-gateway` (in service) | Correctness, **Safety** | `confirm=DELETE_NAT_GATEWAY <id>`; pre-flight: `describe-nat-gateways` to confirm state; **EIP associated with deleted NAT is released (rule A7-relevant)** |
| `delete-vpc` (non-empty) | Correctness, Safety, **Traceability** | **HIGH BLAST RADIUS**; pre-flight: list subnets, IGWs, NATs, route tables (non-main), SGs, VPC endpoints, VPC peering, Network ACLs; refuse if ANY exist; user must run cleanup first; pre-flight MUST echo the dependency count |
| `delete-vpc` (empty) | Correctness, Safety | `confirm=DELETE_VPC <vpc-id>` |
| `delete-vpc-endpoint` (in use) | Correctness, **Safety** | Pre-flight: check route table associations; refuse if any |
| `delete-vpc-peering-connection` (active) | Correctness, **Safety** | `confirm=DELETE_VPC_PEERING <pcx-id>` |
| `associate-route-table` / `disassociate-route-table` (main) | Correctness, **Safety** | Main route table cannot be disassociated (use `replace-route-table-association`) |
| `modify-vpc-attribute` (enabling `EnableDnsSupport` / `EnableDnsHostnames`) | Correctness, **Safety** | Reversible but disrupts hostname resolution briefly |

## Safety special cases (auto-fail)

- `delete-vpc` called while any subnets, IGWs, NATs, route tables, SGs,
  VPC endpoints, or peering connections exist → **Correctness = 0 → ABORT**
  with a dependency list in the trace. The pre-flight MUST be a single
  comprehensive command and the count of remaining resources MUST appear.
- `delete-security-group` called while any ENI references it
  (`describe-network-interfaces` returns non-empty) →
  **Correctness = 0 → ABORT**.
- `delete-security-group` called on the **default SG** while any
  instance is in the VPC → **Correctness = 0 → ABORT** (AWS enforces
  this; rubric pre-checks).
- `delete-route-table` called on the **main route table** →
  **Correctness = 0 → ABORT** (it cannot be deleted; use
  `replace-route-table-association` instead).
- `delete-internet-gateway` called while still `attached` →
  **Correctness = 0 → ABORT**; require `detach-internet-gateway` first.
- `delete-nat-gateway` called while `State != "deleted"` →
  **Correctness = 0 → ABORT**.
- `delete-subnet` called while any ENI exists in the subnet →
  **Correctness = 0 → ABORT**.
- `authorize-security-group-ingress` adding `0.0.0.0/0` or `::/0` on
  port 22 / 3389 / 5432 / 3306 / 27017 / 6379 (SSH / RDP / common DB
  ports) without `confirm=AUTHORIZE_SG_PUBLIC <sg-id>` →
  **Safety = 0 → ABORT**.
- `delete-vpc` / `delete-security-group` / `delete-nat-gateway` on
  resources tagged `env=prod` (or `tier=production`) without
  `confirm=DELETE_PROD_VPC` / `confirm=DELETE_PROD_SG` /
  `confirm=DELETE_PROD_NAT` → **Safety = 0 → ABORT**.
- VPC resource id in the request not echoed from a `describe-*` lookup
  → **Correctness = 0 → ABORT** (rule A8).
- `--region` does not match `{{user.region}}` or
  `{{env.AWS_DEFAULT_REGION}}` → **Correctness = 0 → ABORT** (rule A7).
- `aws sts get-caller-identity` not run before any mutating op →
  **Traceability = 0 → ABORT** (rule A10).
- `CidrBlock` / CIDR authorization containing a malformed value →
  **Spec Compliance = 0 → ABORT**.

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 (Phase 1 default) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial rubric for `aws-vpc-ops` GCL rollout (Phase 1, required, not pilot) |
