# Cross-Session Learnings

> Append-only log of lessons learned during implementation work. Each entry
> is keyed by date + topic and pinned to a specific commit / spec.

## Index

| # | Lesson | Date | Category |
|---|---|---|---|
| 1 | G3 body-dupe skip whole header block | 2026-07-28 | TE Gate |
| 2 | G1 off-by-one on trailing newline | 2026-07-28 | TE Gate |
| 3 | Inline YAML arrays save 4-5 lines/frontmatter | 2026-07-28 | TE Gate |
| 4 | Keep SHOULD/SHOULD NOT sub-headers literally | 2026-07-28 | TE Gate |
| 5 | Anchor links need target-heading existence check | 2026-07-28 | TE Gate |
| 6 | TDD step size: one block per commit | 2026-07-28 | Process |
| 7 | SNS: GCL+AIOps+variables compress to single executable paragraph | 2026-07-28 | P0-B |
| 8 | Final gate snapshot must cover all 4 dimensions | 2026-07-28 | P0-B |
| 9 | SQS/CloudFront JSON paths need machine-parseable labels | 2026-07-28 | P0-B |
| 10 | Long skills: contract in SKILL.md, details in references | 2026-07-28 | P0-B |
| 11 | SecretsManager: SecretString/SecretBinary never in trace | 2026-07-28 | P0-B |
| 12 | Aurora: AIOps runbook → delegate contract + references link | 2026-07-28 | P0-B |
| 13 | EKS: static version table violates TE-1; query live API | 2026-07-28 | P0-B |
| 14 | Auto Scaling: A16 scale-to-zero before force delete | 2026-07-28 | P0-B |
| 15 | SSM send-command: target-bound confirm + output masking | 2026-07-28 | P0-B |
| 16 | ElastiCache: default final snapshot; apply-immediately = failover | 2026-07-28 | P0-B |
| 17 | API GW production replace: decision tier + API key masking | 2026-07-28 | P0-B |
| 18 | Lambda delete: enumerate event source mappings first | 2026-07-28 | P0-B |
| 19 | OpenSearch: AUTO_HEAL only non-destructive; domain/snapshot/VPC need token | 2026-07-28 | P0-B |
| 20 | ELB deregistration: confirm intensity scales with % capacity | 2026-07-28 | P0-B |
| 21 | Security Hub: AUTO_HEAL only updates approved finding workflows | 2026-07-28 | P0-B |
| 22 | EventBridge: delete in ref graph order; token ≠ dependency check | 2026-07-28 | P0-B |
| 23 | S3: must retain A2/A6/A9/A15 + recursive confirm simultaneously | 2026-07-28 | P0-B |
| 24 | EFS: prove mount targets/access points/consumers clean first | 2026-07-28 | P0-B |
| 25 | Route53: multi-signal failover + precise record diff + decision-tier auth | 2026-07-28 | P0-B |
| 26 | ECR: explicit digest/tag set required; no wildcard/empty list | 2026-07-28 | P0-B |
| 27 | Batch C6 debt: batch by security domain, gate each independently | 2026-07-28 | P0-B |
| 28 | High-risk compress: retain service-specific hard gates (RDS A5, VPC A13…) | 2026-07-28 | P0-B |

---

## 2026-07-28 — TE Gate C6 Debt Pilot

**Files**: `docs/superpowers/specs/2026-07-28-te-gate-c6-debt-design.md`,
`docs/superpowers/plans/2026-07-28-te-gate-c6-debt-pilot.md`,
`scripts/tests/test_te_gate.py`, `scripts/te_gate.py`,
`aws-cloudwatch-ops/SKILL.md` (135→118), `aws-ram-ops/SKILL.md` (666→119),
`aws-ram-ops/references/operations.md` (new, 425 lines).

### Lesson 1 — G3 body-dupe check must skip the entire header block, not just the header line

**Problem**: `te_gate.py` reported `JSON path re-declared in body (TE-4)`
on the **header's own line** when the header used multi-path content like
`.A | .B → .C`. The header-block splitter stopped at the next `##` heading
but the body-dupe check only skipped up to `header_idx`, so a token
extracted from the LHS matched the RHS of the same line.

**Lesson**: The block boundary must be used both to extract declarations
and to bound the body-dupe scan. A sub-line in the block is a header,
not a body re-declaration.

**Evidence**: Fix: track `block_end_idx` (next `##` after the header) and
skip `i <= block_end_idx` in the body loop. 30+ of 37 skills have
multi-path header content; without this fix, P0-B hits spurious G3
failures when copy-pasting cloudwatch-style headers.

---

### Lesson 2 — G1 line count has an off-by-one when the file ends with `\n`

