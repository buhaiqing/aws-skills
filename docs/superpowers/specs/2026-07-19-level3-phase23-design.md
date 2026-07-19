# Level 3 关联覆盖 — Phase-2/3 收尾设计（Task #10）

- **日期**: 2026-07-19
- **状态**: 草稿（待用户确认后执行）
- **父设计**: `docs/superpowers/specs/2026-07-11-level3-coverage-design.md`
- **落地方式**: 采集器为主（用户确认）

## 1. 背景与现状复核（基于磁盘源码，非记忆）

对 `_inference.py` 全部 `rule = "..."` 赋值点的 grep 复核结果：

**已 live 的规则（Phase-1 已落地）**：
ALB-EC2, RDS-CONN/LAT, AURORA-*, CW-ALARM, DG-INSIGHT, XRAY-FAULT,
EKS-NG/NODE/OOM, NAT-PORT, NLB-TRAFFIC, EC-CPU/MEM/CONN, EC2-MEM/IO/NET,
LAMBDA-THROTTLE, APIGW-5XX, DYNAMO-THROTTLE/GSI, CACHE-EVICT, WAF-ALB, EC-FAILOVER。

**deferred（addendum 标 "to be added" 但未在代码中实现）**：
- `ATHENA-COST-01`（Athena 查询成本异常）
- `RAM-SHARE-01`（RAM 资源共享状态异常）
- `SEC-ROTATE-01`（SecretsManager 轮转过期）
- `CF-ORIGIN-02` / `CF-CACHE-01`（CloudFront 源站延迟 / 缓存命中率）
- `OS-HEAP-01` / `OS-SHARD-01`（OpenSearch 堆压力 / 分片不均）

> addendum 表格自相矛盾（同一行既写 "✅ exists" 又写 "⏳ deferred"）。
> 代码复核是权威：上述 5 个服务（Athena/RAM/SecretsManager/CloudFront/OpenSearch）
> 的 inference 规则在 `_inference.py` 中**均未实现**，属于真正的"死代码"缺口。
> CloudFront 的 `audit_cloudfront` 采集器已存在但只发 `CF-EDGE-01`/`CF-ORIGIN-01`（不同 ID/阈值），
> 不覆盖 `CF-ORIGIN-02`/`CF-CACHE-01`。

## 2. 目标与范围

**目标**：把 5 个服务的 deferred inference 规则补成 live code，使
`signals[<svc>]` 在运行时被真实填充、规则可触发。沿用现有内联模式
（不另起 `detect_*` 函数），保持 fail-closed（只检测+推荐+委托，绝不自动写操作）。

**范围（外科手术式）**：
- **改 / 新增采集器**：
  - `collectors/edge.py`：`audit_cloudfront` 增补 `CF-ORIGIN-02`（OriginLatency>1000 OR OriginSuccessRate<0.99）、`CF-CACHE-01`（CacheHitRate<0.8）；新增 `audit_cloudfront_signals()` 填充 `signals["CloudFront"]`。
  - `collectors/analytics.py`（新建）：`audit_athena_cost()` 填充 `signals["Athena"]`（Athena 查询 ProcessedBytes/QuerySucceeded per WorkGroup + 长耗时检测）。
  - `collectors/governance.py`：新增 `audit_ram_shares()` 填充 `signals["RAM"]`；新增 `audit_secrets_rotation()` 填充 `signals["SecretsManager"]`。
  - `collectors/data.py` 或新建 `collectors/search.py`：`audit_opensearch_health()` 填充 `signals["OpenSearch"]`（JVMMemoryPressure / ClusterIndexWritesBlocked / UnassignedShards）。
- **改 `_inference.py`**：在 `apply_chain_inference()` 内新增 5 段内联规则（消费对应 `signals` key）。
- **改 `collectors/registry.py`**：登记新采集器到 `collect_aws_native_insights()`。
- **改 `aws-aiops-cruise/runbooks/scripts/_shared.py`**：为 Athena / OpenSearch 增加 PRODUCTS 条目（metric 型可直接由 `parallel_metric_scan` 填充；但本次统一走采集器以确保语义准确，PRODUCTS 仅作为库存计数保留可选）。
- **改 `references/inference-rules-addendum.md`**：修正自相矛盾的表格，标注 5 条规则已实现。
- **新增测试**：`tests/test_inference_phase23.py`，合成 signals 验证 5 条规则命中/不命中边界。

**不改**：感知层 Perceive Agent、现有 live 规则、各 `aws-<svc>-ops` 技能自身、路由元数据表（Phase-1 已补 8 行，本次不重复）。

## 3. 逐服务落地方案（采集器为主）

