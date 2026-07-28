# TE Gate C6 Debt Remediation — Pilot Design

- **Date**: 2026-07-28
- **Status**: Approved for P0-A pilot (2 skills)
- **Scope**: `scripts/te_gate.py` + 2 pilot skills (`aws-cloudwatch-ops`, `aws-ram-ops`)
- **Out of scope**: 35 remaining skills (handled in P0-B after pilot validates the pattern)

## Problem

`python3 scripts/te_gate.py --all --strict` exits 1 for all 37 skills. The
Maturity Model §5.1 advertises "TE Hard Gate ✅", but the executable gate
contradicts the documentation. Two distinct failure modes are present:

1. **G1 (line count)**: every `aws-*-ops/SKILL.md` exceeds 120 lines. Worst
   offenders: `aws-ec2-ops` 1064, `aws-cloudtrail-ops` 787, `aws-dynamodb-ops`
   783, `aws-ram-ops` 666, `aws-waf-ops` 564.
2. **G3 (Common JSON Paths)**: ~30/37 skills either have no `Common JSON Paths`
   header or have a header whose content does not match the regex used by
   `te_gate.py`. Real causes are two-fold:
   - Tooling: `JSON_PATH_LINE_RE` requires `key = .path` shape; many skills
     use `# Header: .path.{key1,key2}` (curly brace expansion) or
     `key1 → .path1; key2 → .path2` (multi-path on one line).
   - Duplication: a few skills re-declare paths in body, which is what the
     G3 body-check is actually meant to catch.

Other TE gates (G2 / G5 / G6) are LLM-/human-judged and intentionally not
machine-checked by `te_gate.py` — they are not in scope.

## Goals

1. Make `te_gate.py --all --strict` exit 0 for the 2 pilot skills.
2. Establish a reusable split pattern (`SKILL.md` ≈ index + Operations Detail
   in `references/operations.md`) so P0-B can apply it to the remaining 35
   skills without re-discovering the rules.
3. Tighten `te_gate.py` regex to accept the project's existing
   human-friendly patterns (`# Label: .path.{...}` and `;`-separated multi-path
   lines) **only** when the expansion is unambiguous.
4. Lock the C6 "MUST PASS" status with a CI / lint hook so the gate cannot
   silently drift back to red.

## Non-goals

- Modifying all 37 skills in one PR (this is P0-A pilot only).
- Changing the frontmatter schema or skill structure.
- Touching Charter / TE semantics (line caps, G1–G6 definitions).
- Adding new TE gates (G2 / G5 / G6 are still LLM-judged).

## Design

### Pilot A — `aws-cloudwatch-ops` (light-touch)

The file is 135 lines (15 over the G1 cap) and already follows the
"Operations Index → references/" pattern — only the G3 header format is
non-compliant.

- **G1 fix**: trim the `## Reference Files` index to a single line per
  reference (currently multi-line list). Already-structured operations
  index stays.
- **G3 fix**: reformat the `## Common JSON Paths` block so each line matches
  `JSON_PATH_LINE_RE` (one path per line, `key = .path` shape). Multi-path
  expressions split into separate lines.

No new reference files are required for this pilot.

### Pilot B — `aws-ram-ops` (heavy-touch)

The file is 666 lines (546 over the cap). The body contains 14 explicit
"Operation: …" blocks (Pre-flight → Execute → Validate → Recover), each
~25 lines, plus 4 destructive-op confirmation templates.

- **G1 fix**: extract the per-operation blocks into a new
  `references/operations.md` (target ~250 lines). Keep in `SKILL.md`:
  - Frontmatter
  - `## Common JSON Paths` (reformatted)
  - One-line summary of the operation list (table referencing the new file)
  - `## Trigger & Scope` (SHOULD / SHOULD NOT)
  - `## Variable Convention` (compressed to the essentials)
  - `## Execution Flow Pattern` (one-line summary + link to `operations.md`)
  - `## Safety Gates` (kept inline — these are the Skeleton-confirmation
    patterns agents must scan, not operation detail)
  - `## Token Efficiency` (one-line summary)
  - `## Reference Files` (index)
  - `## Quality Gate (GCL)`
  - `## AIOps Delegate Contract` (Recognition + Behavior rules + Cross-ref)

