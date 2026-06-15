# AGENTS.md

Repo-specific guidance for OpenCode/AI agents. Read `CLAUDE.md` first for the
shared baseline (architecture, credential convention, dual-path execution,
safety gates, error-recovery table). This file only records things an agent
would otherwise get wrong.

## What this repo is

A flat collection of AI-Agent runbooks for AWS services. Every top-level
`aws-<service>-ops/` directory is a *skill*, not source code. There is no
build, no lint, no test runner, no CI. "Editing the codebase" means editing
Markdown skill files and the YAML/JSON assets they ship.

There is exactly one meta-skill, `aws-skill-generator/`, that scaffolds and
governs all `aws-<service>-ops/` skills. Treat it as the source of truth for
structure, frontmatter, and review rules.

## Source-of-truth files (read these before editing skills)

- `aws-skill-generator/SKILL.md` — generation process, Charter (C1–C6),
  Token Efficiency rules (TE-1…TE-6).
- `aws-skill-generator/references/aws-skill-template.md` — required SKILL.md
  skeleton (frontmatter + section order).
- `aws-skill-generator/references/governance-review.md` — pre-merge
  checklist and adversarial scenarios (A–H). Skills failing C1–C6 or H1–H6
  must be auto-fixed, not merged.
- `aws-skill-generator/references/aws-cli-conventions.md`,
  `boto3-sdk-usage.md`, `integration.md` — shared conventions; individual
  skills reference these instead of duplicating.

## Skill layout (must match exactly)

```
aws-<service>-ops/
  SKILL.md                 # ~70–120 lines, "what to do" only
  references/
    aws-cli-usage.md       # CLI commands + JSON paths (verified)
    boto3-sdk-usage.md     # SDK patterns (no docstrings — TE-2)
    core-concepts.md       # Service architecture, quotas
    troubleshooting.md     # Compact error table (TE-3)
  assets/                  # example-config.yaml, dashboards, etc.
```

`prompt-examples.md`, `cost-tracking.md`, `escalation.md`,
`aiops-automation-engine.md` are optional extensions used by mature skills
(e.g. `aws-elb-ops`). Do not invent new file names without updating
`aws-skill-template.md` and the README.

## SKILL.md frontmatter gotcha (real bug currently in repo)

YAML frontmatter is a **single** block delimited by one opening and one
closing `---`. `aws-ec2-ops/SKILL.md` accidentally splits the block (a
stray `---` after the `description` value), which breaks frontmatter
parsers. When you create or edit a SKILL.md:

- Exactly two `---` markers, both at the start of the file.
- `description: >-` folded scalars must end with a blank line, **not** a
  `---` line.
- After editing frontmatter, verify with:
  `awk '/^---$/{c++; if(c==2){exit}} c==1' SKILL.md` returns the whole
  frontmatter block, and `head -1` is `---`.

## Mandatory sections in every SKILL.md

Enforced by Charter C1–C6 (see `governance-review.md`). Missing any of these
means the skill is invalid and must be auto-fixed:

1. YAML frontmatter with `name`, `description`, `license`, `compatibility`,
   `metadata`.
2. `## Trigger & Scope` with both `### SHOULD Use When` and
   `### SHOULD NOT Use When` (delegate names must point to skills that
   actually exist in this repo).
3. `## Variable Convention` table using only `{{env.*}}`, `{{user.*}}`,
   `{{output.*}}` placeholders. Never instruct the user to paste secrets;
   `{{env.AWS_ACCESS_KEY_ID}}` / `{{env.AWS_SECRET_ACCESS_KEY}}` must fail
   closed if unset.
4. Execution flow per operation: **Pre-flight → Execute → Validate → Recover**.
5. Explicit human confirmation step before any destructive op (delete,
   terminate, deregister, detach).
6. Token Efficiency (TE-1…TE-6): no hardcoded version/port/state tables,
   no SDK docstrings, compact error tables, JSON paths declared once at
   file top, YAML anchors in `example-config.yaml`, no duplicated flows
   across SKILL.md and references.

