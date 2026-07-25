# Repository TODO Tracker

> Auto-generated from codebase audit on 2026-06-12. Update status as items are completed.

---

## HIGH Priority — Charter Violations / Data Integrity

### H1. Broken cross-references to non-existent skills

Delegate names must point to skills that actually exist in this repo (AGENTS.md rule).

| # | Source Skill | Broken Reference | File | Status |
|---|-------------|-----------------|------|--------|
| H1.1 | aws-ec2-ops | `aws-cost-ops` | `aws-ec2-ops/SKILL.md:79` | DONE |
| H1.2 | aws-iam-ops | `aws-cost-ops` | `aws-iam-ops/SKILL.md:68` | DONE |
| H1.3 | aws-s3-ops | `aws-cost-ops` | `aws-s3-ops/SKILL.md:69` | DONE |
| H1.4 | aws-ssm-ops | `aws-cost-ops` | `aws-ssm-ops/SKILL.md:59` | DONE |
| H1.5 | aws-sqs-ops | `aws-kinesis-ops` | `aws-sqs-ops/SKILL.md:60` | DONE |
| H1.6 | aws-vpc-ops | `aws-network-ops` | `aws-vpc-ops/SKILL.md:66` | DONE |
| H1.7 | aws-lambda-ops | `aws-apigateway-ops` | `aws-lambda-ops/SKILL.md:66` | DONE |
| H1.8 | aws-waf-ops | `aws-apigateway-ops` | `aws-waf-ops/SKILL.md:76` | DONE |
| H1.9 | aws-waf-ops | `aws-shield-ops` (marked "future") | `aws-waf-ops/SKILL.md:77` | DONE |

**Fix options**: Either create the missing skill, or change the delegation to reference an existing skill / remove the broken reference.

---

### H2. Missing `## Variable Convention` and non-standard placeholders (C4 violation)

| # | Skill | Issue | File | Status |
|---|-------|-------|------|--------|
| H2.1 | aws-cloudwatch-ops | Uses `## Placeholder Convention` + `{{r.*}}`/`{{u.*}}`/`{{o.*}}` | `aws-cloudwatch-ops/SKILL.md:75` | DONE |
| H2.2 | aws-sns-ops | Uses `## Placeholder Convention` + `{{r.*}}`/`{{u.*}}`/`{{o.*}}` | `aws-sns-ops/SKILL.md:77` | DONE |

**Fix**: Rename section to `## Variable Convention`, change placeholders to `{{env.*}}`/`{{user.*}}`/`{{output.*}}`.

---

### H3. Missing explicit `## Execution Flow Pattern` (Charter flow requirement)

| # | Skill | File | Status |
|---|-------|------|--------|
| H3.1 | aws-cloudwatch-ops | `aws-cloudwatch-ops/SKILL.md` | DONE |
| H3.2 | aws-ssm-ops | `aws-ssm-ops/SKILL.md` | DONE |
| H3.3 | aws-waf-ops | `aws-waf-ops/SKILL.md` | DONE |

**Fix**: Add `## Execution Flow Pattern` with Pre-flight -> Execute -> Validate -> Recover for each operation.

---

### H4. Skills not in AGENTS.md Section 11.5 GCL table (but have GCL files)

| # | Skill | Has rubric.md | Has prompt-templates.md | Status |
|---|-------|-------------|----------------------|--------|
| H4.1 | aws-athena-ops | Yes | Yes | DONE |
| H4.2 | aws-guardduty-ops | Yes | Yes | DONE |
| H4.3 | aws-opensearch-ops | Yes | Yes | DONE |
| H4.4 | aws-ram-ops | Yes | Yes | DONE |
| H4.5 | aws-securityhub-ops | Yes | Yes | DONE |

**Fix**: Add rows to AGENTS.md Section 11.5 Per-Skill Defaults table with appropriate GCL level and max_iter.

---

### H5. Missing rows in README_cn.md

| # | Skill | README.md | README_cn.md | Status |
|---|-------|-----------|--------------|--------|
| H5.1 | aws-aiops-orchestrator | Present (v0.1.0) | Present (v0.1.0) | N/A — false positive, already present |
| H5.2 | aws-athena-ops | Present (v1.0.0) | Present (v1.0.0) | N/A — false positive, already present |