**Problem**: `check_g1` reported N+1 lines when the file was exactly N lines
ending in `\n`. The function used `text.count("\\n") + 1` which double-counts.

**Lesson**: Use `len(text.splitlines())` — correct regardless of trailing newline.

**Evidence**: Skills exactly 120 lines were spuriously reported as 121 and
failed G1. P0-B could not trust the `≤ 120` cap until this was fixed.

---

### Lesson 3 — Frontmatter YAML `cross_skill_deps` and `environment` can be inline arrays

**Problem**: Multi-line YAML lists consume 6+ lines per skill in frontmatter.

**Lesson**: `[aws-iam-ops, aws-vpc-ops, ...]` and
`[AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, ...]` syntax is valid YAML,
parses identically, and saves 4-5 lines per frontmatter. Only semantics
matter, not the YAML shape.

**Evidence**: 35 skills × 5 lines saved = 175 lines total recoverable.
Does not violate any Charter rule.

---

### Lesson 4 — SKILL.md must keep `### SHOULD Use When` / `### SHOULD NOT Use When` literal sub-headers

**Problem**: Compressing Trigger & Scope into a single paragraph (SHOULD: …
SHOULD NOT: …) saved lines but broke Charter C2's literal string check.

**Lesson**: Keep the `### SHOULD Use When` / `### SHOULD NOT Use When`
sub-headers even when content is compressed. They are 4 lines but preserve
the Charter invariant.

**Evidence**: P0-B should not strip these sub-headers when aggressively
compressing to stay under the 120-line cap.

---

### Lesson 5 — Cross-file anchor links need a "anchor actually exists in the target" check

**Problem**: Adding `[references/operations.md#config-placeholders]` in
SKILL.md created a broken link because the section was in SKILL.md, not
in operations.md. C2 (link integrity) only caught "file exists", not
"anchor exists".

**Lesson**: A real link-integrity check must (a) resolve the file,
(b) parse its headings, (c) match the GitHub-style anchor. Estimated
30 lines, not 200.

**Evidence**: P0-B validation must not give false PASS on broken anchor
references; this is a gap in the current `links_lint` coverage.

---

### Lesson 6 — TDD step size: replace one block per commit, not all at once

**Problem**: The first P0-B attempt used a 169-line `assert old in text`
script that failed on the AIOps block because the assumption about exact
whitespace was off by one newline. Hard to bisect.

**Lesson**: TDD discipline — replace one section, run `te_gate`, log RED,
move on. Each of 6 steps touched 30-60 lines and was independently
verifiable.

**Evidence**: Per-skill step list: frontmatter → JSON paths → trigger &
scope → variable convention → config placeholders → operations →
safety gates → AIOps → TE → quality gate → ref files. A 35-skill batch
rewrite is doomed if each skill is one big script.

---

## 2026-07-28 — P0-B Skills Compression (Lessons 7–28)

**Evidence**: changelog v16–v24; 37/37 skills pass `te_gate --all --strict`.

### Lesson 7 — SNS: GCL+AIOps+variables compress to single executable paragraph

**Problem**: SNS skill had GCL, AIOps, and variable convention spread
across 3 sections, consuming ~15 lines.

**Lesson**: GCL, AIOps runbook, and variable convention can be compressed
into one paragraph as long as the confirmation token, trace contract,
and output masking are preserved.

**Evidence**: `aws-sns-ops` compressed 231→103 lines; passed `te_gate
--strict`. 5/37 skills passed after this fix (v16).

---

### Lesson 8 — Final gate snapshot must cover all 4 dimensions, not just line count

**Problem**: A skill that passes the 120-line cap might still fail
behavioral tests, static quality, link integrity, or its own TE gate.

**Lesson**: The gate snapshot for each P0-B skill must simultaneously
cover: (1) behavioral test, (2) static quality (ruff/te_gate), (3) link
integrity, (4) target skill TE gate. Passing line count alone is
insufficient.

**Evidence**: Pilot E final validation expanded from line count check to
4-dimension snapshot; 5/37 skills passed at that point (v16).

---

### Lesson 9 — SQS/CloudFront JSON path gate requires machine-parseable labels

**Problem**: JSON path blocks written as prose comments were not
machine-verifiable, causing `te_gate` to give false PASSes.

**Lesson**: JSON path gate requires path lines to start with a parseable
label (e.g., `CreateQueue: .QueueUrl`). Prose comments are not
machine-verifiable assets.

**Evidence**: SQS and CloudFront JSON path blocks repaired in Pilots F–H;
8/37 skills passed after those fixes (v17).

---

### Lesson 10 — Long skills: keep operation contract in SKILL.md, CLI/SDK details in references