| 服务 | 规则 | 触发信号 | 采集器 | signals key | 判定 |
|------|------|----------|----------|-------------|------|
| Athena | `ATHENA-COST-01` | `AWS/Athena` 命名空间，维度 `WorkGroup`：`ProcessedBytes` 异常 / `QuerySucceeded` 下降 / `QueryExecutionTime`(describe) > 600s | `audit_athena_cost` | `Athena` | 单查询 bytes 异常增或耗时>600s → WARNING/CRITICAL |
| RAM | `RAM-SHARE-01` | `ram list-permissions` / `get-resource-share-invitation`：ShareStatus != ACTIVE 或关联被拒 | `audit_ram_shares` | `RAM` | 状态非 ACTIVE → WARNING |
| SecretsManager | `SEC-ROTATE-01` | `secretsmanager describe-secret` → `LastRotated` age > 90d | `audit_secrets_rotation` | `SecretsManager` | age>90d → WARNING，>180d → CRITICAL |
| CloudFront | `CF-ORIGIN-02` | `AWS/CloudFront` OriginLatency>1000ms OR OriginSuccessRate<0.99 | `audit_cloudfront`（增补）| `CloudFront` | 命中 → WARNING/CRITICAL |
| CloudFront | `CF-CACHE-01` | `AWS/CloudFront` CacheHitRate<0.8 | `audit_cloudfront`（增补）| `CloudFront` | 命中 → WARNING |
| OpenSearch | `OS-HEAP-01` | `AWS/ES` JVMMemoryPressure>=80（>=95 CRITICAL）| `audit_opensearch_health` | `OpenSearch` | 命中 → WARNING/CRITICAL |
| OpenSearch | `OS-SHARD-01` | `AWS/ES` ClusterIndexWritesBlocked=true OR UnassignedShards>0 | `audit_opensearch_health` | `OpenSearch` | 命中 → CRITICAL |

> 注：OpenSearch 维度为 `DomainName`（region-scoped）。Athena 维度为 `WorkGroup`（us-east-1 全局）。
> RAM/SecretsManager 无 CloudWatch metric，纯 describe，必须走采集器。

## 4. 实现模式（对齐磁盘现有代码）

- 每条规则延续 `apply_chain_inference()` 内联循环模式：
  `for rid, metrics in signals.get("<ResourceType>", {}).items():`，命中则 `make_incident(...)`
  （字段对齐 `make_incident` 签名）。
- `resource_type` 用大驼峰：`Athena` / `RAM` / `SecretsManager` / `CloudFront` / `OpenSearch`。
- 采集器返回 `(incidents, signals_dict)` 二元组时，由 `registry.py` 按 EKS 现有模式合并进总 `signals`；若仅需填充 signals 不发 incident（如纯 metric 已由 PRODUCTS 覆盖的），返回单 list 即可。
- 判定逻辑写成纯函数式、可单测；阈值常量集中在采集器顶部。

## 5. 测试与验收（每服务独立 GCL）

| 验收项 | 标准 |
|--------|------|
| 路由表 | Phase-1 已补 8 行，grep 确认 5 个技能名均在 cruise/orchestrator SKILL.md（不重复改） |
| 规则语义 | addendum 修正为 5 条均 "✅ implemented" |
| Python 实现 | 每条规则一段内联逻辑，走 `make_incident` |
| 单测 | `test_inference_phase23.py`：合成 signals 验证命中/不命中边界；`pytest` 全绿 |
| 不回归 | 现有 live 规则行为不变；`test_inference_phase1.py` / `test_shared.py` 零 failure |
| 不自动执行 | 新增代码无 `modify-/delete-/terminate-` 调用（grep 验证） |
| §12 split | 代码改动走 `codegraph sync .` + `codegraph explore`；addendum Markdown 走 Grep |
| Token Efficiency | 每个服务落地后过 Token Efficiency Monitor（OPTIMAL/REFACTOR-NOW/ACCEPT-SUBOPTIMAL） |
| GCL | 每服务 reflect-until-clean（Generator + ≥2 Critic，零问题）|

## 6. 分期与 Fan-out

按服务扇出独立子 Agent（并行），每个子 Agent 拥有完整 spec 片段 + 数据可用性约束：

| 子 Agent | 服务 | 改动文件 |
|----------|------|----------|
| A | Athena | `collectors/analytics.py`(新) + `_inference.py` + `registry.py` |
| B | RAM | `collectors/governance.py`(增补) + `_inference.py` + `registry.py` |
| C | SecretsManager | `collectors/governance.py`(增补) + `_inference.py` + `registry.py` |
| D | CloudFront | `collectors/edge.py`(增补) + `_inference.py` + `registry.py` |
| E | OpenSearch | `collectors/search.py`(新) + `_inference.py` + `registry.py` + `_shared.py`(PRODUCTS 可选) |

主 Agent 仅编排 + 汇总 + 每服务过 Token Efficiency Monitor + 统一 commit + 修 addendum。

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| `_inference.py` 多子 Agent 并发改同一文件冲突 | 每个子 Agent 改**独立函数段/独立 signals key**；主 Agent 串行合并到 `apply_chain_inference` 末尾，避免同一处编辑 |
| 阈值不合理误报 | 纯函数 + 单测覆盖命中/不命中边界 |
| 编号冲突 | 沿用设计文档既定 ID（ATHENA-COST-01 等），不新造 |
| 采集器维度/命名空间错 | 实现前用 `aws <svc> ... --help` 或 `references/` 文档验证（fact-check 门禁） |