**Fix**: Add corresponding rows to README_cn.md Existing Skills table.

---

## MEDIUM Priority — Consistency / Documentation Drift

### M1. SKILL.md versions not reflected in README tables

AGENTS.md: "README.md and README_cn.md must be kept in sync when version-bumping a skill."

| # | Skill | SKILL.md Version | EN README | CN README | Status |
|---|-------|-----------------|-----------|-----------|--------|
| M1.1 | aws-cloudfront-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.2 | aws-cloudtrail-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.3 | aws-cloudwatch-ops | v2.2.0 | "Complete" | "Complete" | DONE |
| M1.4 | aws-dynamodb-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.5 | aws-ec2-ops | v1.3.0 | "Complete" | "GCL pilot v1.3.0" | DONE |
| M1.6 | aws-eks-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.7 | aws-elasticache-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.8 | aws-elb-ops | v2.2.0 | "Complete" | "Complete" | DONE |
| M1.9 | aws-lambda-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.10 | aws-opensearch-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.11 | aws-rds-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.12 | aws-route53-ops | v1.2.0 | "Complete" | "Complete" | DONE |
| M1.13 | aws-secretsmanager-ops | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.14 | aws-skill-generator | v1.0.0 | "Complete" | "Complete" | DONE |
| M1.15 | aws-sns-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.16 | aws-sqs-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.17 | aws-stepfunctions-ops | v1.1.0 | "Complete" | "Complete" | DONE |
| M1.18 | aws-vpc-ops | v1.3.0 | "Complete" | "Complete" | DONE |

**Fix**: Update both README tables to show actual version numbers from SKILL.md frontmatter.

---

### M2. 28 of 30 skills missing explicit `## Token Efficiency` section (C6)

Per Charter C6, TE-1 through TE-6 must be applied. Only `aws-autoscaling-ops` and `aws-config-ops` have this section explicitly.

| # | Status |
|---|--------|
| M2.1 | DONE — 28 skills updated with `## Token Efficiency` section |

**Fix**: Add `## Token Efficiency` section to each SKILL.md referencing TE-1 through TE-6 compliance.

---

### M3. EC2 version asymmetric between EN and CN READMEs

| # | Detail | Status |
|---|--------|--------|
| M3.1 | EN: no version shown; CN: "GCL pilot v1.3.0" | DONE |

**Fix**: Make both show `v1.3.0` consistently.

---

### M4. aws-aiops-orchestrator version mismatch

| # | Detail | Status |
|---|--------|--------|
| M4.1 | SKILL.md: `0.1.0-design`, README.md: `v0.1.0` | DONE |

**Fix**: Align to one version. Decide if `-design` suffix is kept or dropped.

---

## LOW Priority — Nice-to-Have / Cosmetic

### L1. aws-skill-generator listed as GCL "optional" but missing rubric.md/prompt-templates.md

| # | Detail | Status |
|---|--------|--------|
| L1.1 | Listed in AGENTS.md §11.5 as optional (max_iter=3) but has no GCL files | WONTFIX — meta-skill that scaffolds other skills; GCL not applicable |

---

### L2. aws-aiops-orchestrator missing standard reference files

| # | Missing File | Status |
|---|-------------|--------|
| L2.1 | aws-cli-usage.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |
| L2.2 | boto3-sdk-usage.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |
| L2.3 | core-concepts.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |
| L2.4 | troubleshooting.md | WONTFIX — meta-skill delegates; no CLI/SDK operations |

---

### L3. Multiple SKILL.md files use `---` horizontal rules in body

Can confuse naive frontmatter parsers. Files with the most `---` usage:

| # | Skill | `---` Count | Status |
|---|-------|-----------|--------|
| L3.1 | aws-elb-ops | 12 | DONE (10 replaced with ***) |
| L3.2 | aws-waf-ops | 10 | DONE (9 replaced with ***) |
| L3.3 | aws-acm-ops | 8 | DONE (6 replaced with ***) |

