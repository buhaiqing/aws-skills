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
| A11 | `aws cloudfront delete-distribution` before `Status=Deployed` (Enabled) | Correctness=0; distribution MUST first be Disabled, then poll `get-distribution` until `Status=Deployed`, then delete |
| A12 | `aws elbv2 deregister-targets` dropping ≥50% of healthy targets without drain confirmation | Correctness=0 unless trace records `confirm=DRAIN_TARGETS <tg-arn> <from-count>→<to-count>`; default rule is undeletable |
| A13 | `aws ec2 delete-vpc` without 8-describe pre-flight (subnets/IGWs/NATs/RTs/SGs/endpoints/peering/NACLs) | Correctness=0; trace MUST contain all 8 describe-call results with `null`/empty markers for absent resources |
| A14 | `aws rds delete-db-instance` / `aws rds delete-db-cluster` with `--skip-final-snapshot` on a prod-tagged instance | Safety=0 unless trace contains literal `DELETE_NO_SNAPSHOT <db-id>` token; Aurora cluster delete is irreversible (no final-cluster-snapshot equivalent for Global DB) |
| A15 | `aws s3api put-bucket-policy` widening to `Principal: "*"` + `Effect: Allow` + `Action: "s3:*"` | Safety=0 unless trace contains literal `confirm=PUT_POLICY_PUBLIC <bucket>`; same rule for `put-bucket-acl` with public canned ACL |
| A16 | `aws autoscaling delete-auto-scaling-group` with `--force-delete` while `DesiredCapacity > 0` | Safety=0 unless `--desired-capacity 0` was applied first AND `InstanceProtection=false` on all instances; otherwise `--force-delete` is rejected by AWS with a noisy error that masks the real cause |

> **Reference convention:** every skill's `references/rubric.md` SHOULD
> reference applicable A-rules by id (e.g. "rule A11", "rule A14") rather
> than restating the rule in prose. This keeps rules centralized in
> `gcl-spec.md` §8 and lets the spec evolve without touching every skill.

## 9. Anti-Patterns (banned)

- ❌ **Shared context G+C** — defeats independence → banned
- ❌ **Subjective scoring** — Critic must use the rubric, not "vibes" → banned
- ❌ **Unbounded loop** — always hard-cap iterations → banned
- ❌ **Critic sees the user request** — encourages rubber-stamping → banned
- ❌ **Silently downgrade on Safety fail** — must ABORT visibly → banned
- ❌ **Trace not persisted** — no post-mortem possible → banned
- ❌ **Critic mutates resources** — Critic is read-only by definition → banned
- ❌ **AWS CLI `--output json` placed before subcommand** — non-portable; convention is `aws <svc> <op> --output json` (see CLAUDE.md) → banned in examples and traces
- ❌ **`{{user.*}}` placeholders in Critic templates** — the Critic must score the trace in isolation; any `{{user.*}}` reference inside a Critic prompt template (even inside a fenced code block) lets the Critic see the original request and rubber-stamp. If the Critic needs a value that originates from the user request, the Orchestrator MUST extract it from `{{user.*}}` and re-inject it as `{{output.*}}` before calling the Critic. The only `{{user.*}}` references allowed in a skill's `references/prompt-templates.md` are inside the **Generator** section and the **Variable Convention** documentation table. See the mapping in §7.1 below.

### 7.1 User→Output placeholder mapping (Critic isolation)

When the Critic template needs a value that semantically comes from the user
request, the skill's prompt-templates.md MUST route it through `{{output.*}}`,
populated by the Orchestrator from the trace or from `{{user.*}}`. Standard
mappings:

| Origin (Generator / Variable Convention) | Critic-side reference | Orchestrator behavior |
|---|---|---|
| `{{user.region}}` | `{{output.requested_region}}` | Copy `{{user.region}}` (or `{{env.AWS_DEFAULT_REGION}}` fallback) into `output.requested_region` before invoking Critic |
| `{{user.safety_confirm}}` | `{{output.safety_confirm_token}}` | Capture the literal `confirm=<OP> <id>` token from the trace into `output.safety_confirm_token`; if absent, set to empty string (Critic then scores Safety=0 per rule §3) |

Rationale: the Critic sees `{{output.*}}` as trace-derived state, not as the
user's stated intent. This preserves rule A7 (region check) and destructive-op
confirmation checks **without** letting the Critic pattern-match against the
original request. (Added in spec v1.11.0, 2026-06-27, see §11 changelog.)

## 10. Rollout Roadmap