**Problem**: Long skills like EBS (270 lines) risked losing safety
contracts when compressed to fit the 120-line cap.

**Lesson**: SKILL.md should retain the operation contract (safety gates,
confirmation strings, destructive guards). CLI/SDK details belong in
`references/`. Compressing to the 120-line boundary is possible without
sacrificing safety as long as the contract stays in-skill.

**Evidence**: EBS compressed 270→120; safety gates retained (v17).

---

### Lesson 11 — SecretsManager: SecretString/SecretBinary rule must stay in-skill, not just references

**Problem**: Moving the "SecretString/SecretBinary never appear in trace"
rule to `references/` meant it was not enforced by the skill's own
safety gate.

**Lesson**: Service-specific safety rules must remain in the main skill
contract, not demoted to reference files. The skill's C6 gate validates
the main contract, not references.

**Evidence**: SecretsManager C6 recompressed; rule retained in main
contract; 11/37 skills passed (v18).

---

### Lesson 12 — Aurora: AIOps runbook table → delegate contract + references link

**Problem**: Aurora had a verbose AIOps runbook table taking 20+ lines.

**Lesson**: The AIOps runbook table can be replaced by a unified
`delegate contract` block + a `references/` link, as long as
`MANUAL/AI_ASSIST/AUTO_HEAL` and destructive token semantics are preserved.

**Evidence**: Aurora compressed 210→108; delegate contract + references
link retained (v18).

---

### Lesson 13 — EKS: version table violates TE-1; encode safety rule, query live API

**Problem**: EKS had a static supported-versions table, which becomes
stale and violates TE-1 (no static version debt).

**Lesson**: Retain "upgrade one minor version at a time" as a safety rule.
Real-time supported-version query should come from the AWS API, not a
static table.

**Evidence**: EKS compressed 245→97; static version table removed;
13/37 skills passed (v19).

---

### Lesson 14 — Auto Scaling: A16 scale-to-zero before force delete

**Problem**: Compressing Auto Scaling risked losing the A16 guard:
force delete is only safe after DesiredCapacity is first set to zero.

**Lesson**: The A16 scale-to-zero-before-force-delete rule must be
preserved in the main contract and cannot be replaced by a generic
delete confirmation.

**Evidence**: Auto Scaling compressed 265→110; A16 guard retained (v19).

---

### Lesson 15 — SSM send-command: target-bound confirm + output masking

**Problem**: `send-command` is not a resource deletion but has high
blast radius as a remote execution primitive.

**Lesson**: Even when C6-compressed, `send-command` operations must use
target-bound confirmations and mask stdout/stderr in traces.

**Evidence**: SSM compressed 253→101; remote-command confirm + masking
retained (v20).

---

### Lesson 16 — ElastiCache: default final snapshot; `--apply-immediately` = failover scenario

**Problem**: ElastiCache deletion had no explicit final-snapshot default.

**Lesson**: ElastiCache delete should default to `final-snapshot=true`.
The `--apply-immediately` flag (which can trigger failover) should be
a separate confirmation scenario, not folded into the generic delete confirm.

**Evidence**: ElastiCache compressed 271→107; final-snapshot default added (v20).

---

### Lesson 17 — API Gateway production replace: decision tier + API key / auth header masking

**Problem**: API Gateway production replacement is a high-impact write
operation but was not gated separately from other updates.

**Lesson**: Production replace operations need decision-tier control and
must mask API keys, auth headers, and request bodies in traces. Even
non-delete write operations warrant this treatment.

**Evidence**: API Gateway compressed 291→111; decision tier + masking
retained (v20).

---

### Lesson 18 — Lambda delete: enumerate event source mappings before deletion

**Problem**: Lambda delete confirmation was a generic "confirm function
deletion" dialog that didn't account for hidden triggers.

**Lesson**: Lambda delete must explicitly enumerate event source mappings.
When triggers exist, the confirmation should upgrade to
`DELETE_FUNCTION_WITH_TRIGGERS`. Generic delete confirmation is insufficient.

**Evidence**: Lambda compressed 294→110; trigger enumeration retained (v21).

---

### Lesson 19 — OpenSearch: AUTO_HEAL only non-destructive; domain/snapshot/VPC/pipeline need resource-bound token

**Problem**: OpenSearch had a generic AUTO_HEAL entry that could
inadvertently trigger destructive operations.

**Lesson**: OpenSearch AUTO_HEAL is limited to non-destructive修复 only.
Domain deletion, snapshot deletion, VPC endpoint deletion, pipeline
deletion, and engine upgrades all require resource-bound tokens.

**Evidence**: OpenSearch compressed 299→109; AUTO_HEAL scope narrowed (v21).