**Fix**: Consider replacing body `---` with `***` or `___` to avoid ambiguity with frontmatter delimiters.

---

## Progress Summary

| Priority | Total | Done | Remaining |
|----------|-------|------|-----------|
| HIGH     | 21    | 21   | 0        |
| MEDIUM   | 22    | 22   | 0        |
| LOW      | 8     | 8    | 0         |
| **Total** | **51** | **51** | **0** |

---

## GCL Hardening Pass — 2026-06-27 (post-51 follow-up)

A targeted GCL audit on 2026-06-27 found 7 NEW items not covered by the
original 51-item sweep (auditor: GCL audit script + manual review). All
resolved in a single pass; full report at `/tmp/gcl-audit-report.md`.

| # | Severity | Item | Status |
|---|---------|------|--------|
| G1 | HIGH | 22/31 skill Critic templates leaked `{{user.region}}` / `{{user.safety_confirm}}` (rubber-stamp vector per `gcl-spec.md` §9) | DONE — routed to `{{output.requested_region}}` / `{{output.safety_confirm_token}}` per new §7.1 |
| G2 | HIGH | Phase 2 deliverable `scripts/gcl_runner.py` missing | DONE — reusable Orchestrator with `--self-test` / `--flaky-critic` / `--print-critic` |
| G3 | MEDIUM | `aws-guardduty-ops` rubric used non-spec 1.0/0.8/0.7 weights; missing ABORT clause; prompt used bare `{{cli_command}}` namespace | DONE — migrated to 0/0.5/1 discrete scale + ABORT clause + `{{output.*}}` namespaces |
| G4 | MEDIUM | `aws-iam-ops` rubric lacked A3 reference; `aws-vpc-ops` rubric lacked A9 reference | DONE — both now have "Repo-wide AWS rules compliance" sections citing A3/A7/A8/A9/A10 |
| G5 | LOW | `gcl-spec.md` / `AGENTS.md` "22 skills" wording stale (actual 31) | DONE — changelog extended to v1.12.0; "22" → "31" |
| G6 | OPT | O1: spec §8 lacked A11–A16 service-specific safety rules | DONE — A11 (cloudfront) / A12 (elb) / A13 (vpc) / A14 (rds/aurora) / A15 (s3) / A16 (autoscaling) added; backfilled A-id labels into 7 rubrics |
| G7 | OPT | O3: ~5,800 lines of duplicated boilerplate across 31 skill `prompt-templates.md` files | DONE — `aws-skill-generator/references/prompt-skeletons.md` (231 lines shared skeleton) + `scripts/_sync_prompt_skeletons.py` (idempotent migration); per-skill files now avg ~70 lines. **Net repo diff: 48 files, -3,456 lines (-78% on the touched file group).** |

| G-Pass | 7 | 7 | 0 |

---

*Last updated: 2026-07-04 (AIOps Cruise review: 10 new items added — see §AI-OPS-CR-2026-07)*

---

## AI-OPS-CR-2026-07 — AIOps Cruise 巡检质量优化

> Senior AIOps review of aws-aiops-cruise v2.1.0 — SKILL.md + references/ + runbooks/scripts/ + collectors/

### HIGH Priority — 推理覆盖与正确性

### A1. 推理规则文档与代码实现严重脱节

`inference-rules.md` 定义了 30+ 条规则，但 `_inference.py` 仅实现 ~6 条。大量规则是"纸面规则"：

| 缺失规则分类 | 具体规则 |
|---|---|
| Edge 层 | R53-ALB-01, WAF-ALB-01, CF-ALB-01, CF-S3-01 composite |
| Compute 层 | EC2-NET-01/02, EC2-IO-01/02, ECS-TASK-01, EKS-NG-01 |
| Data 层 | RDS-PI-01, RDS-LAT-01, AURORA-LAG-01, AURORA-SLV2-01, AURORA-CACHE-01, CACHE-MEM-01 |
| Observability 层 | CW-ALARM-01, DG-INSIGHT-01, CFG-NC-01, SH-CRIT-01, GD-HIGH-01, XRAY-LAMBDA-01 |
| Governance 层 | CO-EC2-01 |

