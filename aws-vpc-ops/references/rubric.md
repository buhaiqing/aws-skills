# VPC Ops Rubric (GCL)

> Rubric for `aws-vpc-ops` per `gcl-spec.md` §3. Version v1.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|-----------|--------|-----------|-------|-------|
| 1 | **Correctness** | hard | ≥ 0.5; **= 1.0 required** for all destructive ops | 0 / 0.5 / 1 | Resource id matches `describe-*` lookup; dependencies confirmed (rule A8) |
| 2 | **Safety** | hard | = 1 | 0 / 1 | Destructive ops require confirmation. High blast radius for `delete-vpc`, `delete-security-group` |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `create-*` returns `*AlreadyExists` on collision; `delete-*` is idempotent |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Full command, args, exit code, response excerpt (≤2 KB), dependency snapshot; sts first (A10) |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Valid CIDRs; subnet within VPC; well-formed route/SG rules; valid endpoint service names |

## Operation-specific Overrides

| Operation | Required = 1.0 | Notes |
|-----------|----------------|-------|
| `create-vpc` | Correctness, Spec Compliance | `CidrBlock` must be valid RFC1918 or non-overlapping public range |
| `create-subnet` | Correctness, Spec Compliance | Subnet CIDR within VPC CIDR; AZ specified |
| `create-security-group` | Correctness | Default outbound `0.0.0.0/0:all`; capture for review |
| `authorize-*-ingress/egress` (widening to `0.0.0.0/0`) | Correctness, **Safety** | `confirm=AUTHORIZE_SG_PUBLIC <sg-id>` |
| `delete-security-group` (ENI-ref'd) | Correctness, Safety, **Traceability** | Pre-flight `describe-network-interfaces`; refuse if any ENI |
| `delete-security-group` (default SG) | Correctness, **Safety** | Refuse if any instance in VPC |
| `delete-subnet` (has ENIs) | Correctness, **Safety** | Pre-flight ENI check; refuse if any |
| `delete-route-table` (main) | Correctness, **Safety** | Refuse — main RT cannot be deleted |
| `delete-route-table` (custom, in use) | Correctness, **Safety** | Pre-flight associations; refuse if any subnet associated |
| `delete-internet-gateway` (attached) | Correctness, **Safety** | Must detach first |
| `delete-nat-gateway` (in service) | Correctness, **Safety** | `confirm=DELETE_NAT_GATEWAY <id>`; pre-flight state check; EIP released |
| `delete-vpc` (non-empty) | Correctness, Safety, **Traceability** | **HIGH BLAST RADIUS**; 8 describe-\* pre-flight (subnets/IGWs/NATs/RTs/SGs/endpoints/peering/NACLs); refuse if any non-empty (rule A13) |
| `delete-vpc` (empty) | Correctness, Safety | `confirm=DELETE_VPC <vpc-id>` |
| `delete-vpc-endpoint` (in use) | Correctness, **Safety** | Pre-flight route table check |
| `delete-vpc-peering-connection` (active) | Correctness, **Safety** | `confirm=DELETE_VPC_PEERING <pcx-id>` |
| `associate/disassociate-route-table` (main) | Correctness, **Safety** | Main RT cannot be disassociated (use `replace-route-table-association`) |
| `modify-vpc-attribute` (DNS) | Correctness, **Safety** | Reversible but disrupts hostname resolution briefly |

## Safety Special Cases (auto-fail)

- `delete-vpc` while deps exist → **Correctness=0 → ABORT**
- `delete-security-group` while ENI references it → **Correctness=0 → ABORT**
- `delete-security-group` (default SG) while instances in VPC → **Correctness=0 → ABORT**
- `delete-route-table` (main RT) → **Correctness=0 → ABORT**
- `delete-internet-gateway` while attached → **Correctness=0 → ABORT**
- `delete-nat-gateway` while `State != "deleted"` → **Correctness=0 → ABORT**
- `delete-subnet` while ENI exists → **Correctness=0 → ABORT**
- `authorize-security-group-ingress` adding `0.0.0.0/0` on sensitive ports without confirm → **Safety=0 → ABORT**
- `delete-vpc`/`delete-security-group`/`delete-nat-gateway` on prod-tagged without `confirm=DELETE_PROD_*` → **Safety=0 → ABORT**
- Resource id not from `describe-*` lookup → **Correctness=0 → ABORT** (A8)
- `--region` mismatch → **Correctness=0 → ABORT** (A7)
- `sts get-caller-identity` not first → **Traceability=0 → ABORT** (A10)
- Malformed `CidrBlock` → **Spec Compliance=0 → ABORT**

## Repo-wide AWS rules compliance

This rubric incorporates the following rules from `gcl-spec.md` §8 by reference:

- **A7** — `--region` must match `{{output.requested_region}}`.
- **A8** — Resource id (vpc-id, subnet-id, sg-id, rt-id, eni-id) echoed back
  from a `describe-*` lookup.
- **A9** — VPC ops are mostly metadata, but `run-instances --user-data`,
  `--iam-instance-profile`, and any `authorize-security-group-ingress` with
  embedded credentials MUST mask those values in the trace (rule A9).
  Plaintext `PasswordData` / `KeyMaterial` / `UserData` → **Safety = 0 → ABORT**.
- **A10** — `aws sts get-caller-identity` is the first trace command.

## Loop Parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **2** | `gcl-spec.md` §10 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | `gcl-spec.md` §6 |
| Rubric version | `v1` | this file |