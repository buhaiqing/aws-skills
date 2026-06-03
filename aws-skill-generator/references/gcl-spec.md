# Generator-Critic-Loop (GCL) — Shared Specification

> Source of truth for the **GCL** adversarial quality gate applied to every
> skill execution in this repository. The high-level index and current rollout
> status live in the top-level `AGENTS.md` §11. This file is the deep spec.
>
> **Naming:** **GCL (Generator-Critic-Loop)** to avoid confusion with a real
> GAN. The Critic does **not** learn a sample distribution; it scores an
> explicit, hand-written rubric.

---

## 1. Purpose

Apply an adversarial **Generator ↔ Critic** loop with a quantitative rubric
to every skill execution. Most valuable in **high-side-effect AWS operations**
(`terminate-instances`, `delete-bucket`, `iam delete-user`, `kms
schedule-key-deletion`, RDS `delete-db-instance`, `deregister-task-definition`,
etc.) where a single mistake is unrecoverable.

| GAN (real) | GCL (this spec) |
|---|---|
| Discriminator learns sample distribution | Critic scores an **explicit rubric** |
| No termination condition | Must terminate: **PASS / MAX_ITER / SAFETY_FAIL** |
| G and D train in parallel | G and C run **sequentially** |
| Goal: "fool the D" | Goal: "pass the rubric threshold" |

## 2. Roles

| Role | Job | Input | Output | Forbidden |
|---|---|---|---|---|
| **Generator (G)** | Execute the AWS operation | user request + previous Critic feedback | result + execution trace | modifying the rubric; self-scoring |
| **Critic (C)** | Independently audit G's output | G's result + trace + rubric | scores + suggestions | calling `aws` / `boto3` / mutating anything |
| **Orchestrator (O)** | Loop control, termination, final return | context + C scores + budget | continue / final result | executing or scoring on its own |

**Hard constraint:** G and C MUST live in **isolated prompt contexts**
(preferably isolated sessions or sub-agents). A shared context is a
"pseudo-GCL" and is explicitly banned — see §9.

## 3. Rubric (mandatory per skill)

Each `SKILL.md` MUST declare its skill-specific rubric in
`references/rubric.md`. Minimum 5 dimensions:

| Dimension | Meaning | Scale | Default threshold |
|---|---|---|---|
| **Correctness** | Resource id / state / config actually matches the request | 0 / 0.5 / 1 | ≥ 0.5 (1.0 required for `terminate` / `delete` / IAM / KMS / DDL) |
| **Safety** | Destructive op (`delete` / `terminate` / `deregister` / `detach` / `revoke` / IAM / KMS / DDL) was confirmed or guarded | 0 / 1 | = 1 |
| **Idempotency** | Retrying the same call will not cause duplicate side-effects (e.g. `ClientToken` on `RunInstances`) | 0 / 0.5 / 1 | ≥ 0.5 |
| **Traceability** | Output is auditable: command, args, raw response, errors all captured | 0 / 0.5 / 1 | ≥ 0.5 |
| **Spec Compliance** | Conforms to the skill's `core-concepts.md` constraints (region, AZ, quota, IAM pre-reqs) | 0 / 0.5 / 1 | ≥ 0.5 |

**Safety = 0 → ABORT immediately, regardless of total score.**

## 4. Loop Flow

```
User Request
     │
     ▼
[0] Pre-flight (Orchestrator)
    - resolve env.* and user.* variables
    - load AWS credentials (env → ~/.aws/credentials → defaults; see CLAUDE.md)
    - pick skill, load its rubric
     │
     ▼
[1] Generate (G) ───────────────────────┐
    - run aws --output json <svc> <op>   │   (primary; boto3 fallback after 3 fails)
    - or boto3 client call              │
    - capture trace                     │
     │                                  │
     ▼                                  │
[2] Critique (C)                       │
    - isolated prompt context           │
    - score every rubric dimension      │
    - emit actionable suggestions       │
     │                                  │
     ▼                                  │
[3] Decide (Orchestrator)              │
    - Safety=0  → ABORT (no partial)   │
    - all pass  → RETURN                │
    - else & iter<max → inject         │
       suggestions into G               │
    - else → RETURN best + unresolved   │
       rubric items                     │
     └──────────────────────────────────┘
```

## 5. Termination (first match wins)

| Condition | Behavior |
|---|---|
| **PASS** | Every rubric dimension meets its threshold → return G's result |
| **MAX_ITER** | Reached `max_iterations` (default 2 for destructive) → return **best-so-far** + unresolved rubric items |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**; never return partial or "best-effort" output |

Per-skill `max_iter` defaults are enumerated in `AGENTS.md` §11.5 (Per-Skill
Defaults table). Any skill may override its own `max_iter` in its
`SKILL.md` under `## Quality Gate (GCL)`.

## 6. Trace & Audit (mandatory)

Every GCL run MUST persist a JSON trace to:

```
./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
```

Required schema (JSON object):

```json
{
  "skill": "aws-ec2-ops",
  "request": "<sanitized user request>",
  "rubric_version": "v1",
  "iterations": [
    {
      "iter": 1,
      "generator": {
        "command": "aws --output json ec2 terminate-instances --instance-ids i-... --no-dry-run",
        "args":    { "instance-ids": ["i-..."] },
        "exit_code": 0,
        "result_excerpt": "<≤ 2 KB raw response excerpt>"
      },
      "critic": {
        "scores": {
          "correctness": 1, "safety": 1, "idempotency": 0.5,
          "traceability": 1, "spec_compliance": 1
        },
        "suggestions": ["..."],
        "blocking": false
      },
      "decision": "RETRY"
    }
  ],
  "final": { "status": "PASS", "iter": 2, "output": "..." }
}
```