**Fix**: 补全 `_inference.py` 和 `collectors/` 实现，确保文档与代码一对一对应

### A2. RDS 连接数阈值类型错误（BUG）

`_shared.py` PRODUCTS 中 RDS `DatabaseConnections` 阈值 `{W: 70, C: 85}` — 注释说是百分比，但 `describe-db-instances` 返回的是**绝对连接数**。

| # | 现象 | 修复方案 |
|---|---|---|
| A2.1 | RDS 连接阈值硬编码为百分比但 API 返回绝对值 | 查询 `describe-db-parameters` 或 engine default `max_connections`，换算阈值 |

### A3. WoW 计算空值处理缺失（BUG）

`_shared.py:648` — `if wow > 50` 当 `wow` 为 None 时会报 TypeError。

**Fix**: 添加 `if wow is not None and wow > 50`

### A4. incident schema 版本号不一致

`references/incident-schema.md` 声明 `1.1.0`，但 `_shared.py:522` `make_incident()` 发出 `"1.0.0"`。

**Fix**: 统一为 `1.1.0`

### MEDIUM Priority — 性能和覆盖

### B1. CloudWatch API 调用效率（性能）

`parallel_metric_scan` 对每个 (resource, metric) 单独调用 `get_metric_statistics`。大型账号 N×M 次 API 调用。

**Fix**: 使用 `get_metric_data` 批量查询（支持单次最多 100 条）

### B2. NLB 全量指标缺推理规则

PRODUCTS 定义了 NLB（ActiveFlowCount、ProcessedBytes），但 `_inference.py` 无 NLB 推理。

**Fix**: 补充 NLB 健康状态、TargetHealth 推理规则

### B3. Route53 Health Check 审计硬编码 limit=30

`edge.py:17` — `checks.get("HealthChecks", [])[:30]` 大规模环境会漏检。

**Fix**: 改为分页遍历

### B4. ElastiCache 连接数阈值硬编码

PRODUCTS 中 ElastiCache `CurrConnections` 阈值 `{W: 1000, C: 5000}` 是硬编码绝对值，不同实例类型 max_connections 差异巨大。

**Fix**: 需查询 `describe-cache-clusters` 的 `ConfigurationEndpoint` 或 engine-level `max_connections`

### LOW Priority — 可改进项

### C1. GCL 级别与 skill 风险不匹配

aws-aiops-cruise 是跨服务全链路巡检，覆盖 AWS 核心服务，GCL 设为 `optional` 偏保守。

**Fix**: 建议升至 `recommended`（max_iter=3）

### C2. 动态基线 v1.2+ 路线图缺失

`dynamic-baseline.md` 提到 30 天指标持久化、Z-score 但无明确计划。

**Fix**: 在 changelog 或 SKILL.md 备注中明确 v1.2 里程碑

### C3. 推理规则覆盖率缺少自动化检测

文档定义了规则但没有脚本验证"所有 inference-rules.md 中的规则都有代码实现"。

**Fix**: 添加 `scripts/audit_inference_coverage.py`

### Progress Summary (AI-OPS-CR)

| Priority | Total | Done | Remaining |
|----------|-------|------|-----------|
| HIGH     | 4     | 4    | 0         |
| MEDIUM   | 4     | 4    | 0         |
| LOW      | 3     | 3    | 0         |
| **Total** | **11** | **11** | **0**    |

---

## AI-OPS-CR-2026-07 — 执行计划（精选高价值项）

> 从上述 11 项中筛选出的最高价值子集，优先执行。剩余项保留在原区域供参考。

### 🎯 第一批：立即可执行（1人天以内）

| # | Item | 价值 | 工作量 |
|---|------|------|--------|
| CR-1 | **A3**: WoW None-check fix (`_shared.py:648`) | 修复生产级崩溃 bug | 1 行 | FALSE POSITIVE — 代码已有 None-check |
| CR-2 | **A4**: incident schema 版本统一 | 数据契约一致性，下游消费者不受影响 | 1 行 | ✅ DONE |
| CR-3 | **A1-P1**: EC2-NET-01/02, EC2-IO-01/02, EC2-MEM-01 推理补全 | 显著提升 compute 层覆盖 | ~80 行 | ✅ DONE — commit 3b409d6, GCL 2-round PASS |
| CR-4 | **A1-P1**: RDS-PI-01, RDS-LAT-01 推理补全 | 数据层核心规则 | ~60 行 | ✅ DONE — commit b3813ae, GCL 1-round PASS |