## Repo conventions worth knowing

- Always invoke CLI with `--output json`; assets and references assume
  JSON output so agents can `jq` paths.
- CLI is primary, boto3 is fallback after 3 CLI failures (CLAUDE.md).
- Credentials load order (highest first): shell env → `.env` → defaults.
  `.env` is git-ignored; `.env.example` is the template.
- `README.md` and `README_cn.md` must be kept in sync when adding,
  removing, or version-bumping a skill (the "Existing Skills" table and
  the AIOps section both reference per-skill versions).
- `.omc/` holds OpenCode session state and project memory — do not commit
  changes there as part of skill edits.

## Self-reflection rule (project policy)

> **Rule**: After every skill update, auto-run **2 rounds** of self-review
> and fix all discovered issues. Do not hand back to the user between rounds.
>
> Full spec (check tables, verification scripts, dedup procedures,
> implementation notes) at
> [`docs/post-update-self-review.md`](docs/post-update-self-review.md)

| Round | Scope | Key Checks |
|-------|-------|-----------|
| **R1: Structural** | Frontmatter / Trigger / Variables / Token Efficiency | C1–C6, TE-1…TE-6, **C6 MUST PASS** |
| **R2: Content** | CLI validation / error codes / safety gates / link integrity / dedup / TODO.md sync | F1–F8, **F5/F6/F8 MUST PASS** |

Each round, for every modified skill:

1. Re-read the modified SKILL.md from disk (do not trust memory).
2. **Verify Charter C1–C6** (see `governance-review.md`). Failure →
   report `[CHARTER VIOLATION] C{n}: {reason}` and auto-fix.
3. **Verify Token Efficiency TE-1…TE-6** per `aws-skill-generator/SKILL.md`.
   C6 is a MUST PASS gate — see [post-update-self-review.md](docs/post-update-self-review.md) §TE verification.
4. **Verify frontmatter** parses (single `---` open + close, see §frontmatter gotcha).
5. **Verify delegation references** — every `aws-<x>-ops` in SHOULD/SHOULD NOT
   or recovery tables must point to an existing directory.
6. **Verify destructive ops** (`delete`, `terminate`, `detach`, `revoke`)
   each have explicit confirmation in pre-flight.
7. **Verify JSON paths** match `references/aws-cli-usage.md` and the
   centralized "Common JSON Paths" block at SKILL.md top.
8. **Verify README sync** — `README.md` and `README_cn.md` tables reflect state.
9. **TE Post-Change Audit** — scan references/ for token waste per
   [post-update-self-review.md](docs/post-update-self-review.md) §Content Deduplication.

After round 2 passes cleanly, report a one-line summary per modified
skill: `[OK] aws-<service>-ops v<version> — 2 rounds clean`.

If round 2 still finds issues, run additional rounds until clean. Do
**not** stop after 2 rounds if problems remain.

### Reflexion Memory (cross-session learning)

Failed operations leave structured failure patterns in
[`docs/failure-patterns.md`](docs/failure-patterns.md). Before executing any
high-risk operation, the agent MUST check this file for known failure modes
of the target resource type. Each pattern records:

| Field | Purpose |
|-------|---------|
| `resource_type` | Which AWS resource (e.g., `aws-rds-db-instance`) |
| `failure_mode` | What went wrong (e.g., `final-snapshot-skip-in-prod`) |
| `root_cause` | Why it happened |
| `fix` | What the agent should do differently |
| `severity` | `P0` (block) / `P1` (warn) / `P2` (info) |
| `added_date` | When the pattern was recorded |

Patterns are appended after every GCL `SAFETY_FAIL` or `MAX_ITER` with
unresolved safety issues. The agent treats these as **hard constraints** —
not suggestions — when planning or executing operations.

## When the user asks for a new AWS skill

Load `aws-skill-generator` first, then collect the inputs listed under
"Quick Start Checklist → P0" in its SKILL.md before generating any
files. The directory you create must mirror the layout above exactly,
and the generated SKILL.md must pass the Charter and TE rules on the
first round of self-reflection — if it does not, fix the generator
output, not just the symptom in the new skill.

