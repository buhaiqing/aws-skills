# Cross-Skill Knowledge Transfer — Design Spec

> **Purpose**: L4 Gap 5 — 37 个 skill 目前各自孤立学习。`aws-ec2-ops` 收割到的
> 经验（failure-patterns.md 行）永远不会传到依赖它的 skill。本设计让经验沿
> `cross_skill_deps` 依赖边**下游流动**，并用对抗 Critic 门禁（GCL 映射）阻止
> 弱信号/泛化事实污染目标 skill。
- **创建日期**: 2026-08-26
- **关联**: `docs/agentic-maturity-model.md` Gap 5 · ADR-0001 M4 (governed_learning)
- **状态**: Implemented (P1a)

## 1. Problem

每个 skill 独立运行、独立收割失败经验。复合 skill（aiops-cruise 等）做 RCA 时
拿不到上游 skill 的教训 → RCA 质量受限。cross_skill_deps 目前只是声明，不承载
知识。

## 2. GCL Mapping

| GCL 角色 | 实现 |
|---|---|
| Generator | `harvest_transfer_candidates`: 对每条 failure-pattern 行，向**所有声明依赖 source skill 的 skill** 提议同一事实；dedup key `(source, target, fact)` |
| Critic | `gcl_gate_transfer`: 对抗门禁 — self-transfer 拒绝；`evidence_count < min_evidence(=2)` 拒绝；泛化事实（命中 GENERIC_BLOCKLIST={"rate limit","throttling","timeout"}）需 ≥2× min_evidence |
| Termination | 每个 candidate 终态 ∈ {accepted, rejected}，无循环 |

## 3. Contract（单一信源，实现 = `scripts/cross_skill_transfer.py`）

```python
@dataclass
class TransferCandidate:
    source_skill: str; target_skill: str; fact: str
    evidence_count: int
    source_refs: list[str]
    status: str = "pending"   # pending|accepted|rejected

load_skill_deps(repo_root) -> dict[str, list[str]]   # 容错解析 SKILL.md 的 cross_skill_deps
harvest_transfer_candidates(repo_root, patterns) -> list[TransferCandidate]
gcl_gate_transfer(candidate, *, min_evidence=2) -> TransferCandidate
report(candidates) -> {total, accepted, rejected, acceptance_rate}
```

CLI: `python3 scripts/cross_skill_transfer.py harvest [--patterns P] [--min-evidence N] [--apply]`。
`--apply` 原子写（tmp+rename）到 `audit-results/cross-skill-transfer.json`。

fact 归一化：`f"{command}: {fix or root_cause}"`。

## 4. Rollout

- **P1a** (本 spec): module + tests（14 tests，含 2 Hypothesis property）— DONE
- **P1b**: telemetry_dashboard 增加跨 skill 相关性视图（accepted candidates 按 target skill 聚合）
- **P1c**: 季度 review 钩子 — accepted candidates 抽样进 golden scenario 候选

## 5. Risks

| 风险 | 缓解 |
|---|---|
| 事实漂移（源 skill 行为已变） | evidence_count 门槛 + 季度 review (P1c) |
| 重复刷屏 | dedup key (source,target,fact) + Hypothesis property 断言 |
| 泛化事实无信息量 | GENERIC_BLOCKLIST 需 2× 证据 |

## 6. Verification

```bash
python3 -m pytest scripts/tests/test_cross_skill_transfer.py -q   # 14 passed
python3 scripts/cross_skill_transfer.py harvest                    # JSON report
```