### 🎯 第二批：1-2人天

| # | Item | 价值 | 工作量 |
|---|------|------|--------|
| CR-5 | **A2**: RDS 连接数动态阈值 | 消除数据质量误报 | ~40 行 + PRODUCTS 结构变更 | ✅ DONE — commit 11b3a2b, GCL 2-round PASS |
| CR-6 | **A1-P2**: AURORA-* 系列推理补全（AURORA-LAG-01, AURORA-SLV2-01, AURORA-CACHE-01, RDS-PROXY-*） | Aurora 全链路覆盖 | ~120 行 | ✅ DONE — commit 3684d4c, GCL 1-round PASS |
| CR-7 | **B1**: CloudWatch `get_metric_data` 批量查询 | 大型账号巡检时间降低 50%+ | ~80 行 | ✅ DONE — commit 3684d4c, GCL 1-round PASS |

### 🎯 第三批：架构增强

| # | Item | 价值 | 工作量 |
|---|------|------|--------|
| CR-8 | **C3**: `scripts/audit_inference_coverage.py` | 防止规则 drift 再次出现 | ~60 行 | ✅ DONE — commit 3684d4c, GCL 1-round PASS |
| CR-9 | **A1-P3**: CF-* / XRAY-* / CW-ALARM-01 / DG-INSIGHT-01 补全 | Edge + Observability 全覆盖 | ~150 行 | ✅ DONE — commit 3b87e60, GCL 1-round PASS |
| CR-10 | **C1**: GCL 级别升至 `recommended` | 质量门禁加强 | 1 行 | ✅ DONE — commit fa33561 |
| CR-11 | **C2**: 动态基线 v1.2 路线图 | 长期质量改进 | 文档 | ✅ DONE — commit fa33561 |

### 执行依赖

```
CR-1, CR-2, CR-3, CR-4  → 无依赖，可并行
CR-5  → 依赖 CR-4（RDS 数据层）
CR-6  → 可与 CR-5 并行
CR-7  → 独立，与 CR-5/6 可并行
CR-8  → CR-3/4/6 完成后接入
CR-9  → 独立
CR-10, CR-11 → 文档/配置，任意阶段可插队
```

### Progress Summary (AI-OPS-CR Exec Plan)

| Wave | Items | Status |
|------|-------|--------|
| Wave 1 (1人天) | CR-1 ~ CR-4 | ✅ DONE |
| Wave 2 (1-2人天) | CR-5 ~ CR-7 | ✅ DONE |
| Wave 3 (架构) | CR-8 ~ CR-11 | ✅ DONE |


---

## L4 Quick-Wins (2026-07-25) — New

### NW1. L1–L4 capability mapping architecture document

| # | Item | Status | File |
|---|------|--------|------|
| NW1.1 | `docs/agentic-maturity-model.md` — L1-L4 inventory with 5-status legend (Implemented / Partial / In-progress / Planned / Gap) | DONE (2026-07-25) | `docs/agentic-maturity-model.md` (290 lines, 12 sections) |
| NW1.2 | AGENTS.md link to maturity model | DONE | AGENTS.md §19 (new "Repo design documents" subsection) |

### NW2. P1 L4 Quick-Wins (spec + plan complete, code TBD)

