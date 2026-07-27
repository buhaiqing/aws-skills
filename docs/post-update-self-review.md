# Post-Update Self-Review Audit Template

> **Version**: 1.0.0
> **Date**: 2026-07-27
> **Scope**: Global 3-round self-review template for all aws-skills skill changes
> **Rounds**: R1 Structural · R2 Content · R3 Cross-cutting + Lessons Learned

---

## Usage

Copy this file as a working document when auditing a skill update.
After each round, record results and any fixes applied.
Only report `[OK]` after all 3 rounds pass cleanly.

---

## Round Tracking

```raw
> R1: ⏳ PENDING
> R2: ⏳ PENDING
> R3: ⏳ PENDING
```

---

## R1: Structural Review

### C1–C6 (Charter Compliance)

| Check | Result | Evidence |
|-------|--------|----------|
| C1: YAML Frontmatter | ⏳ | name, description, license, compatibility, metadata present |
| C2: SHOULD/SHOULD NOT | ⏳ | `### SHOULD Use When` + `### SHOULD NOT Use When` present |
| C3: Trigger & Scope | ⏳ | `## Trigger & Scope` with product/service keywords |
| C4: Variable Convention | ⏳ | `## Variable Convention` table with `{{env.*}}`, `{{user.*}}`, `{{output.*}}` |
| C5: Safety Gates | ⏳ | Safety gates for all destructive ops (delete, terminate, detach, revoke) |
| C6: Token Efficiency | ⏳ | TE-1…TE-6 section present; **MUST PASS** |

### TE-1–TE-6 Verification

| Rule | Check | Result |
|------|-------|--------|
| TE-1 | No hardcoded quota/port/version tables; uses API/CLI instead | ⏳ |
| TE-2 | No docstrings in boto3 SDK code; inline comments only | ⏳ |
| TE-3 | Compact error tables (≤3 cols, ≤40 lines) | ⏳ |
| TE-4 | JSON paths centralized at file top | ⏳ |
| TE-5 | YAML anchors in example-config.yaml | ⏳ |
| TE-6 | No duplicate "Complete Workflow" across SKILL.md + references/ | ⏳ |

### Frontmatter Parsing

| Check | Result |
|-------|--------|
| Single `---` open + close (no stray `---` mid-block) | ⏳ |
| `environment` includes all required vars | ⏳ |
| `cross_skill_deps` dirs all exist in repo | ⏳ |
| `gcl.*` fields consistent (pilot/class) | ⏳ |

### Delegation References

| Reference | Target Directory | Exists? |
|-----------|-----------------|---------|
| `aws-...-ops` (SHOULD/SHOULD NOT) | `aws-...-ops/` | ⏳ |

### Destructive Ops Confirmation

| Op | Has Confirmation? |
|----|-------------------|
| delete | ⏳ |
| terminate | ⏳ |
| detach | ⏳ |
| revoke | ⏳ |

---

## R2: Content Review

### Link Integrity

| Link | Type | Status |
|------|------|--------|
| `references/aws-cli-usage.md` | local relative | ⏳ |
| `references/boto3-sdk-usage.md` | local relative | ⏳ |
| `references/core-concepts.md` | local relative | ⏳ |
| `references/troubleshooting.md` | local relative | ⏳ |
| `references/rubric.md` | local relative | ⏳ (GCL skills) |
| `references/prompt-templates.md` | local relative | ⏳ (GCL skills) |

### CLI Fidelity

| Check | Status |
|-------|--------|
| Commands use `--output json` (not `aws --output json`) | ⏳ |
| Dual-path documented (CLI primary + boto3 fallback) | ⏳ |
| boto3 fallback after 3 CLI failures | ⏳ |

### Safety Gates

| Op | Safety Gate? |
|----|-------------|
| delete | ⏳ |
| terminate | ⏳ |
| detach | ⏳ |
| revoke | ⏳ |

### TODO / FIXME Scan

| File | TODOs? |
|------|--------|
| `SKILL.md` | ⏳ |
| `references/aws-cli-usage.md` | ⏳ |
| `references/boto3-sdk-usage.md` | ⏳ |
| `references/core-concepts.md` | ⏳ |
| `references/troubleshooting.md` | ⏳ |

### README Sync

| Check | Status |
|-------|--------|
| `README.md` version matches SKILL.md frontmatter | ⏳ |
| `README_cn.md` version matches SKILL.md frontmatter | ⏳ |
| Skills table includes this skill | ⏳ |

---

## R3: Cross-cutting + Lessons Learned

### CADL / AGENTS.md Consistency

| Check | Status |
|-------|--------|
| No violation of §12 CodeGraph split gate (code→CodeGraph, docs→Grep) | ⏳ |
| No violation of §14 TE hard gate (SKILL.md ≤ 120 lines) | ⏳ |
| GCL Per-Skill Defaults table (§11.5) updated if GCL class changed | ⏳ |
| Cross-skill delegation refs still valid after change | ⏳ |

### Token Efficiency Audit

| Check | Status |
|-------|--------|
| No duplicated content across SKILL.md + references/ | ⏳ |
| No hardcoded version/port/state tables (TE-1) | ⏳ |
| No boto3 docstrings (TE-2) | ⏳ |
| Error tables compact ≤40 lines (TE-3) | ⏳ |
| JSON paths declared once at top (TE-4) | ⏳ |
| YAML anchors used in assets/ (TE-5) | ⏳ |

### Lessons Learned (required for P0 completions)

| # | Lesson | Category | Action |
|---|--------|----------|--------|
| 1 | | | |

> **Categories**: `pitfall` | `pattern` | `convention` | `tool-choice` | `repo-fact`
> **Fill in at least 1 lesson for every P0 task** — these feed `docs/failure-patterns.md` and `.omc/conventions.json`.

---

## Verdict

```
[⏳] <skill> v<version> — N rounds clean / N issues remaining
```

| Round | Checks Passed | Status |
|-------|--------------|--------|
| R1 (Structural) | C1–C6 ✅, TE-1–TE-6 ✅, Frontmatter ✅, Delegation ✅, Safety Gates ✅ | ⏳ |
| R2 (Content) | Links ✅, CLI ✅, Safety ✅, No TODOs ✅, README Sync ✅ | ⏳ |
| R3 (Cross-cutting) | CADL ✅, TE Audit ✅, Lessons Learned ✅ | ⏳ |

---

## Version History

| From | To | Date | Description |
|------|----|------|-------------|
| | 1.0.0 | 2026-07-27 | Created global template with 3-round structure (R1 Structural, R2 Content, R3 Cross-cutting + Lessons Learned) |
