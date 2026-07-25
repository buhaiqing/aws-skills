# FinOps 扩展任务 F4–F7 设计文档

- **日期**: 2026-07-25
- **状态**: 已定稿
- **范围**: 在 F1–F3 基础上扩展 4 项 FinOps 优化能力，本次重点实现 F-7（暴露真实差距）。
- **关联**: `docs/superpowers/specs/2026-07-19-finsecops-optimization-design.md`（F1–F3 定义）

## 1. 背景与已核实现状

| 维度 | 现状 | 证据 |
|------|------|------|
| FinOps 复合技能 | `aws-finops-core` v1.0.0（composite，delegate 6 个 L1） | `aws-finops-core/SKILL.md` |
| 闲置检测规则 | 5 类（ALB/EBS/Snapshot/Lambda/RDS）+ ECS 3 类 | `references/idle-detection-rules.md` (125 行) |
| RI/SP 覆盖率 | 有查询命令 + 阈值表，**无分析引擎** | `references/reserved-coverage.md` (42 行) |
| 标签合规 | 有 4 个必选标签 + 合规率公式，**无自动化脚本** | `references/tag-compliance.md` (64 行) |
| 预算告警 | 有文档，**无自动化** | `references/budget-alerts.md` |
| 成本异常检测 | 有 7 天基线 + 阈值，**无推理规则接入 AIOps** | `references/anomaly-detection.md` |
| 差距诊断 | **完全缺失** — 无工具可度量 FinOps 能力的真实覆盖与缺口 | 全仓库 grep `finops_gap\|gap_audit` = 0 |

**核心矛盾**: FinOps 文档覆盖较全（8 个 reference 文件），但**无自动化诊断工具**来度量"文档声称的能力 vs 实际落地"之间的真实差距。

## 2. F4–F7 优化机会

| # | 机会 | 现状缺口 | 建议落点 | 优先级 |
|---|------|----------|----------|--------|
| F4 | **标签合规自动化审计** | tag-compliance.md 有公式无脚本；无定期审计机制 | `scripts/finops_tag_audit.py`：扫描资源标签 → 计算合规率 → 输出报告 | P2 |
| F5 | **RI/SP 覆盖率优化引擎** | reserved-coverage.md 有查询无分析；无购买/续费建议生成 | `scripts/finops_ri_sp_analysis.py`：拉取覆盖率 → 对比阈值 → 输出建议 | P2 |
| F6 | **预算与告警自动化** | budget-alerts.md 有文档无自动化；无预算创建/告警规则 setup | `scripts/finops_budget_setup.py`：创建预算 → 配置告警 → 验证 | P3 |
| F7 | **暴露真实差距（Gap Exposure）** | **完全缺失** — 无工具可诊断 FinOps 能力的真实覆盖与缺口 | `scripts/finops_gap_audit.py`：多维度审计 → 结构化差距报告（JSON + Markdown） | **P1** |

## 3. F-7 详细设计（本次实现）

### 3.1 目标

创建一个**FinOps 能力差距诊断工具**，自动度量以下维度的真实差距：

1. **能力覆盖差距**: SKILL.md 声称的 `provides` vs 实际有 reference 实现的能力
2. **路由差距**: FinOps 能力在 orchestrator/cruise 中的路由覆盖
3. **自动化差距**: 有文档但无脚本的能力
4. **测试差距**: 有脚本但无测试的能力
5. **推理规则差距**: AIOps 推理规则中 FinOps 相关规则的覆盖

### 3.2 审计维度

| 维度 | 数据源 | 判定逻辑 |
|------|--------|----------|
| **D1: 能力声明 vs 实现** | `aws-finops-core/SKILL.md` frontmatter `provides` vs `references/` 文件 | provides 中每项是否有对应 reference 文件 |
| **D2: 路由覆盖** | `aws-aiops-orchestrator/SKILL.md` + `aws-aiops-cruise/SKILL.md` 中 `aws-finops-core` 引用 | FinOps 能力是否被 AIOps 路由 |
| **D3: 自动化覆盖** | `scripts/finops_*.py` 存在性 | 每个 FinOps 能力是否有自动化脚本 |
| **D4: 测试覆盖** | `tests/` 目录中 FinOps 相关测试 | 每个脚本是否有对应测试 |
| **D5: 推理规则覆盖** | `_inference.py` 中 `COST-*` 规则 | 成本异常是否接入推理引擎 |

### 3.3 输出格式

```json
{
  "audit_date": "2026-07-25T...",
  "dimensions": {
    "D1_capability_coverage": {"score": 0.75, "gaps": [...]},
    "D2_routing_coverage": {"score": 0.50, "gaps": [...]},
    "D3_automation_coverage": {"score": 0.25, "gaps": [...]},
    "D4_test_coverage": {"score": 0.00, "gaps": [...]},
    "D5_inference_coverage": {"score": 0.00, "gaps": [...]}
  },
  "overall_score": 0.30,
  "verdict": "FAIL"
}
```

### 3.4 验收标准

| 验收项 | 标准 |
|--------|------|
| 脚本可运行 | `python3 scripts/finops_gap_audit.py` 输出结构化报告 |
| 5 维度覆盖 | D1–D5 均有评分和差距列表 |
| JSON + Markdown 双输出 | `--format json` / `--format md` 均支持 |
| 退出码 | 有差距 → exit 1；全覆盖 → exit 0 |
| 测试 | ≥ 5 个单测覆盖各维度 |

## 4. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 审计维度遗漏 | 5 维度覆盖能力/路由/自动化/测试/推理，可后续扩展 D6+ |
| 误报（false positive） | 判定逻辑基于文件存在性 + grep，非语义推断 |
| 与现有 audit_inference_coverage.py 重复 | 本工具聚焦 FinOps 全景，inference 审计仅为其 D5 子集 |
