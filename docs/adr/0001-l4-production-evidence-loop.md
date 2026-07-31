# ADR-0001: 以生产证据闭环推动 Agentic AI 稳定 L4

- **Status**: Accepted
- **Date**: 2026-07-28
- **Owners**: aws-skills maintainers
- **Decision scope**: 评测、运行时安全、可观测性、跨服务执行与持续学习
- **Related**: `docs/agentic-maturity-model.md`, `docs/failure-patterns.md`, `aws-skill-generator/references/gcl-spec.md`

## Context

仓库已达到受治理的 L3+：37/37 skill 通过严格 TE Gate，具备跨 skill 委派、GCL、运行时安全、trace、反思记忆和有限 `AUTO_HEAL`。当前主要缺口不再是规则数量，而是缺少可重复的生产证据：真实场景成功率、人工接管率、安全阻断率、恢复时间、成本和跨服务失败补偿尚未形成统一闭环。

继续扩充 SKILL.md 或增加静态规则，边际收益低且可能增加治理漂移。稳定 L4 需要证明系统能持续评测、先模拟后执行、在线观测、失败补偿，并将经验回灌后验证改进有效。

## Decision

接下来两个里程碑停止无指标驱动的 skill 扩张，集中建设四条能力主线：

1. **Eval Harness**：把 golden scenarios 扩展成统一、可重复、分风险等级的仓库级评测体系。
2. **Shadow Execution**：所有写操作先生成计划、预期 diff 和 blast radius，再进入执行授权。
3. **Telemetry + SLO**：统一 GCL、runtime safety、人工接管、成本和恢复指标，形成 30 天滚动证据。
4. **Transactional Orchestration**：跨服务计划声明前置条件、后置条件和 compensation；失败时按策略补偿或安全停止。

持续学习只接受“有评测证明”的规则更新：failure pattern 产生候选规则后，必须通过历史失败重放和回归基线，才能进入 `AGENTS.md` 或 runtime guardrail。

## Non-Goals

- 不追求无限自治或取消人工确认。
- 不以更多 Markdown、更多 skill 数量作为 L4 成功指标。
- 不让 Critic、Telemetry 或学习模块直接修改 AWS 资源。
- 不在没有 shadow evidence 和 rollback/compensation 的情况下扩大 `AUTO_HEAL`。

## Architecture

```text
Request
  → Planner (plan + risk + expected diff)
  → Shadow Executor (dry-run / describe / simulator)
  → Runtime Safety (policy + failure memory + confirmation token)
  → Generator → Critic → Orchestrator
  → AWS tool proxy
  → Validator
  → Compensation / Safe Halt
  → Telemetry
  → Failure Candidate
  → Offline Eval Replay
  → Approved Knowledge Update
```

### Trust Boundaries

| Component | May read | May write | Must not do |
|---|---|---|---|
| Planner | request, skill contracts, topology | execution plan | call AWS mutations |
| Shadow Executor | plan, AWS read APIs, simulator | shadow evidence | execute real writes |
| Runtime Safety | plan, policy, failure patterns | allow/block decision | weaken confirmation rules |
| Generator | approved plan | resource mutation through proxy | alter rubric or policy |
| Critic | sanitized result, rubric | score and remediation advice | see raw secrets or mutate resources |
| Telemetry | redacted traces and outcomes | metrics/events | become an execution dependency |
| Learning pipeline | failures, eval corpus | candidate rule | auto-promote untested rules |

## Delivery Plan

### Milestone 1 — Evidence Foundation

**Target**: 可重复评测和稳定指标基线。

#### Progress (2026-07-31)

**DONE (bootstrap + Wave 2 core)**