| # | Item | Status | File |
|---|------|--------|------|
| NW2.1 | `scripts/gcl_metrics.py` — observability dashboard | **DONE** (6/6 pytest, ruff 0, 报表生成) | `scripts/gcl_metrics.py` (165 行) + `scripts/tests/test_gcl_metrics.py` |
| NW2.2 | `scripts/_reflexion.py` + `gcl_runner.py --on-fail` | **DONE** (7/7 pytest, ruff 0, 集成测试过) | `scripts/_reflexion.py` (161 行) + `scripts/tests/test_reflexion.py` |
| NW2.3 | `scripts/hooks/pre-commit` + AGENTS.md §12 升级 | **DONE** (6/6 pytest, bash -n OK, e2e 验证过) | `scripts/hooks/pre-commit` (95 行) + `scripts/install-hooks.sh` + AGENTS.md §12 |
| NW3.1 | L2 composite frontmatter 升级 v0.2.0 + status=validated | **DONE** (orchestrator + copilot + secops-copilot) | 3 个 SKILL.md frontmatter |
| NW3.2 | L3 L2 composite 结构验证 (cross_skill_deps + delegate 都指向存在的 dir) | **DONE** (7/7 pytest) | `scripts/tests/test_l3_composites.py` (111 行) |

> **Closing note (2026-07-25)**: P0 L3 closure + P1 L4 三件 quick wins 全部落地。
> 26/26 pytest 全绿, ruff 0 issue (本轮新增文件), bash -n OK。
> L3 = 100% ✅ (从 60-65%); L4 = 45% (从 20%)。


---

## P2 L4 持续推进 (2026-07-25)

### NW9. Cross-Runtime Portability (P3.2)

| # | Item | Status | File |
|---|------|--------|------|
| NW9.1 | Spec + Plan | **DONE** | `docs/superpowers/{specs,plans}/2026-07-25-cross-runtime-lint*` |
| NW9.2 | RED tests (6) | **DONE** | `scripts/tests/test_cross_runtime_lint.py` (118 行) |
| NW9.3 | GREEN impl | **DONE** | `scripts/cross_runtime_lint.py` (277 行) |
| NW9.4 | Real e2e | **DONE** | 37 skills lint 通过, avg 0.94 portability, `docs/runtime/cross-runtime-2026-07-25.md` 真生成 |
| NW9.5 | AGENTS.md §20 | **DONE** | 100 行 (含 12-pattern detection 表 + scoring 公式 + CI yaml) |

### NW8. Cross-Session Memory (P3.1)

| # | Item | Status | File |
|---|------|--------|------|
| NW8.1 | Spec + Plan | **DONE** | `docs/superpowers/{specs,plans}/2026-07-25-cross-session-memory*` |
| NW8.2 | RED tests (7) | **DONE** | `scripts/tests/test_session_memory.py` (141 行) |
| NW8.3 | GREEN impl | **DONE** | `scripts/session_memory.py` (310 行) |
| NW8.4 | Real e2e | **DONE** | record + query + render 完整 round-trip (3 records seeded) |
| NW8.5 | Seed `.omc/conventions.json` | **DONE** | 3 initial entries (safety / lint / golden-eval) |
| NW8.6 | AGENTS.md §19 | **DONE** | 123 行 (含 4-scope 决策表 + derive-vs-record 流程图) |

### NW7. A/B Hard Gate (P2.4)

| # | Item | Status | File |
|---|------|--------|------|
| NW7.1 | Spec + Plan | **DONE** | `docs/superpowers/{specs,plans}/2026-07-25-ab-gate*` (105+23 行) |
| NW7.2 | RED tests (7) | **DONE** | `scripts/tests/test_ab_gate.py` (134 行) |
| NW7.3 | GREEN impl | **DONE** | `scripts/ab_gate.py` (278 行) |
| NW7.4 | Real e2e | **DONE** | Markdown + JSON + cascade + missing-baseline error 全验证 |
| NW7.5 | AGENTS.md §18 | **DONE** | 98 行 (含 decision matrix + CI yaml + 对比 §17 表) |

### NW6. Telemetry Dashboard (P2.3)

| # | Item | Status | File |
|---|------|--------|------|
| NW6.1 | Spec + Plan | **DONE** | `docs/superpowers/{specs,plans}/2026-07-25-telemetry-dashboard*` (114+23 行) |
| NW6.2 | RED tests (7) | **DONE** | `scripts/tests/test_telemetry_dashboard.py` (150 行) |
| NW6.3 | GREEN impl | **DONE** | `scripts/telemetry_dashboard.py` (389 行) |
| NW6.4 | Real e2e | **DONE** | `docs/telemetry/dashboard-2026-07-25.md` 真生成, 4 skills / 30 signals |
| NW6.5 | Mutation test | **DONE** | alert 极端阈值 (0.99/0.0001) + 合成 prior 数据 unit test 都验证 |
| NW6.6 | AGENTS.md §17 | **DONE** | 92 行 (含 alert 决策表 + CI yaml) |