- **Phase 1 (this commit)** — add this spec + `AGENTS.md` §11; pilot on
  **`aws-ec2-ops`** (most representative destructive workload) with its
  `references/rubric.md` and `references/prompt-templates.md`.
  `aws-iam-ops` follows in the next PR.
- **Phase 2** (shipped 2026-06-27) — `scripts/gcl_runner.py` exists as a reusable
  Orchestrator (invokes G, then C in isolated context, persists trace to
  `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`, enforces §5 termination).
  Independent of any specific agent runtime.
- **Phase 3** — feed `gcl-trace-*.json` into a CloudWatch dashboard / Athena
  query for Quality Gate pass-rate and per-skill failure-mode histograms.
- **Phase 4** — wire rubric pass-rate to CloudWatch Alarms; production
  incidents refine thresholds.

## 11. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added (`aws-skill-generator/references/gcl-spec.md`) — pilot scoped to `aws-ec2-ops` |
| 1.1.0 | 2026-06-04 | Second GCL pilot on `aws-iam-ops` (v1.1.0) |
| 1.2.0 | 2026-06-04 | Third GCL pilot on `aws-kms-ops` (v2.1.0) |
| 1.3.0 | 2026-06-04 | Fourth GCL pilot on `aws-s3-ops` (v1.1.0) |
| 1.4.0 | 2026-06-04 | Group 1 GCL rollout: `aws-rds-ops`, `aws-lambda-ops`, `aws-dynamodb-ops` |
| 1.5.0 | 2026-06-04 | Group 2 GCL rollout: `aws-vpc-ops`, `aws-route53-ops`, `aws-cloudfront-ops`, `aws-elb-ops` |
| 1.6.0 | 2026-06-04 | Group 3 GCL rollout: `aws-elasticache-ops`, `aws-waf-ops`, `aws-secretsmanager-ops`, `aws-ssm-ops`, `aws-acm-ops`, `aws-eks-ops`, `aws-sqs-ops`, `aws-sns-ops`, `aws-stepfunctions-ops`, `aws-cloudwatch-ops`, `aws-cloudtrail-ops` |
| 1.7.0 | 2026-06-07 | Group 4 GCL rollout: `aws-autoscaling-ops`, `aws-config-ops`, `aws-eventbridge-ops` |
| 1.8.0 | 2026-06-12 | Group 5 GCL rollout: `aws-athena-ops`, `aws-guardduty-ops`, `aws-opensearch-ops`, `aws-ram-ops`, `aws-securityhub-ops` — all 23 GCL-enabled skills |
| 1.9.0 | 2026-06-13 | Group 6 GCL rollout: `aws-aurora-ops` — 24 GCL-enabled skills |
| 1.10.0 | 2026-06-13 | `aws-aurora-ops` AIOps delegate + `aws-aiops-cruise` / `aws-aiops-orchestrator` GCL disabled (meta) — final count 26 GCL-enabled + 2 meta read-only + 1 generator meta = 29 total `aws-<svc>-ops` |
| 1.11.0 | 2026-06-27 | **Critic-isolation hardening.** Added §7.1 (User→Output placeholder mapping) and a new anti-pattern to §9 (`{{user.*}}` in Critic templates banned). Migrated all 22 affected skill prompt-templates.md to route `{{user.region}}` → `{{output.requested_region}}` and `{{user.safety_confirm}}` → `{{output.safety_confirm_token}}`. Added `scripts/gcl_runner.py` (Phase 2 reusable Orchestrator; see §10). Updated `aws-guardduty-ops` rubric to 0/0.5/1 discrete scale + ABORT clause. Spec now covers 31 `aws-<svc>-ops` skills; see `AGENTS.md` §11.5 for the Per-Skill Defaults table (also updated). |
| 1.12.0 | 2026-06-27 | **A11–A16 added + prompt-skeleton extraction (O3).** §8 gained six new repo-wide rules: A11 (CloudFront delete must disable→poll Deployed first), A12 (ELB deregister-targets 50%/100% drain confirmation), A13 (VPC delete-vpc 8-describe pre-flight), A14 (RDS/Aurora `--skip-final-snapshot` guard), A15 (S3 `Principal: *` policy widening guard), A16 (ASG `--force-delete` requires scale-to-0 + InstanceProtection=false). Backfilled A-id labels into the 7 affected rubrics. Created `aws-skill-generator/references/prompt-skeletons.md` (canonical Generator/Critic/Orchestrator templates + shared Variable Convention). `scripts/_sync_prompt_skeletons.py` retro-migrated all 31 skill `prompt-templates.md` from ~5,800 lines of duplicated boilerplate to ~2,200 lines of thin deltas (-78%). `scripts/gcl_runner.py` now resolves the rendered Critic prompt at runtime via `render_critic_prompt()` and exposes `--print-critic` for inspection. Net repo diff: 48 files, -3,456 lines. |
| 1.13.0 | 2026-07-04 | **Parallel GCL added (§12).** Documents the multi-Generator + single-Critic pattern for composite tasks that decompose into independent subtasks. Includes flow diagram, 5 rules, 4 anti-patterns, and WAF-ALB-01 example. Applicable to `aws-aiops-cruise` and `aws-aiops-orchestrator` composite rule development. |

