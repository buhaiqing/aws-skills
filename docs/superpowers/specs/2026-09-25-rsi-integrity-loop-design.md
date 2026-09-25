# Recursive Self Improvement Integrity Loop Design

## Problem Statement

当前仓库已经实现 GCL、Telemetry、Golden Eval、Governed Learning、Memory Eval、Shadow 与 Self Review，但反馈闭环存在可信度断点：Telemetry 将 self-test stub 计为生产证据，Golden current/baseline 重复计数，readiness 在 metrics stale 时仍显示 ALL GREEN，候选晋升可依赖模拟 eval artifact，Memory Eval 可从被测记录自生成 golden cases，scheduled loop 与 candidate-to-rollback outcome ledger 缺失。

目标是在不扩大自动执行权限、不让学习链直接修改 AWS 资源的前提下，建立可信的 Recursive Self Improvement 证据链。任何经验只有在真实信号、独立评测、可追溯 artifact 和无回归证据同时成立时，才能进入后续 promotion 流程。

## Solution

采用三个互斥实现切片和两个串行 GCL 阶段：

1. Signal Integrity：统一真实 trace 判定、Golden run 选择与去重，并让 RSI freshness 参与 readiness。
2. Evidence Contract：候选评测必须绑定真实 eval artifact 和 SHA256，缺失、损坏或不匹配时 fail closed。
3. Shadow Learning：建立独立 labeled memory golden set、scheduled real-trace shadow loop，以及 append-only outcome ledger。

三个切片先各自按 TDD 实现；随后由只读 Critic 并行审查，主 Agent 串行完成跨切片契约整合、完整回归、文档同步和最终 Critic。

## User Stories

1. 作为维护者，我需要 Dashboard 只统计真实、非 self-test 的 GCL run，以便用真实成功率驱动改进。
2. 作为维护者，我需要 Golden current/baseline 不重复计数，以便 pass rate 分母可解释。
3. 作为 CI 维护者，我需要 metrics stale/缺失时 readiness fail，以便“全绿”不代表 RSI 已具备运行证据。
4. 作为 reviewer，我需要每个候选的 before/after evidence 指向真实文件及 SHA256，以便检测 fixture 冒充和证据漂移。
5. 作为安全 reviewer，我需要 artifact 缺失、hash 不匹配、replay 报错时拒绝 promotion，以便学习链 fail closed。
6. 作为 memory maintainer，我需要独立 labeled cases 包含 relevant 与 irrelevant 期望，以便 retrieval eval 不自证。
7. 作为 repository maintainer，我需要定时任务消费真实 run 并只生成 shadow proposals，以便持续学习而不自动写回长期规则。
8. 作为 auditor，我需要查询 candidate 到 rollback 的完整事件链，以便判断规则是否真正改善结果。
9. 作为 operator，我需要 ledger 幂等、append-only、可重放，以便 CI 重跑不污染统计。
10. 作为维护者，我需要统一验证命令和 GCL rubric，以便并行实现不会产生契约漂移。

## Implementation Decisions

### Slice A: Signal Integrity

- `gcl_metrics.is_real_trace` 成为 trace 真实性的单一判定源；Telemetry 不复制判定规则。
- Telemetry 只消费明确选择的 Golden 输入，禁止扫描并混合 `*-current.json` 与 `*-baseline.json`。
- Golden 信号以 `(skill, scenario_id, run_id)` 去重；缺少 run_id 时以稳定内容 hash 作为 fallback identity。
- Readiness 分为 harness 与 RSI 两层；RSI readiness 至少要求 metrics freshness 通过。
- 任何 stale metrics 均不得显示为完整 ALL GREEN。

### Slice B: Evidence Contract

- Eval evidence schema 包含 `artifact_path`、`artifact_sha256`、`generated_at`、`producer`、`run_id`、`regressions`、`no_regression`。
- Hash 基于原始 artifact bytes 计算，不基于重新序列化的 JSON。
- Artifact 缺失、不可读、hash 格式错误、hash 不匹配或 producer/run_id 缺失时，candidate 状态必须为 `needs_eval`。
- `evaluate_candidate` 不再提供硬编码成功 fixture；真实 regression fixture 必须由调用方传入。
- `golden_eval --auto-promote` 移除 broad exception；失败必须结构化输出并返回非零。
- Scheduled shadow mode 不调用 `approve_candidate` 或 `auto_promote`。

### Slice C: Shadow Learning And Outcomes

- 新增独立 labeled memory golden 文件，cases 不得从 `.omc/conventions.json` 自动生成。
- Case schema 包含 `id`、`query`、`relevant_ids`、`irrelevant_ids`；最小有效样本数由配置常量固定。
- Memory eval 在 cases 缺失、schema 非法或样本不足时 fail closed。
- Scheduled workflow 仅由 `schedule` 与 `workflow_dispatch` 触发，消费真实 run，过滤 stub，生成 shadow candidate/eval/outcome artifact；不 push、不修改长期规则。
- Outcome ledger 为 append-only JSONL；事件类型覆盖 `candidate_proposed`、`candidate_evaluated`、`promotion_recorded`、`deployment_observed`、`post_deploy_measured`、`rollback_recorded`。
- Ledger identity 使用 `event_id` 幂等；重跑不得重复追加同一事件。
- Outcome report 从 ledger 计算 candidate→promotion→post-deploy delta→rollback 完整性和有效样本数。

## Testing Decisions

- 所有行为变更执行 TDD：先观察 targeted test 因缺失行为失败，再写最小实现。
- Slice A 测试必须混合 real trace、stub trace、current/baseline 和重复 scenario，证明 Dashboard 不误计。
- Readiness 测试必须证明 stale metrics 不能产生完整 green。
- Slice B 测试必须覆盖真实 artifact round-trip、缺失 artifact、tamper/hash mismatch、replay failure 和 broad-exception 回归。
- Slice C 测试必须覆盖独立 cases、irrelevant 判定、样本不足 fail-closed、scheduled dry-run、无长期 KB 写入、ledger idempotency 和完整 outcome report。
- 集成门禁：`ruff check scripts/`、`pytest -v scripts/tests/`、pre-commit、workflow YAML 解析、三个 CLI dry-run 均通过。
- Critic 必须检查 Spec↔Plan↔Code、真实调用链、无 stub 冒充真实证据、无 broad exception、无未声明文件越界。

## Out Of Scope

- 不执行或修改任何 AWS 资源。
- 不扩大 `AUTO_HEAL`、destructive approval 或 Skill runtime 权限。
- 不在 CI 中自动提交长期规则、AGENTS.md、ADR 或 failure-patterns。
- 不引入数据库、消息队列或第三方依赖；使用 stdlib + 现有 GitHub Actions。
- 不实现模型训练或自动生成新 Skill。
- 不追求“全自动递归自我修改”；本轮只闭合可审计证据链。

## Further Notes

- 当前历史 ADR 声明 auto-promotion=0%，而代码已有 tiered auto-promote。实现阶段以 fail-closed shadow 为默认；契约同步由主 Agent 在集成阶段处理。
- 当前本地 GCL traces 主要为 self-test stub，修复后应诚实显示 0 real traces，而不是补造生产数据。
- 当前 golden baseline/current 双份数据只用于验证去重；不得把 baseline 当作新增生产样本。