## 11. Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> Inspired by GAN's Generator/Discriminator idea, but deliberately **not** a
> real GAN. Naming: **GCL (Generator-Critic-Loop)** to avoid misleading
> reviewers and LLM trainees.

### 11.1 Purpose

Apply an adversarial **Generator ↔ Critic** loop with a quantitative rubric
to every skill execution. Most valuable in **high-side-effect AWS
operations** (`terminate-instances`, `delete-bucket`, `delete-db-instance`,
`iam delete-user`, `kms schedule-key-deletion`, etc.) where a single
mistake is unrecoverable.

The full specification lives in
[`aws-skill-generator/references/gcl-spec.md`](aws-skill-generator/references/gcl-spec.md).
This section is the **index, current rollout status, and Per-Skill
Defaults table** — read it first, then load the spec for detail.

| GAN (real) | GCL (this spec) |
|---|---|
| Discriminator learns sample distribution | Critic scores an **explicit rubric** |
| No termination condition | Must terminate: **PASS / MAX_ITER / SAFETY_FAIL** |
| G and D train in parallel | G and C run **sequentially** |
| Goal: "fool the D" | Goal: "pass the rubric threshold" |

### 11.2 Roles & isolation

| Role | Job | Forbidden |
|---|---|---|
| **Generator (G)** | Execute the AWS op via `aws --output json` (primary) / boto3 (fallback) | modifying the rubric; self-scoring |
| **Critic (C)** | Independently audit G's output against the rubric | calling `aws` / `boto3` / mutating anything |
| **Orchestrator (O)** | Loop control, termination, final return | executing or scoring on its own |

G and C MUST live in **isolated prompt contexts** (separate sessions or
sub-agents). Shared context is a "pseudo-GCL" and is banned — see spec §9.

### 11.3 Rubric (mandatory per skill)

Each skill declares its 5-dimension rubric in `references/rubric.md`:
**Correctness / Safety / Idempotency / Traceability / Spec Compliance** on
a 0 / 0.5 / 1 scale. **Safety = 0 → ABORT immediately**, regardless of
total score. Full rules in spec §3.

### 11.4 Termination (first match wins)

| Condition | Behavior |
|---|---|
| **PASS** | Every rubric dimension meets its threshold → return G's result |
| **MAX_ITER** | Reached `max_iterations` → return **best-so-far** + unresolved rubric items |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**; never return partial output |

### 11.5 Per-Skill Defaults

