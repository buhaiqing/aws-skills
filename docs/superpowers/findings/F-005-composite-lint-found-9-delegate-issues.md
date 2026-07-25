---
id: F-005
severity: P2
title: composite lint discovered 9 unresolved delegate operations
status: fixed
added: 2026-07-26
closed: 2026-07-26
phase: p0-closure
---

## Root cause

`scripts/composite_lint.py` (P0 closure deliverable) ran on the actual repo
and found that `aws-security-copilot` declares 9 operations on base skills
that those base skills do NOT declare in their `metadata.provides:` or
`delegate.accepts:`:

- aws-guardduty-ops: list-findings, get-findings
- aws-securityhub-ops: get-findings, get-insights
- aws-config-ops: get-compliance-summary
- aws-iam-ops: access-analyzer-findings
- aws-secretsmanager-ops: list-secrets
- aws-kms-ops: list-keys
- aws-cloudtrail-ops: lookup-events

The CI gate (`composite-gate + setup-hooks` workflow) is **fail-closed** —
PR merge will be blocked until these are resolved. This is correct gate
behavior, but reveals **real cross-skill metadata drift** that was hidden
under the previous "L4 = 100%" claim.

## Fix

✅ **Fixed 2026-07-26**: Added `type: base` + `provides:` block to 7 base skills (`aws-guardduty-ops`, `aws-securityhub-ops`, `aws-config-ops`, `aws-iam-ops`, `aws-secretsmanager-ops`, `aws-kms-ops`, `aws-cloudtrail-ops`). Total 9 ops declared. `composite_lint --all` now exits 0.

Original fix plan (for reference):

For each base skill, add the missing operations to `metadata.provides:`
(or extend `metadata.delegate.accepts:` if not the canonical provider).

E.g. for `aws-guardduty-ops/SKILL.md`:
```yaml
metadata:
  type: base
  provides:
  - list-findings
  - get-findings
  # ... existing ops
```

After fixing, re-run `python3 scripts/composite_lint.py lint --all`
should return all composites with score=1.0.

## Lesson

1. **Lint 工具的价值在第一次真跑时显现** — 测试只能验证 lint 行为正确,
   真实发现藏在实际数据中
2. **L4 "100%" 是 scripts/ 完整度, 不是 metadata 完整度** — metadata 一致性
   是 P0 closure 才浮出水面的新维度
3. **CI fail-closed 是 feature, 不是 bug** — 应该保留, 不要降级为 warn
