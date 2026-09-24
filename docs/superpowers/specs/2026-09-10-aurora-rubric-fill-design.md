# Design — `aws-aurora-ops` rubric fill (+ generator CLI-namespace defect)

Plan: `docs/superpowers/plans/2026-09-10-aurora-rubric-fill.md`

## Problem

1. **Unfilled rubric instance.** `aws-aurora-ops/references/rubric.md` still
   carries the generator's placeholder markers
   (`<!-- LLM_FILL: ... -->` + `<!-- TODO: list every operation ... -->`)
   in both service-specific sections — `## Operation-specific overrides`
   and `## Safety special cases (auto-fail)`. It is the only rubric in the
   repo in that state (36 other `rubric.md` files are filled). The skill is
   `gcl.class = required`, `max_iter = 2`, so a GCL run loads this file as
   the scoring contract: the per-op overrides and the auto-fail list are
   simply absent, and the Critic has nothing service-specific to score
   against beyond the generic 5 dimensions.
2. **Generator CLI-namespace defect.** `scripts/_gen_rubric.py::_aws_cli_svc()`
   maps a skill dir to its AWS CLI namespace; the map is missing
   `aws-aurora-ops`, so it falls through to the derived value `aurora`.
   Aurora is driven by the **`rds`** namespace (`aws rds create-db-cluster`,
   `aws rds failover-db-cluster`, …). Regenerating the rubric therefore
   writes `aws aurora <op>` into the Traceability dimension. The same
   omission exists in `scripts/_sync_prompt_skeletons.py::CLI_OVERRIDES`,
   which produced `{{skill.aws_cli_svc}} = aurora` in
   `aws-aurora-ops/references/prompt-templates.md` — the value the shared
   skeleton interpolates into the Generator prompt's command line.

Both defects are pre-existing; (2) blocks a correct (1), since the requested
path is "regenerate with `_gen_rubric.py`".

## Decision

- **Fill the two sections by hand-editing after regeneration.** The
  requested `--llm-fill` path is unavailable: `_llm_rubric_fill.call_llm()`
  needs `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`; neither is set in this
  environment, and no `.env` exists, so the generator emits
  `WARNING: LLM fill skipped` and writes the untouched template. The
  Generator of record for the GCL loop is therefore the agent, not
  DashScope — recorded in the trace.
- **Fix the namespace map in both scripts** and the one generated line in
  `aws-aurora-ops/references/prompt-templates.md`. Mapping aurora → `rds` is
  the same convention already used for `aws-ebs-ops → ec2` and
  `aws-elb-ops → elbv2`. Without it, the regeneration request writes a
  known-wrong command namespace into the deliverable.
- **Content bar = the sibling `aws-rds-ops` rubric.** Same CLI namespace,
  same A-rule family (A14 supersedes the legacy A5 for Aurora per
  `gcl-spec.md` §11 v1.12.0), same profile: an ops × required-dimensions
  table plus an auto-fail list that cites A-ids by reference rather than
  restating them.
- **Rubric version stays `v1`.** §11 of `gcl-spec.md` versions the *spec*;
  a rubric's own version tracks its instantiation. The file keeps
  `Rubric version: v1` and gains a `1.0.1` changelog row (content fill, no
  dimension/threshold change). In-file revision-row precedent:
  `aws-athena-ops/references/rubric.md:75`,
  `aws-eks-ops/references/rubric.md:61`.
- **The generator must not be able to destroy a fill.** `main()` wrote
  `references/rubric.md` unconditionally, so re-running it after a fill
  silently replaced the content with the bare template — the failure mode
  this task is repairing. It now refuses when the target exists without a
  fill marker, and requires `--force` to regenerate.

## Scope

In: `aws-aurora-ops/references/rubric.md`,
`aws-aurora-ops/references/prompt-templates.md` (metadata row +
Confirmation Strings rows), `scripts/_gen_rubric.py` (namespace map,
template heading, overwrite guard), `scripts/_sync_prompt_skeletons.py`
(namespace map + comment), a new regression test, and this spec/plan pair.

Out: the other 36 rubrics, the `aws-aiops-cruise` inference code, the
`.worktrees/` copy (stale worktree; not tracked).

## Verification

| Gate | Command | Expected |
|---|---|---|
| Rubric completeness | `pytest scripts/tests/test_rubric_completeness.py -q` | red before the fill, green after |
| Regression suite | `pytest scripts/tests/ -q` | green (pre-commit gate) |
| GCL runner loads the skill | `python3 scripts/gcl_runner.py --skill aws-aurora-ops --print-critic` | renders Critic prompt incl. the skill's Hard rules |
| GCL loop | Generator (agent) → blind Critic (isolated subagent) → §5 verdict | `PASS`, trace persisted to `audit-results/` |
| CLI namespace | `python3 -c "from scripts._gen_rubric import _aws_cli_svc; print(_aws_cli_svc('aws-aurora-ops'))"` | `rds` |

## Round 2 — Critic findings applied

Two isolated Critic subagents (`reviewer`, no user request, read-only) audited
the round-1 artifact. Applied fixes:

| # | Finding (critic) | Fix |
|---|---|---|
| 1 | `delete-global-cluster` precondition misstated: the auto-fail only demanded that non-primary members be detached | `rubric.md` now requires an empty `GlobalClusterMembers` list — every member, primary included, must be detached first; the `remove-from-global-cluster` row no longer claims the primary is ineligible |
| 2 | Changelog row claimed the `## Loop parameters` heading was "restored" in the rubric, which was false (HEAD already had it; the defect was in the generator template) | row reworded to describe only the fill + the CLI namespace |
| 3 | AIOps delegate contract (`aiops_delegate`, `trace_id` propagation, 24 h `idempotency_key` dedupe) had no scored row and no auto-fail | ops-table row + three auto-fail bullets (MANUAL write / AUTO_HEAL destructive without token; missing `trace_id`/`aiops_context`; duplicate `idempotency_key` inside the TTL) |
| 4 | `prompt-templates.md` Confirmation Strings table was a strict subset of the tokens the rubric now enforces | added the backtrack and writer-delete tokens + a `1.3.0` row |
| 5 | `_gen_rubric.py` overwrote a filled rubric without warning | `--force` guard (see Decision) + regression test |
| 6 | Plan slice 1 mis-attributed the stale `mirrors scripts/gcl_runner.py` comment to `_gen_rubric.py` | the comment lives in `_sync_prompt_skeletons.py:42`; plan wording corrected |

Rejected, with evidence: the claim that a rubric-side `1.0.1` row contradicts
repo convention — `aws-athena-ops/references/rubric.md:75` and
`aws-eks-ops/references/rubric.md:61` both carry revision rows.

Open, not fixed (pre-existing, repo-wide): rubrics embed `{{user.*}}`
placeholders (`aws-aurora-ops/references/rubric.md` password/ACL/region rows)
even though the rubric text is passed to the Critic; the sibling
`aws-rds-ops` / `aws-iam-ops` / `aws-kms-ops` rubrics do the same, so this is
a `gcl-spec.md` §7.1 question for the whole repo, not this change.

**Verification limits.** `docs.aws.amazon.com` is unreachable from this
environment (`read` → certificate verification error; `web_search` → all
providers failed), so the Global Database preconditions are aligned to the
API precondition asserted by the Critic plus the conservative reading, and
were not re-checked against the live AWS reference. Flagged for human review.