| Skill | GCL | Default `max_iter` | Notes |
|---|---|---|---|
| `aws-ec2-ops` | **required (pilot)** | 2 | `terminate-instances`, `delete-key-pair`, `deregister-image`, `detach-volume` |
| `aws-autoscaling-ops` | **required** | 2 | `delete-auto-scaling-group` (`--force-delete` guard), `delete-launch-configuration`, `detach-instances` (decrement guard), `set-desired-capacity` → 0 — shipped v1.0.0 |
| `aws-config-ops` | **recommended** | 3 | `delete-config-rule`, `delete-configuration-recorder`, `stop-configuration-recorder` — shipped v1.0.0 |
| `aws-eventbridge-ops` | **recommended** | 3 | `delete-rule` (target cleanup guard), `delete-event-bus`, `delete-schedule`, `delete-pipe` — shipped v1.0.0 |
| `aws-iam-ops` | **required (pilot)** | 2 | `delete-user`, `detach-user-policy`, `delete-access-key`; `*:*` policy guard |
| `aws-kms-ops` | **required (pilot)** | 2 | `schedule-key-deletion` is irreversible; `--pending-window-in-days ≥ 7` |
| `aws-s3-ops` | **required (pilot)** | 2 | `delete-bucket` (Versioned guard), `delete-objects` (empty array refusal) |
| `aws-rds-ops` | **required** | 2 | `delete-db-instance` (final-snapshot guard for prod) — shipped v1.1.0 |
| `aws-aurora-ops` | **required** | 2 | `delete-db-cluster`, `delete-db-cluster-snapshot`, `failover-db-cluster`, `backtrack-db-cluster`, Global Database detach — shipped v1.0.0 |
| `aws-lambda-ops` | **required** | 2 | `delete-function` (irreversible), `delete-function-concurrency` — shipped v1.1.0 |
| `aws-dynamodb-ops` | **required** | 2 | `delete-table` (data loss), `update-table` (throughput) — shipped v1.1.0 |
| `aws-elasticache-ops` | **required** | 2 | `delete-replication-group`, `delete-cache-cluster` |
| `aws-route53-ops` | **required** | 2 | `delete-hosted-zone` (DNS cut) — shipped v1.2.0 |
| `aws-sqs-ops` | **required** | 2 | `delete-queue` (in-flight message loss) |
| `aws-sns-ops` | **required** | 2 | `delete-topic`, `unsubscribe` |
| `aws-cloudfront-ops` | **required** | 2 | `delete-distribution` (cache invalidation + DNS) — shipped v1.1.0 |
| `aws-waf-ops` | **required** | 2 | `delete-rule-group`, `delete-web-acl` |
| `aws-secretsmanager-ops` | **required** | 2 | `delete-secret` (irrecoverable), `put-secret-value` |
| `aws-ssm-ops` | **required** | 2 | `send-command` (remote exec), `delete-parameter` |
| `aws-stepfunctions-ops` | **required** | 2 | `delete-state-machine`, `stop-execution` |
| `aws-vpc-ops` | **required** | 2 | `delete-vpc` (cascade), `delete-security-group` (cross-ref) — shipped v1.3.0 |
| `aws-acm-ops` | required | 2 | `delete-certificate` (in-use guard) |
| `aws-eks-ops` | required | 2 | `delete-cluster` (irreversible) |
| `aws-elb-ops` | recommended | 3 | `delete-load-balancer`, `deregister-targets` ≥50% DRAIN — shipped v2.2.0 |
| `aws-cloudwatch-ops` | recommended | 3 | `delete-alarms` (silent-failure guard) |
| `aws-athena-ops` | **required** | 2 | `delete-work-group`, `delete-named-query`, `delete-data-catalog`, `delete-prepared-statement` — shipped v1.0.0 |
| `aws-guardduty-ops` | **required** | 2 | `delete-detector`, `delete-filter`, `delete-ip-set`, `delete-threat-intel-set`, `delete-publishing-destination` — shipped v1.0.0 |
| `aws-opensearch-ops` | **required** | 2 | `delete-domain` (data loss), `delete-snapshot`, `delete-vpc-endpoint`, `delete-ingestion` — shipped v1.0.0 |
| `aws-ram-ops` | **required** | 2 | `delete-resource-share` (breaks dependent accounts), `delete-permission`, `delete-permission-version` — shipped v1.0.0 |
| `aws-securityhub-ops` | **required** | 2 | `delete-insight`, `delete-action-target`, `delete-automation-rule`, `delete-configuration-policy`, `disable-securityhub` — shipped v1.0.0 |
| `aws-cloudtrail-ops` | optional | 3 | read-mostly; `delete-trail` = severe |
| `aws-skill-generator` | optional | 3 | meta operation; secret-leak guard |
| `aws-topo-discovery` | optional | 3 | read-only discovery; no destructive operations |
| `aws-aiops-cruise` | optional | 3 | read-only full-chain patrol; 7 Perceive Agents; no destructive operations |

Each skill may override its own `max_iter` in its `SKILL.md` under
`## Quality Gate (GCL)`. A skill not yet listed has GCL **disabled** by
default — pilots are rolled out one at a time per the spec §10 roadmap.

### 11.6 Trace & audit (mandatory)

Every GCL run persists a JSON trace to
`./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` per the schema in spec §6.
`audit-results/` is git-ignored; traces retained 30 days; old traces pruned
by the Phase 2 Orchestrator runner.

### 11.7 Prompt templates (mandatory per skill)

