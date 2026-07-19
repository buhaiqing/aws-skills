# Security Copilot Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `aws-skill-generator/references/gcl-spec.md` §3 for `aws-security-copilot`.

## Rubric version

`v1`

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Correctness** | hard | ≥ 0.5 | 0 / 0.5 / 1 | All 7 delegate targets exist; findings routed to correct skill per `playbook-routes.md` |
| 2 | **Safety** | hard | **= 1** | 0 / 1 | CRITICAL findings → HALT before remediation; no auto-remediate without user confirm |
| 3 | **Idempotency** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Same request → same posture summary |
| 4 | **Traceability** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Trace MUST contain `run_id`, all delegated skill calls, and merged findings |
| 5 | **Spec Compliance** | soft | ≥ 0.5 | 0 / 0.5 / 1 | Layering contract + Charter C7; output conforms to `incident-schema.md` |

## Hard termination rule

Per `gcl-spec.md` §3: if `Safety = 0`, the GCL loop MUST **ABORT** immediately.
A CRITICAL finding without an explicit HALT annotation is a **Safety = 0**.

## Critical-finding HALT check

| Check | Auto-fail condition |
|---|---|
| CRITICAL finding present | No `HALT` marker + no `notify_user()` call → **Safety = 0 → ABORT** |
| CRITICAL finding remediation | Any auto-remediation call before user confirm → **Safety = 0 → ABORT** |
| Confirmation pattern | CRITICAL without `confirm=HALT <finding-id>` → **Safety = 0 → ABORT** |

## Delegation correctness check

| Check | Auto-fail condition |
|---|---|
| Delegate target exists | Any `delegate` dir missing from disk → **Correctness = 0 → ABORT** |
| Finding routed correctly | Wrong skill for finding type → **Correctness = 0** |
| 7 required delegates | GuardDuty / SecurityHub / Config / IAM / Secrets / KMS / CloudTrail any missing → **Correctness = 0** |

## Loop parameters

| Parameter | Value |
|---|---|
| `max_iterations` | **3** (from `metadata.gcl.max_iter` in SKILL.md frontmatter) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |
| Rubric version | `v1` |
