> 见 [AGENTS.md §11](../AGENTS.md) 索引

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

> The full 37-line Per-Skill Defaults table (with each skill's GCL tier,
> `max_iter`, and destructive-op list) has been moved out to
> [`docs/gcl-per-skill-defaults.md`](docs/gcl-per-skill-defaults.md).

Key points: all `required` / `recommended` skills have rolled out full GCL
implementations; `optional` and read-only tiers (cloudtrail /
topo-discovery / aiops-cruise) are handled via a downgrade strategy. Each
skill may override `max_iter` under its own `SKILL.md`'s
`## Quality Gate (GCL)`. Skills not listed default to GCL **disabled**.

### 11.6 Trace & audit (mandatory)

Every GCL run persists a JSON trace to
`./audit-results/gcl-trace-YYYYMMDD-HHMMSS-<run-id>.json` per the schema in spec §6.
`audit-results/` is git-ignored; traces retained 30 days; old traces pruned
by the Phase 2 Orchestrator runner.

### 11.7 Prompt templates (mandatory per skill)

Each skill's `references/prompt-templates.md` is a **thin specialization**
of the canonical shared skeleton at
[`references/prompt-skeletons.md`](aws-skill-generator/references/prompt-skeletons.md)
(spec §7). The per-skill file contains ONLY:

1. Skill metadata table (`{{skill.*}}` placeholders)
2. Hard rules (Critic template injection) — one bullet per
   service-specific rule, each citing a `gcl-spec.md` §8 A-id (A1–A16)
3. Confirmation Strings table — mandatory for every destructive op
4. Variable Convention deltas — only entries unique to this skill

The three canonical templates (Generator / Critic / Orchestrator) are
resolved from the shared skeleton at runtime by
`scripts/gcl_runner.py` via `render_critic_prompt()`. Placeholders MUST
follow the repository-wide `{{env.*}}` / `{{user.*}}` / `{{output.*}}`
convention. Critic prompt MUST hide the raw user request to prevent
"answer-aligned" rubber-stamping. New skill creators MUST use the
[`assets/new-skill-template/prompt-templates.md`](aws-skill-generator/assets/new-skill-template/prompt-templates.md)
copy-paste template; run `--dry-run` before merging.

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
- ❌ **Parallel GCL: Generators share mutable state** — race conditions → banned
- ❌ **Parallel GCL: Generators modify the same file** — merge conflicts → banned
- ❌ **Parallel GCL: Critic audits only one Generator output** — must audit ALL

### 11.9 AWS-specific rules (repo-wide)

Codified in `gcl-spec.md` §8. Highlights:

- **A1** `terminate-instances` requires user `--no-dry-run` opt-in
- **A7** `--region` must match `{{user.region}}` or `{{env.AWS_DEFAULT_REGION}}`
- **A8** Resource id must be echoed back from a `describe-*` lookup
- **A9** Plaintext `KeyMaterial` / `PasswordData` / `UserData` credentials
  in trace → Safety = 0; mask with `***` and length only
- **A10** `aws sts get-caller-identity` MUST be the first command in trace
- **A11** `cloudfront delete-distribution` must `disable → poll Deployed` first
- **A12** `elbv2 deregister-targets` ≥50% → requires drain confirmation
- **A13** `ec2 delete-vpc` requires 8-describe pre-flight
- **A14** `rds --skip-final-snapshot` → requires `DELETE_NO_SNAPSHOT` token
- **A15** `s3 put-bucket-policy` widening to `Principal: *` → requires public confirmation
- **A16** `autoscaling --force-delete` with `DesiredCapacity > 0` → must scale-to-0 first

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
| 1.11.0 | 2026-06-27 | **GCL hardening pass.** (a) Migrated 22 skill `prompt-templates.md` files to route `{{user.region}}` → `{{output.requested_region}}` and `{{user.safety_confirm}}` → `{{output.safety_confirm_token}}` inside the Critic section, eliminating the rubber-stamp vector (`gcl-spec.md` §9 anti-pattern); added §7.1 to `gcl-spec.md` documenting the placeholder mapping. (b) Shipped `scripts/gcl_runner.py` (Phase 2 reusable Orchestrator: §4 loop, §5 termination, §6 trace schema, 30-day prune, `--self-test` mode for unit verification). (c) `aws-guardduty-ops` rubric migrated from continuous 1.0/0.8/0.7 weights to spec-mandated 0/0.5/1 discrete scale + explicit ABORT-on-Safety-0 clause; `aws-guardduty-ops` prompt templates migrated from bare `{{cli_command}}` / `{{boto3_code}}` / `{{generator_output}}` to spec-compliant `{{output.*}}` namespaces. (d) `aws-iam-ops` rubric now explicitly references rules **A3** / **A7** / **A8** / **A9** / **A10** by id; `aws-vpc-ops` rubric added A9 (`UserData` / `KeyMaterial` masking) clause. (e) `gcl-spec.md` changelog extended to v1.11.0; "22 skills" references corrected to the actual 31-skill scope (28 required/recommended + 2 meta read-only + 1 generator meta). |
| 1.12.0 | 2026-06-27 | **O1 (A11–A16) + O3 (prompt-skeleton extraction) + `--print-critic` runtime.** `gcl-spec.md` §8 gained six new repo-wide safety rules: **A11** (CloudFront distribution delete requires disable→Deployed first), **A12** (ELB `deregister-targets` 50%/100% drain confirmation), **A13** (VPC `delete-vpc` 8-describe pre-flight), **A14** (RDS/Aurora `--skip-final-snapshot` guard, supersedes legacy A5 in `aws-aurora-ops`), **A15** (S3 `Principal: *` policy widening), **A16** (ASG `--force-delete` requires scale-to-0 + `InstanceProtection=false`). Backfilled A-id labels into the 7 affected rubrics (cloudfront/elb/vpc/rds/aurora/s3/autoscaling). Created `aws-skill-generator/references/prompt-skeletons.md` (canonical Generator/Critic/Orchestrator templates + shared Variable Convention table; 231 lines). New `scripts/_sync_prompt_skeletons.py` retro-migrated all 31 skill `prompt-templates.md` files from ~5,800 lines of duplicated boilerplate to **~2,200 lines of thin deltas (-78%)**; idempotent; supports `--skill <name>`, `--all`, `--dry-run`, `--restore`. `scripts/gcl_runner.py` now exposes `render_critic_prompt()` + `--print-critic` for inspecting the merged Critic prompt at runtime. All three termination paths (PASS / SAFETY_FAIL / MAX_ITER) verified end-to-end via `--self-test` after migration. Net repo diff vs pre-v1.11.0: 48 files changed, **-3,456 lines**. |
| 1.13.0 | 2026-06-27 | **§11.7 updated to reflect shared skeleton architecture (prompt-templates.md is now a thin specialization, not self-contained) + §11.9 extended with A11–A16 highlights + §11.5 Per-Skill Defaults table annotated with A-rules for 7 skills (cloudfront/elb/vpc/rds/aurora/s3/autoscaling). New copy-paste template at `aws-skill-generator/assets/new-skill-template/prompt-templates.md` for new skill creators.** |
| 1.14.0 | 2026-07-04 | **Parallel GCL added (§12 in gcl-spec.md).** Documents the multi-Generator + single-Critic pattern for composite tasks that decompose into independent subtasks (e.g., WAF-ALB-01). Includes flow diagram, 5 rules, 4 anti-patterns, and worked example. Applicable to `aws-aiops-cruise` and `aws-aiops-orchestrator` composite rule development. |

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