Each skill's `references/prompt-templates.md` MUST contain Generator,
Critic, and Orchestrator decider skeletons (spec §7). Placeholders MUST
follow the repository-wide `{{env.*}}` / `{{user.*}}` / `{{output.*}}`
convention (see AGENTS.md §Variable Convention). Critic prompt MUST hide
the raw user request to prevent "answer-aligned" rubber-stamping.

### 11.8 Anti-patterns (banned)

- ❌ **Shared context G+C** — defeats independence → banned
- ❌ **Subjective scoring** — Critic must use the rubric, not "vibes" → banned
- ❌ **Unbounded loop** — always hard-cap iterations → banned
- ❌ **Critic sees the user request** — encourages rubber-stamping → banned
- ❌ **Silently downgrade on Safety fail** — must ABORT visibly → banned
- ❌ **Trace not persisted** — no post-mortem possible → banned
- ❌ **Critic mutates resources** — Critic is read-only by definition → banned
- ❌ **`aws --output json` placed before subcommand** — non-portable;
  convention is `aws <svc> <op> --output json` (see CLAUDE.md) → banned
  in GCL traces and examples

### 11.9 AWS-specific rules (repo-wide)

Codified in `gcl-spec.md` §8. Highlights:

- **A1** `terminate-instances` requires user `--no-dry-run` opt-in
- **A7** `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** Resource id must be echoed back from a `describe-*` lookup
- **A9** Plaintext `KeyMaterial` / `PasswordData` / `UserData` credentials
  in trace → Safety = 0; mask with `***` and length only
- **A10** `aws sts get-caller-identity` MUST be the first command in trace

### 11.10 Rollout roadmap

- **Phase 1 (in progress)** — spec + this index shipped; pilots on
  **`aws-ec2-ops`** (compute, destructive workload),
  **`aws-iam-ops`** (identity, secret-handling + wildcard-policy guards),
  **`aws-kms-ops`** (encryption, irreversible deletion + plaintext
  masking), and **`aws-s3-ops`** (storage, Versioned-bucket guard +
  public-access widening + `--recursive` rm count confirmation). Roll
  forward to remaining `required` skills one at a time (see §11.5 table).
- **Phase 2** — add `scripts/gcl_runner.py` as a reusable Orchestrator
  (invokes G, then C in isolated context, persists trace, enforces
  termination). Independent of any specific agent runtime.
- **Phase 3** — feed `gcl-trace-*.json` into a CloudWatch dashboard /
  Athena query for Quality Gate pass-rate and per-skill failure-mode
  histograms.
- **Phase 4** — wire rubric pass-rate to CloudWatch Alarms; production
  incidents refine thresholds.

### 11.11 Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial GCL specification added (`aws-skill-generator/references/gcl-spec.md`) and `AGENTS.md` §11 index; pilot scoped to **`aws-ec2-ops`** with `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); Per-Skill Defaults table covers all 22 existing skills |
| 1.1.0 | 2026-06-04 | Second GCL pilot on **`aws-iam-ops`** (v1.1.0) — added `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); IAM-specific safety rules for `*:*` / `AdministratorAccess` attach, root-account `create-access-key` refusal, `Principal: *` trust policy guard, attached-policies pre-flight for `delete-user`, `SecretAccessKey` never logged |
| 1.2.0 | 2026-06-04 | Third GCL pilot on **`aws-kms-ops`** (v2.1.0) — added `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); KMS-specific safety rules for irreversible `schedule-key-deletion` (`--pending-window-in-days ≥ 7`, literal `PERMANENTLY DELETE <key-id>` confirmation), outstanding-grants pre-flight, `Principal: *` widening `put-key-policy` guard, `delete-custom-key-store` requires no `Enabled` CMKs; **`Plaintext` and `CiphertextBlob` never logged** (masked to `***<len>` and first16+last4 respectively) |
| 1.3.0 | 2026-06-04 | Fourth GCL pilot on **`aws-s3-ops`** (v1.1.0) — added `references/rubric.md` (v1) and `references/prompt-templates.md` (v1); S3-specific safety rules for Versioned `delete-bucket` (rule A2 — must `list-object-versions` + `delete-object-versions` first), `delete-objects` empty-array refusal (rule A6), `aws s3 rm --recursive` count-and-bytes confirmation, `Principal: *` widening `put-bucket-policy` guard, public canned ACL refusal, MFA-Delete bucket confirmation, sensitive-file upload (`.env`/`*.pem`/`*.key`) gated + content masked (rule A9) |
| 1.4.0 | 2026-06-04 | Group 1 GCL rollout: **`aws-rds-ops`** (v1.1.0) final-snapshot guard (rule A5: `--skip-final-snapshot` needs `DELETE_NO_SNAPSHOT`), `MasterUserPassword` MUST be Secrets Manager ARN (rule A9); **`aws-lambda-ops`** (v1.1.0) `delete-function` irreversibility + event source mapping guard, ALL env vars masked (rule A9), pre-existing Charter fix `## Flow Pattern` → `## Execution Flow Pattern`; **`aws-dynamodb-ops`** (v1.1.0) `delete-table` irreversibility + GSIs/LSIs pre-flight, GSI REMOVE confirm, TTL enable confirm (irreversible 48 h), item values ALL masked (rule A9). Helper scripts `_add_gcl_to_skill.py` + `_gen_rubric.py` shipped. |
| 1.5.0 | 2026-06-04 | Group 2 GCL rollout: **`aws-vpc-ops`** (v1.3.0) `delete-vpc` 8-describe pre-flight (subnets/IGWs/NATs/RTs/SGs/endpoints/peering/NACLs), main RT undeletable, default SG undeletable while VPC has instances, public SG ingress on sensitive ports; **`aws-route53-ops`** (v1.2.0) `change-resource-record-sets: DELETE` + prod DNS guard, `delete-hosted-zone` non-NS/SOA refusal; **`aws-cloudfront-ops`** (v1.1.0) `delete-distribution` MUST disable first (poll `Status=Deployed`), OAC vs OAI guard; **`aws-elb-ops`** (v2.2.0, **recommended**, max_iter=3) `deregister-targets` 50%/100% drain threshold, default rule undeletable. |
| 1.6.0 | 2026-06-07 | New skill — **`aws-autoscaling-ops`** (v1.0.0) with full GCL scaffolding: `delete-auto-scaling-group` (`--force-delete` guard + scale-to-0 pre-flight), `delete-launch-configuration`, `detach-instances` (decrement guard), `set-desired-capacity` → 0 guard, `suspend-processes` (HealthCheck/ReplaceUnhealthy) safety, `confirm=DELETE <asg-name>` / `confirm=DETACH <instance-id>` patterns; rubric.md and prompt-templates.md shipped. |
| 1.7.0 | 2026-06-07 | New skills — **`aws-config-ops`** (v1.0.0, recommended, max_iter=3) with `delete-config-rule`, `stop-configuration-recorder`, `delete-configuration-recorder` guards; **`aws-eventbridge-ops`** (v1.0.0, recommended, max_iter=3) with `delete-rule` target-cleanup guard, `delete-event-bus`, `delete-schedule`, `delete-pipe`; both shipped with full rubric.md and prompt-templates.md. |
| 1.8.0 | 2026-06-12 | Added 5 skills to §11.5 Per-Skill Defaults table (back-filled from Groups 6–7 GCL rollout): **`aws-athena-ops`** (required, max_iter=2), **`aws-guardduty-ops`** (required, max_iter=2), **`aws-opensearch-ops`** (required, max_iter=2), **`aws-ram-ops`** (required, max_iter=2), **`aws-securityhub-ops`** (required, max_iter=2) — all shipped with rubric.md and prompt-templates.md. |
| 1.9.0 | 2026-06-13 | New skill — **`aws-aurora-ops`** (v1.0.0→**v1.1.0** AIOps): orchestrator delegate contract, 8 prompt scenarios, layered inspection, AIOps metrics CLI, cross-skill chains; **`aws-rds-ops`** delegates Aurora failover; **`aws-aiops-cruise`** / **`aws-aiops-orchestrator`** route Aurora cluster ops here. |
| 1.10.0 | 2026-06-13 | **`aws-aurora-ops`** v1.2.0 P2: orchestrator runbooks RB-023–RB-027, detection rules FD-15/16 PD-08/09, `incident-schema` v1.1.0 Aurora/`RDSProxy` resource types + examples. |