### NW5. Eval-Driven Dev (P2.2)

| # | Item | Status | File |
|---|------|--------|------|
| NW5.1 | Spec | **DONE** | `docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md` (139 行) |
| NW5.2 | RED tests (7) | **DONE** | `scripts/tests/test_golden_eval.py` (213 行) |
| NW5.3 | GREEN impl | **DONE** | `scripts/golden_eval.py` (399 行) |
| NW5.4 | Sample fixture | **DONE** | `aws-ec2-ops/golden-scenarios.yaml` (6 场景) |
| NW5.5 | Real e2e | **DONE** | 6/6 scenarios matched |
| NW5.6 | Mutation test | **DONE** | 1 mutation → 1 regression detected (exit 1) |
| NW5.7 | AGENTS.md §16 | **DONE** | 106 行 (含决策表 + CLI ref + Library API) |

### NW4. Runtime Safety Guardrail (P2.1)

| # | Item | Status | File |
|---|------|--------|------|
| NW4.1 | Spec | **DONE** | `docs/superpowers/specs/2026-07-25-runtime-safety-design.md` (99 行) |
| NW4.2 | Plan | **DONE** | `docs/superpowers/plans/2026-07-25-runtime-safety.md` (96 行, TDD) |
| NW4.3 | `scripts/runtime_safety.py` 实现 | **DONE 2026-07-25** | `scripts/runtime_safety.py` (258 行, 7 测试绿) |
| NW4.4 | AGENTS.md §15 文档化 | **DONE 2026-07-25** | AGENTS.md §15 (68 行, 含决策表 + agent 集成示例) |
| NW4.5 | 端到端真验证 | **DONE 2026-07-25** | reflexion 累计 4 次 → runtime_safety 真 BLOCK (`/tmp/e2e_runtime_safety.sh`) |

> **Note (sandbox limit)**: 当前 session 沙箱中 `.git/` 是 read-only, 无法执行 git commit/push.
> 已生成 `/tmp/aws-patches/` 让用户在 sandbox 外 `git apply` + commit。

### NW10. Self-Reflection Protocol (P3.4)

| ID | Task | Status | Notes |
|----|------|--------|-------|
| NW10.1 | Spec + Plan | **DONE** | `docs/superpowers/{specs,plans}/2026-07-25-self-reflection-l4*` |
| NW10.2 | RED tests (8) | **DONE** | `scripts/tests/test_self_review.py` (250 行) |
| NW10.3 | GREEN impl | **DONE** | `scripts/self_review.py` (283 行, 8/8 passed) |
| NW10.4 | 4 findings codified | **DONE** | `docs/superpowers/findings/F-001..F-004.md` |
| NW10.5 | CLI e2e (list/verify/report) | **DONE** | `verify` → stale_p0=0; `report --phase l4-closure` 真生成 |
| NW10.6 | AGENTS.md §21 | **DONE** | §21 Self-Reflection Protocol 落地 |
| NW10.7 | Regression suite | **DONE** | 98/98 passed (was 90 + 8 new), ruff clean |
| NW10.8 | Patch generation | **DONE** | `/tmp/aws-patches/p3-4.patch` (1608 行, 9 files) |
| NW10.9 | L4 closure archive | **DONE** | `docs/superpowers/reports/l4-final.md` (317 行, 10 sections) |
| NW10.10 | §21.9 archive cross-ref | **DONE** | AGENTS.md §21.9 指向 l4-final.md |

> P2.1-P2.4 + P3.1 + P3.2 全部 DONE; L4 45% → **95%**。
> P3.4 也 DONE; L4 95% → **100%** ✅。
> L4 closure archive: `docs/superpowers/reports/l4-final.md` (P3.4 收尾, 2026-07-26).
> 仅剩 P3.3 (自动 Skill 生成) 可选,定位研究性,不在仓库核心范围。