---

### Lesson 20 — ELB deregistration: confirm intensity scales with % capacity

**Problem**: ELB target deregistration used a single uniform confirmation.

**Lesson**: Confirmation intensity should scale with the proportion of
capacity being deregistered (<50%, ≥50%, 100%). Proportional scaling
is a more expressive risk representation than a uniform confirm.

**Evidence**: ELB compressed 300→118; proportional deregistration confirm
retained (v21).

---

### Lesson 21 — Security Hub: AUTO_HEAL only updates approved finding workflows

**Problem**: Security Hub AUTO_HEAL could be misused to automatically
close controls, product imports, or the Hub itself.

**Lesson**: Security Hub AUTO_HEAL is restricted to updating
workflow status of already-approved findings. It must not close controls,
product imports, or disable the Hub.

**Evidence**: Security Hub compressed 311→112; AUTO_HEAL scope restricted (v22).

---

### Lesson 22 — EventBridge: delete in reference-graph order; token ≠ dependency check

**Problem**: EventBridge delete confirmation was a single generic confirm.

**Lesson**: EventBridge resources must be deleted in reference-graph order:
targets → rule, rules → bus, API destinations → connection. A confirmation
token does not substitute for dependency order checking.

**Evidence**: EventBridge compressed 318→114; dependency-order deletion
retained (v22).

---

### Lesson 23 — S3: retain A2/A6/A9/A15 + recursive confirm simultaneously; no single "delete confirm" suffices

**Problem**: S3 had a single generic delete confirmation that didn't
cover versioned bucket deletion (A2), batch delete (A6), sensitive file
deletion (A9), or public access (A15).

**Lesson**: S3 C6 contract must simultaneously retain A2, A6, A9, A15
and recursive count/bytes confirmation. No single "delete confirmation"
is adequate for all S3 deletion scenarios.

**Evidence**: S3 compressed 326→109; all four A-rule confirmations retained (v22).

---

### Lesson 24 — EFS: prove mount targets + access points + consumers clean before delete

**Problem**: EFS delete confirmation only asked for filesystem confirmation.

**Lesson**: EFS delete must verify mount targets, access points, and
active consumers are all cleaned up first. A single filesystem confirmation
is insufficient to express EFS dependency risk.

**Evidence**: EFS compressed 328→100; dependency-clean confirmation retained (v23).

---

### Lesson 25 — Route53: multi-signal failover verification + precise record diff + decision-tier auth

**Problem**: Route53 failover was triggered by a single ELB or health check signal.

**Lesson**: Route53 failover requires multi-signal verification, precise
record diff documentation, and decision-tier authorization. A single
ELB/health-signal trigger is inadequate.

**Evidence**: Route53 compressed 343→110; multi-signal failover retained (v23).

---

### Lesson 26 — ECR: explicit digest/tag set required; wildcard or empty list is unsafe

**Problem**: ECR image deletion allowed wildcard or empty digest/tag lists.

**Lesson**: ECR image batch delete must bind to an explicit digest/tag
set and a count. Wildcard or empty-list forms are unsafe. Repository
policy public/cross-account widening requires a separate confirmation.

**Evidence**: ECR compressed 349→103; explicit digest set required (v23).

---

### Lesson 27 — Batch C6 debt: batch by security domain, gate each independently

**Problem**: Trying to clear all C6 debt in one pass created an
un-auditable mega-change.

**Lesson**: C6 debt clearance should be batched by security domain
(e.g., compute, data, network) with each batch independently gated.
"One shot complete" ≠ "one auditable change."

**Evidence**: P0-B ran 5 sequential batches of ~7 skills each;
37/37 passed `te_gate --all --strict` at closure (v24).

---

### Lesson 28 — High-risk service compress: retain service-specific hard gates

**Problem**: Aggressive compression risked stripping service-specific
safety rules in favor of generic guards.

**Lesson**: Each high-risk service has service-specific hard gates that
cannot be replaced by generic confirmation strings:

| Service | Hard Gate |
|---|---|
| RDS | A5: automated backup before deletion |
| VPC | A13: shared VPC unshare requires all consumers released |
| KMS | A4: key material expiry and pending import deletion |
| EC2 | A1: termination protection before instance delete |
| DynamoDB | trigger/TTL: streams must drain before table delete |
| CloudTrail | audit restore-only: trail recreation cannot be AUTO_HEALed |

**Evidence**: Final 12 skills (`rds`, `vpc`, `waf`, `guardduty`, `ecs`,
`athena`, `application-autoscaling`, `kms`, `acm`, `dynamodb`, `cloudtrail`,
`ec2`) compressed; all service-specific hard gates retained; 37/37 passed (v24).
