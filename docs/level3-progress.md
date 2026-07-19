# Level 3 关联覆盖盲区补全 — 进度文档

- **设计文档**: `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`
- **创建日期**: 2026-07-11
- **总目标**: 补全 8 个未接入技能（athena/cloudfront/dynamodb/eks/elasticache/opensearch/ram/secretsmanager）的委托路由 + inference rules，分 3 期迭代，每期 GCL 评审。

## 关键事实校准（实施中发现）

复核 HEAD 原始 `_inference.py` 后确认：
- 路由元数据表（cruise/orchestrator SKILL.md）对 8 个技能全部缺席 → **路由表全补（真实缺口）**。
- inference 检测代码在 HEAD 已覆盖：DYNAMO-THROTTLE-01、EC-MEM-01（及 EC-CPU/CONN/EVICT）、大量 CF-*、RDS-*、Aurora-* 等。
- **真正缺失的 inference 规则**：DYNAMO-GSI-01、EC-FAILOVER-01、OpenSearch 全段（OS-HEAP/OS-SHARD）、EKS 全段、Athena、RAM、SecretsManager。

因此每期工作量调整为"路由全补 + 仅补真实缺失的 inference 代码"，不重复实现已有规则。

## 分期总览

| 期 | 技能 | 状态 | GCL 轮次 | 测试结果 |
|----|------|------|----------|----------|
| 期 1 | dynamodb, elasticache, opensearch | ✅ 完成 | 1 (2 Critic 并行) | pytest 45→72 passed |
| 期 2 | eks, cloudfront | ✅ 完成 (EKS 原生 collector；CloudFront 补 CF-ORIGIN-02/CF-CACHE-01) | - | 72 passed |
| 期 3 | athena, ram, secretsmanager | ✅ 完成 (Task #10, 2026-07-19) | 5 Generator 并行 + Monitor OPTIMAL | 72 passed (含 +21) |

> 全部 3 期已收尾。EKS / CloudFront / Athena / RAM / SecretsManager / OpenSearch 的
> inference 规则现均为 live code（各有原生 collector 填充 `signals[<svc>]`）。

## 期 1 详情

- **范围**: 路由全 8 技能 + inference 补 DYNAMO-GSI-01 / EC-FAILOVER-01 / OS-HEAP-01 / OS-SHARD-01
- **改动文件**:
  - `aws-aiops-cruise/SKILL.md`（Cross-Skill References +8 行）
  - `aws-aiops-orchestrator/SKILL.md`（cross_skill_deps +8 行）
  - `aws-aiops-cruise/references/inference-rules-addendum.md`（新建，全 8 技能规则语义 + 实现状态表）
  - `aws-aiops-cruise/runbooks/scripts/_inference.py`（+4 段规则：DYNAMO-GSI-01/EC-FAILOVER-01/OS-HEAP-01/OS-SHARD-01，内联模式，未改动任何现有规则）
  - `aws-aiops-cruise/tests/test_inference_phase1.py`（新建，5 测试）
- **开始**: 2026-07-11　**完成**: 2026-07-11
- **GCL 评审结论**: 2 个 Critic 子 Agent 并行评审，零问题通过
- **测试**: 全量 45 passed（含新增 5）；Generator 自查 Safety/引用存在性/frontmatter 全 PASS
- **说明**: 未重复实现已有规则（DYNAMO-THROTTLE-01/EC-MEM-01/CF-* 均保留 HEAD 原状，仅新增 4 条缺失规则）。

## 期 2 详情

- **范围**: eks + cloudfront 路由已补；CloudFront inference 代码已存在（CF-*），
  EKS inference 代码缺失需新建（EKS-NODE-01/EKS-OOM-01）。
- **落地**: EKS 通过 `audit_eks_nodes` 原生 collector 填充 `signals["EKS"]`，`EKS-NG-02`
  经 `signals["EKS"]` 直接触发；EKS_NODE 层（CloudWatch Container Insights）驱动
  `EKS-NODE-01`/`EKS-OOM-01`。均为 live code。
- **状态**: ✅ 完成（详见期 1 及 addendum）。

## 期 3 详情 (Task #10 — 2026-07-19)

- **范围**: athena + ram + secretsmanager + cloudfront(CF-ORIGIN-02/CF-CACHE-01) + opensearch(OS-HEAP/OS-SHARD)
  共 5 个服务，全部补成 live code。
- **设计/计划**: `docs/superpowers/specs/2026-07-19-level3-phase23-design.md`、
  `docs/superpowers/plans/2026-07-19-level3-phase23.md`
- **落地方式**: 采集器为主（用户确认）—— 每个服务一个只读原生 collector 填充 `signals[<svc>]`，
  `_inference.py` 内联规则消费该 key；无自动写操作（GCL fail-closed）。
- **改动文件**:
  - `collectors/analytics.py` (新) — `audit_athena_cost` → `signals["Athena"]`
  - `collectors/ram_audit.py` (新) — `audit_ram_shares` → `signals["RAM"]`
  - `collectors/secrets_audit.py` (新) — `audit_secrets_rotation` → `signals["SecretsManager"]`
  - `collectors/cloudfront_audit.py` (新) — `audit_cloudfront_signals` → `signals["CloudFront"]`
  - `collectors/search_audit.py` (新) — `audit_opensearch_health` → `signals["OpenSearch"]`
  - `collectors/registry.py` — 5 个 collector 登记 + 通用 2-tuple `signals` 合并分支
  - `runbooks/scripts/_inference.py` — 7 条内联规则 (ATHENA-COST-01 / RAM-SHARE-01 /
    SEC-ROTATE-01 / CF-ORIGIN-02 / CF-CACHE-01 / OS-HEAP-01 / OS-SHARD-01)
  - `tests/test_inference_phase23.py` (新) — 21 个合成信号测试（命中/不命中边界 + 非回归）
  - `references/inference-rules-addendum.md` — 修正自相矛盾表格（原既标"exists"又标"deferred"），
    5 服务统一标 ✅ live
- **执行纪律**: 5 个 Generator 子 Agent 并行（各写独立新文件，零并发冲突）→ 主 Agent 串行
  stitch `_inference.py` + `registry.py` → Token Efficiency Monitor 判 **OPTIMAL** → §12 split
  （codegraph 校验调用图 + grep 校验 5 个 `aws-<svc>-ops` 目录真实存在）→
  安全门禁（grep 确认无 mutate 调用）→ 72 tests 零 regression。
- **开始**: 2026-07-19　**完成**: 2026-07-19
- **Commits**: `ea540b1` (code) + `b1ac958` (docs) + `195c022` (关闭 RESUME 文档)
- **测试**: 全量 72 passed（51 预存 + 21 新增）；ruff 全绿。
- **推送**: 已 push 至 `origin/main` (`f5d8900..195c022`)。

## 收尾结论

Level 3 关联覆盖盲区补全（设计文档 2026-07-11）全部 3 期完成。8 个技能
（athena/cloudfront/dynamodb/eks/elasticache/opensearch/ram/secretsmanager）的委托路由 +
inference rules 均已 live，对应 `aws-<svc>-ops` 技能可被委托。`docs/RESUME-2026-07-19.md`
已删除。