- 仓库级 `golden-scenarios.yaml`：45 个文件，每个 ≥5 场景，共 274 场景；`golden_eval` 45/45 PASS。
- Confirmation Strings 已统一为 Operation/token 规范表（commit `f215a6a`）。
- `te_gate --all --strict` PASS（37/37 base skill）。
- `evals/scenarios/schema.md` + 五 skill rich `scenarios.yaml`（`risk`, `preconditions`, `expected_plan`, `expected_gate`, `expected_outcome`, `forbidden_actions`）；thin `golden-scenarios.yaml` 按 `id` 对齐。
- 五高风险服务各 ≥10 场景：EC2 14、S3 13、IAM 11、RDS 10、KMS 10，合计 **58**；五类 `risk` 全覆盖。
- `golden_eval.py` 双读 + `--all-high-risk` batch runner；基线 → `audit-results/golden/high-risk.json`（58/58 PASS）。
- mutation-test CI：`scripts/mutation_gate.py` + `scripts/tests/test_mutation_safety_gate.py` + `.github/workflows/golden-high-risk.yml`（故意移除门 → `compare_to_baseline` 100% 检出）。
- trace outcome 枚举扩展：`PASS|SAFETY_FAIL|MAX_ITER|BLOCKED|COMPENSATED`（`golden_eval.VALID_STATUSES` + `gcl_runner.normalize_outcome`；COMPENSATED 为 M3 占位，不执行补偿）。
- 30 天 dashboard warm-up **已启动**：`docs/telemetry/dashboard-2026-07-31.md`；**禁止在 30 天基线完成前扩大 AUTO_HEAL**。

**STILL OPEN (M1 满窗)**

- 30 天 dashboard baseline 满窗完成（warm-up 进行中，首份 snapshot 已生成）。

**Exit criteria**（工程项 ✅ / 满窗项 ⚠️）:

- [x] 5 个高风险服务各 ≥10 个场景，总计 ≥50（实际 58）。
- [x] mutation tests 对故意移除的安全门检出率 100%。
- [x] baseline 可在干净环境重复运行（`--all-high-risk` → `high-risk.json`）。
- [x] trace 中零明文凭据（沿用 A9 / runtime 掩码）。
- [ ] 30 天 dashboard 满窗基线（warm-up；不阻塞 M1 工程闭环判定，阻塞 AUTO_HEAL 扩大与 M2 放宽）。

### Milestone 2 — Shadow Execution

**Target**: 写操作执行前可证明计划、范围和预期变化。

#### Progress (2026-07-31)

**DONE (engineering W0–W5)**

- Design/Plan: `docs/superpowers/specs/2026-07-31-adr-m2-shadow-execution-design.md` + `plans/2026-07-31-adr-m2-shadow-execution.md`
- `scripts/execution_plan.py` — `ExecutionPlan` / `compute_plan_hash` / drift assert
- `scripts/shadow_exec.py` — dry-run | describe | simulate；A9 redact；`audit-results/shadow/`
- `build_plan_bound_token(call, plan_hash)` + `safe_tool_proxy` hard gate（缺 shadow / plan 漂移 → BLOCK）；GCL `confirm=` 不变
- `scripts/shadow_coverage.py check --all-high-risk`：**27/27** destructive 产出 plan_hash + ok shadow
- CI：`.github/workflows/golden-high-risk.yml` 增 M2 pytest + shadow coverage；`--all-high-risk` 仍 **58/58**

**STILL OPEN**

- 全仓非五高风险 skill 的 shadow 覆盖（刻意非目标）
- M3 补偿 / AUTO_HEAL 扩大（仍受 M1 满窗基线约束）

**Exit criteria**:

- [x] 100% 五高风险 destructive scenarios 产生 plan hash 和 shadow evidence（27/27）
- [x] 参数/region/资源漂移被阻断（proxy + unit fixtures）
- [x] 误阻断率在 fixture happy-path = 0（&lt;5%）；安全漏放 = 0（legacy token / 无 shadow → BLOCK）

### Milestone 3 — Transactional Orchestration

**Target**: 跨服务执行具备确定的停止和补偿行为。

- 将跨 skill runbook 表示为 DAG；每个节点声明 `precondition`, `postcondition`, `compensation`, `non_compensable`。
- 补偿动作也必须经过 runtime safety 和 GCL，不允许绕过门禁。
- 不可补偿节点默认 `MANUAL`，执行前生成恢复手册和证据快照。
- 先覆盖三条链：ELB target remediation、RDS failover + Route53、ECS deployment + ELB health。

**Exit criteria**:

- 三条链均有成功、节点失败、补偿失败测试。
- 可补偿失败的自动恢复率 ≥90%。
- 不可补偿动作 100% 在执行前停留于人工确认。