- **G3 fix**: same pattern as Pilot A — reformat `## Common JSON Paths`
  to one-path-per-line.

### `te_gate.py` tightening

The regex will be extended to also accept:

- Comment-prefixed entries (`# Label: .path.{...}`), where the label comes
  from the colon-prefixed portion and the path from the dot-prefixed portion.
- Multi-path lines split on `;` / `→` so each substring is parsed independently.

Tightening is guarded by new unit tests in `scripts/tests/test_te_gate.py`
(to be added in this pilot). Old tests must be preserved — no behavior
regression for already-passing skills.

### Pilot outcome — what we will and will not promise

- Will fix: 2 pilot skills → `te_gate` green; `te_gate.py` regex more
  forgiving; `references/operations.md` proved out as a split target.
- Will not fix: 35 remaining skills. They will be triaged into three
  buckets in the P0-B plan (light / medium / heavy), but implementation is
  out of scope for this pilot.

### CI / lint hook

The pilot does not add a new hook — it relies on the existing
`scripts/hooks/pre-commit` (already shipped). P0-B will wire
`te_gate.py --all --strict` into the pre-commit hook unconditionally.

## Acceptance Criteria

| ID | Gate | Verification |
|---|---|---|
| A1 | `python3 scripts/te_gate.py aws-cloudwatch-ops --strict` exits 0 | re-run after Pilot A |
| A2 | `python3 scripts/te_gate.py aws-ram-ops --strict` exits 0 | re-run after Pilot B |
| A3 | `aws-cloudwatch-ops/SKILL.md` ≤ 120 lines | `wc -l` |
| A4 | `aws-ram-ops/SKILL.md` ≤ 120 lines | `wc -l` |
| A5 | `aws-ram-ops/references/operations.md` exists and contains the 14 operation blocks that were in `SKILL.md` | grep |
| A6 | `scripts/tests/test_te_gate.py` covers the new regex acceptances (≥ 3 tests) | pytest |
| A7 | `python3 -m pytest -p no:rerunfailures scripts/tests/ -q` all green | pytest |
| A8 | `ruff check .` clean | ruff |
| A9 | `python3 scripts/composite_lint.py lint --all` exit 0 | composite_lint |
| A10 | `python3 scripts/cross_runtime_lint.py lint --all --json` min score 1.0 | cross_runtime_lint |
| A11 | `python3 scripts/self_review.py verify` `stale_p0=0` | self_review |

## Risks

- **Regex doubling as parser**: extending `JSON_PATH_LINE_RE` to accept
  `# Label: .path.{...}` is a heuristic. Ambiguous labels (e.g. labels that
  contain `=`) could mis-parse. Mitigation: tests cover the labelled /
  multi-path cases explicitly; if a label contains `=`, fall back to the
  previous strict match.
- **SKILL.md content drift**: pulling operation detail out of `SKILL.md`
  risks losing the "must read this to render correctly" coupling. Mitigation:
  the `## Operations Index` table links directly to each anchor in
  `references/operations.md`, and the latter is reachable in 1 hop from
  every reference listed in `SKILL.md`.
- **Pilot is partial**: 2/37 skills green could still let the repo claim
  "TE Hard Gate ✅" while 35 skills remain red. Mitigation: the pilot
  report explicitly states the 2/37 number, and P0-B is queued behind it
  with its own spec.

## Token Budget

Pilot targets net +200 lines (operations.md extraction is +250, G3 / index
trim is −50, plus a small test file). Test additions: ≤ 60 lines.

## Out-of-band

The P0-A pilot does not touch `audiences-of-record` issues (frontmatter
schema, env var convention, etc.) — those are owned by separate P0 / P1
workstreams.