## 12. Parallel GCL (Multiple Generators + Single Critic)

For **composite tasks** that decompose into independent subtasks, the
Orchestrator MAY fan out to **multiple Generators in parallel**, then
collect results and pass them all to a **single Critic** for audit.

### 12.1 When to use Parallel GCL

| Criterion | Parallel GCL | Sequential GCL |
|-----------|-------------|----------------|
| Subtasks are **independent** (no shared state) | ✅ Use parallel | ❌ Overhead not justified |
| Subtasks modify **different files/resources** | ✅ Use parallel | ❌ Risk of conflicts |
| Subtasks have **different domain expertise** | ✅ Use parallel (specialist agents) | ❌ Single G sufficient |
| Subtasks are **sequential** (B depends on A) | ❌ Must be sequential | ✅ Use sequential |

### 12.2 Flow

```
User Request
     │
     ▼
[0] Decompose (Orchestrator)
    - identify independent subtasks
    - assign category + skills per subtask
     │
     ├──▶ [1a] Generator A ──┐
     │                       │
     ├──▶ [1b] Generator B ──┤   (parallel, isolated contexts)
     │                       │
     └──▶ [1c] Generator N ──┘
              │
              ▼
[2] Collect Results (Orchestrator)
    - gather all G outputs
     │
     ▼
[3] Critique (C) ──────────────────┐
    - single Critic session         │
    - scores ALL G outputs          │
    - cross-references between Gs   │
     │                              │
     ▼                              │
[4] Decide (Orchestrator)          │
    - Safety=0 on ANY G → ABORT    │
    - all pass → RETURN composite   │
    - else & iter<max → fix + loop  │
     └──────────────────────────────┘
```

### 12.3 Rules

1. **Isolation**: Each Generator runs in its own `task()` call with
   `run_in_background=true` (or separate subagent sessions). No shared
   mutable state between Generators.
2. **File partitioning**: Generators MUST NOT modify the same file unless
   the Orchestrator explicitly coordinates (e.g., Generator A edits
   `file_a.py`, Generator B edits `file_b.py`).
3. **Critic scope**: The single Critic receives ALL Generator outputs and
   audits them as a composite. The Critic MUST cross-reference between
   outputs (e.g., "Generator A's entry in `registry.py` imports from
   Generator B's function in `governance.py`").
4. **Failure handling**: If ANY Generator fails, the Orchestrator MAY
   retry that subtask or abort the entire parallel GCL.
5. **Termination**: Same as sequential GCL (§5): PASS / MAX_ITER /
   SAFETY_FAIL. Safety=0 on ANY subtask → ABORT all.

### 12.4 Anti-patterns specific to Parallel GCL

- ❌ **Generators share mutable state** — race conditions → banned
- ❌ **Generators modify the same file** — merge conflicts → banned
- ❌ **Critic audits only one Generator output** — misses cross-reference
  issues → must audit ALL
- ❌ **Orchestrator executes without Critic** — defeats GCL → banned

### 12.5 Example: WAF-ALB-01 composite rule

```
Decompose:
  - Generator A: Add WAF to PRODUCTS + HTTPCode_ELB_5XX_Count to ALB
    File: _shared.py
  - Generator B: Implement WAF-ALB-01 inference rule
    File: _inference.py

  Both run in parallel (different files, no conflict).

Critic:
  - Audits both files
  - Cross-references: WAF product name matches inference rule's signals["WAF"] key
  - Scores all 5 rubric dimensions on both changes

Result: PASS + 1 fix (WAF id field corrected from UUID to Name)
```

## 13. See also

- `AGENTS.md` §11 — top-level index, Per-Skill Defaults table, current phase
- Each pilot skill's `references/rubric.md` — the rubric instance
- Each pilot skill's `references/prompt-templates.md` — the G/C/O prompt skeletons
- `CLAUDE.md` — shared baseline (dual-path execution, credential convention)