### Milestone 4 — Governed Learning

**Target**: 失败经验自动产生、离线验证、人工批准后生效。

- 从 `SAFETY_FAIL`, `MAX_ITER`, `BLOCKED`, compensation failure 生成候选 failure pattern。
- 自动去重、最小化并关联资源类型和场景证据。
- 使用历史失败重放和全量 eval 验证候选规则。
- 只有无回归且修复目标失败的候选才能进入批准队列；批准后更新长期资产。

**Exit criteria**:

- 候选规则重复率 <10%。
- 规则提升必须有 before/after eval 证据。
- 自动晋升率保持 0%；所有长期规则均可追溯到批准记录。

## Metrics and SLOs

| Metric | Initial SLO | Gate |
|---|---:|---|
| Safety escape rate | 0 | 任一逃逸立即冻结相关 AUTO_HEAL |
| Secret leakage rate | 0 | 任一泄漏为 P0 |
| Destructive plan coverage | 100% | 缺 plan 不执行 |
| Shadow evidence coverage | 100% destructive / ≥90% writes | 不达标不得扩自治 |
| GCL PASS rate | ≥95% read-only; ≥90% writes | 连续 7 天低于阈值触发回归 |
| MAX_ITER rate | <5% | 超阈值进入 prompt/rubric review |
| Human takeover rate | 记录基线后按场景下降 | 不以降低安全接管为目标 |
| Compensation success | ≥90% compensable failures | 低于阈值降级为 MANUAL |
| MTTR improvement | 相对人工基线 ≥30% | 仅比较同类事件 |
| Cost per successful run | 建立 p50/p95 基线 | p95 回归 >20% 阻断发布 |

## Rollout Policy

自治等级按服务和操作分别授予，不按整个 skill 一次开放：

1. `OBSERVE`：只读收集与诊断。
2. `RECOMMEND`：产生计划，不写资源。
3. `SHADOW`：运行模拟和 dry-run。
4. `AI_ASSIST`：人工确认后执行。
5. `AUTO_HEAL`：仅对通过评测、可补偿、限定范围的操作开放。

任何指标越界、规则漂移或补偿失败，自动降级一级；Safety escape 或 secret leakage 直接降到 `OBSERVE`。

## Consequences

### Positive

- L4 评级从“架构能力声明”转为可审计的运行证据。
- 扩大自治之前先证明安全、效果和成本。
- 跨服务失败具备统一补偿和停止语义。
- 学习资产可追溯、可回放、可证明无回归。

### Costs

- 场景维护、模拟器和 telemetry schema 增加工程成本。
- 初期执行延迟上升，部分 AUTO_HEAL 会被降级。
- 需要稳定保存脱敏 trace、baseline 和批准记录。

### Risks

- 评测集可能与真实流量偏离；用 shadow telemetry 和事故回放持续校准。
- 过严 gate 可能提高误阻断；允许优化误阻断，但安全漏放必须保持 0。
- compensation 自身可能失败；补偿同样经过 GCL，并为不可补偿动作保留人工恢复手册。

## Rejected Alternatives

1. **继续扩充技能数量**：不能证明生产安全或业务价值。
2. **直接扩大 AUTO_HEAL**：缺少 shadow、SLO 和补偿证据，风险不可接受。
3. **只建设 dashboard**：可见性不能替代执行前验证和失败恢复。
4. **让系统自动修改长期规则**：存在反馈污染和安全规则自我弱化风险。

## Delivery Governance

- 每个 Milestone 必须有 spec、plan、测试和阶段评审。
- 每项实现遵循 TDD，并维护 baseline diff。
- 每个 Milestone 完成后更新 `docs/agentic-maturity-model.md`，不得提前将计划能力标为 Implemented。
- ADR 变更必须新增后继 ADR；不直接覆写已接受决策的核心方向。

## Revisit Conditions

满足任一条件时重新评审：

- 出现 Safety escape、明文秘密泄漏或不可恢复生产事故。
- 连续 30 天无法达到 GCL、compensation 或成本 SLO。
- AWS 原生 dry-run、policy simulation 或审计能力发生重大变化。
- 仓库定位从运维工具集转向完全托管的生产执行平台。