### 11.12 See also

- [`aws-skill-generator/references/gcl-spec.md`](aws-skill-generator/references/gcl-spec.md) — full GCL specification
- [`aws-ec2-ops/references/rubric.md`](aws-ec2-ops/references/rubric.md) — pilot rubric instance
- [`aws-ec2-ops/references/prompt-templates.md`](aws-ec2-ops/references/prompt-templates.md) — pilot G/C/O skeletons
- [`aws-iam-ops/references/rubric.md`](aws-iam-ops/references/rubric.md) — second pilot rubric instance
- [`aws-iam-ops/references/prompt-templates.md`](aws-iam-ops/references/prompt-templates.md) — second pilot G/C/O skeletons
- [`aws-kms-ops/references/rubric.md`](aws-kms-ops/references/rubric.md) — third pilot rubric instance
- [`aws-kms-ops/references/prompt-templates.md`](aws-kms-ops/references/prompt-templates.md) — third pilot G/C/O skeletons
- [`aws-s3-ops/references/rubric.md`](aws-s3-ops/references/rubric.md) — fourth pilot rubric instance
- [`aws-s3-ops/references/prompt-templates.md`](aws-s3-ops/references/prompt-templates.md) — fourth pilot G/C/O skeletons
- [`aws-rds-ops/references/rubric.md`](aws-rds-ops/references/rubric.md) — Group 1 rubric
- [`aws-lambda-ops/references/rubric.md`](aws-lambda-ops/references/rubric.md) — Group 1 rubric
- [`aws-dynamodb-ops/references/rubric.md`](aws-dynamodb-ops/references/rubric.md) — Group 1 rubric
- [`aws-vpc-ops/references/rubric.md`](aws-vpc-ops/references/rubric.md) — Group 2 rubric
- [`aws-route53-ops/references/rubric.md`](aws-route53-ops/references/rubric.md) — Group 2 rubric
- [`aws-cloudfront-ops/references/rubric.md`](aws-cloudfront-ops/references/rubric.md) — Group 2 rubric
- [`aws-elb-ops/references/rubric.md`](aws-elb-ops/references/rubric.md) — Group 2 rubric (recommended)
- [`aws-athena-ops/references/rubric.md`](aws-athena-ops/references/rubric.md) — Group 6 rubric
- [`aws-athena-ops/references/prompt-templates.md`](aws-athena-ops/references/prompt-templates.md) — Group 6 G/C/O skeletons
- [`aws-guardduty-ops/references/rubric.md`](aws-guardduty-ops/references/rubric.md) — Group 6 rubric
- [`aws-guardduty-ops/references/prompt-templates.md`](aws-guardduty-ops/references/prompt-templates.md) — Group 6 G/C/O skeletons
- [`aws-opensearch-ops/references/rubric.md`](aws-opensearch-ops/references/rubric.md) — Group 6 rubric
- [`aws-opensearch-ops/references/prompt-templates.md`](aws-opensearch-ops/references/prompt-templates.md) — Group 6 G/C/O skeletons
- [`aws-ram-ops/references/rubric.md`](aws-ram-ops/references/rubric.md) — Group 7 rubric
- [`aws-ram-ops/references/prompt-templates.md`](aws-ram-ops/references/prompt-templates.md) — Group 7 G/C/O skeletons
- [`aws-securityhub-ops/references/rubric.md`](aws-securityhub-ops/references/rubric.md) — Group 7 rubric
- [`aws-securityhub-ops/references/prompt-templates.md`](aws-securityhub-ops/references/prompt-templates.md) — Group 7 G/C/O skeletons
- Top-level `CLAUDE.md` — shared baseline (dual-path, credentials, recovery table)
