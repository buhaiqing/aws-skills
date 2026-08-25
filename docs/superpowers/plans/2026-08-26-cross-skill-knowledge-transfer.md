# Plan: Cross-Skill Knowledge Transfer (P1)

Spec: [`docs/superpowers/specs/2026-08-26-cross-skill-knowledge-transfer-design.md`](../specs/2026-08-26-cross-skill-knowledge-transfer-design.md)

## P1a — Module + Tests (DONE 2026-08-26)

- [x] `scripts/cross_skill_transfer.py`: TransferCandidate / load_skill_deps / harvest_transfer_candidates / gcl_gate_transfer / report / CLI(--apply atomic)
- [x] `scripts/tests/test_cross_skill_transfer.py`: 14 tests
  - [x] unit: deps 解析（容错/缺目录/self-ref 忽略）
  - [x] unit: harvest 方向（source→dependents）/ dedup / 空行跳过
  - [x] unit: critic gate（min_evidence / self-transfer / 泛化 2×）/ report
  - [x] Hypothesis: gate 永不接受 evidence < min_evidence（fuzzed）
  - [x] Hypothesis: harvest 无重复 (source,target,fact) 三元组
- [x] ruff clean

## P1b — Telemetry 关联 (pending)

- [ ] telemetry_dashboard: 新增 cross-skill section（accepted 按 target 聚合）
- [ ] 验证: `python3 scripts/telemetry_dashboard.py` 输出含 cross-skill 行

## P1c — 季度 Review 钩子 (pending)

- [ ] accepted candidates 抽样 → golden scenario 候选清单
- [ ] 验证: 季度 review checklist 引用 audit-results/cross-skill-transfer.json