`audit-results/` is git-ignored. Trace retention is 30 days; older traces
should be pruned by the local Orchestrator runner (Phase 2 of the rollout
roadmap, `AGENTS.md` §11.10).

## 7. Prompt Templates (mandatory per skill)

Each skill's `references/prompt-templates.md` MUST contain:

1. **Generator Prompt Template** — placeholders: `{{user.request}}`,
   `{{output.critic_feedback}}`, `{{output.rubric}}`
2. **Critic Prompt Template** — placeholders: `{{output.generator_output}}`,
   `{{output.trace}}`, `{{output.rubric}}`
3. **Orchestrator Decider Prompt** — placeholders: `{{output.critic_scores}}`,
   `{{output.iter}}`, `{{output.rubric}}`

> **Placeholder syntax** MUST follow the repository-wide convention
> (see top-level `AGENTS.md` §Variable Convention): `{{env.*}}` / `{{user.*}}` /
> `{{output.*}}`. Bare `{...}` placeholders are NOT allowed in skill prompt
> templates.

**Critic prompt must hide the raw user request** to prevent "answer-aligned"
rubber-stamping. Recommended skeleton:

```text
You are an independent AWS-operation auditor.
You will see one execution result and its trace. Score it STRICTLY against the rubric below.
Do NOT consider the original user request — judge only what was actually done.

rubric: {{output.rubric}}
generator_output: {{output.generator_output}}
trace: {{output.trace}}

Return strict JSON:
{
  "scores": { "correctness": 0|0.5|1, "safety": 0|0.5|1, "idempotency": 0|0.5|1,
              "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1 },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false
}
```

## 8. AWS-specific rules (in addition to generic rubric)

These rules come up often enough to be standardised repo-wide. Each skill's
`rubric.md` SHOULD incorporate them by reference.

| # | Pattern | Auto-fail rule |
|---|---|---|
| A1 | `aws ec2 terminate-instances` without `--no-dry-run` confirmation | Correctness=0 unless trace shows user-supplied `--no-dry-run` opt-in |
| A2 | `aws s3 rm` / `aws s3api delete-bucket` on a bucket with `Versioning=Enabled` | Safety=0 unless explicit `--force` and `--no-dry-run` |
| A3 | `aws iam delete-user` / `aws iam detach-user-policy` while policies still attached | Correctness=0; must run `list-attached-user-policies` first |
| A4 | `aws kms schedule-key-deletion` with `--pending-window-in-days < 7` | Safety=0; AWS enforces min 7, rubric demands user confirm explicitly |
| A5 | `aws rds delete-db-instance` without `--final-db-snapshot-identifier` (prod tag) | Safety=0 unless final snapshot configured |
| A6 | `aws s3api delete-objects` with empty / wildcard `Objects` array | Correctness=0; refuse to run |
| A7 | Any operation whose `--region` does not match the user's `{{user.region}}` (or `AWS_DEFAULT_REGION`) | Correctness=0 |
| A8 | Resource id in the request was not echoed back from a `describe-*` lookup | Correctness=0 |
| A9 | Plaintext secret (`AWS_SECRET_ACCESS_KEY`, `SessionToken`, `DbPassword`) appears in trace | Safety=0; trace MUST mask with `***` and length only |
| A10 | `aws sts get-caller-identity` not run before any IAM/KMS mutating op | Traceability=0 (no identity provenance) |

## 9. Anti-Patterns (banned)

- ❌ **Shared context G+C** — defeats independence → banned
- ❌ **Subjective scoring** — Critic must use the rubric, not "vibes" → banned
- ❌ **Unbounded loop** — always hard-cap iterations → banned
- ❌ **Critic sees the user request** — encourages rubber-stamping → banned
- ❌ **Silently downgrade on Safety fail** — must ABORT visibly → banned
- ❌ **Trace not persisted** — no post-mortem possible → banned
- ❌ **Critic mutates resources** — Critic is read-only by definition → banned
- ❌ **AWS CLI `--output json` placed before subcommand** — non-portable; convention is `aws <svc> <op> --output json` (see CLAUDE.md) → banned in examples and traces

## 10. Rollout Roadmap

- **Phase 1 (this commit)** — add this spec + `AGENTS.md` §11; pilot on
  **`aws-ec2-ops`** (most representative destructive workload) with its
  `references/rubric.md` and `references/prompt-templates.md`.
  `aws-iam-ops` follows in the next PR.
- **Phase 2** — add `scripts/gcl_runner.py` as a reusable Orchestrator
  (invokes G, then C in isolated context, persists trace, enforces
  termination). Independent of any specific agent runtime.
- **Phase 3** — feed `gcl-trace-*.json` into a CloudWatch dashboard / Athena
  query for Quality Gate pass-rate and per-skill failure-mode histograms.
- **Phase 4** — wire rubric pass-rate to CloudWatch Alarms; production
  incidents refine thresholds.

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added (`aws-skill-generator/references/gcl-spec.md`) — pilot scoped to `aws-ec2-ops` |

## 12. See also

- `AGENTS.md` §11 — top-level index, Per-Skill Defaults table, current phase
- Each pilot skill's `references/rubric.md` — the rubric instance
- Each pilot skill's `references/prompt-templates.md` — the G/C/O prompt skeletons
- `CLAUDE.md` — shared baseline (dual-path execution, credential convention)
