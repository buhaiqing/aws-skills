# Plan: Post-M2 Optimization Backlog

**Date**: 2026-07-31  
**Status**: ✅ APPROVED — Wave A→B→C0 依次开发中（`2026-07-31` 用户批准「plan 写好后依次排期」）  
**Context**: ADR-0001 **M1/M2 工程已完成**（commit `18e35ae`）；下一官方主动路径 = **M3 Transactional**  
**SoT**: [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) · [`docs/agentic-maturity-model.md`](../../agentic-maturity-model.md)

## 1. Verdict（先读这节）

**最值得做的不是再扩 skill / 再压 TE**，而是：

1. **把 M2 从「simulate 覆盖」推到「可接线的执行前证据」**（小步 hardening）
2. **维持 / 推进 30 天 telemetry 满窗**（阻塞 AUTO_HEAL，不阻塞 M3 库代码）
3. **开 ADR M3 Transactional（DAG + compensation）**——这是稳定 L4 的下一主里程碑
4. 其余（shadow 扩写操作、CodeGraph 硬门、自动 skill 生成、M4 learning）按收益递减排期

**明确不做（本 backlog）**：无指标驱动的新 `aws-*-ops` 扩张；满窗前扩大 `AUTO_HEAL`。

---

## 2. 机会清单（按价值 / 依赖排序）

| ID | 主题 | 价值 | 依赖 | 建议窗口 |
|---|---|---|---|---|
| **O1** | M2 hardening：真实 dry-run allowlist + describe stub 注入路径文档化；proxy↔shadow 集成测试再加「region drift」 | 高（防假安全感） | 无 | 0.5–1 天 |
| **O2** | Shadow 扩到五高风险 **write**（非 destructive）子集，逼近 ADR SLO「writes ≥90%」的第一步 | 中高 | O1 可选 | 1–2 天 |
| **O3** | Telemetry 满窗：每日/CI 追加 signal；满 30 天后关 M1 ⚠️ + 解锁 AUTO_HEAL **评审**（仍不自动放宽） | 高（治理） | 日历 | 并行 / 到期关单 |
| **O4** | **ADR M3**：spec+plan → DAG 模型 → 三条链（ELB / RDS+R53 / ECS+ELB）→ 补偿也走 GCL+proxy | **最高（主路径）** | M2 ✅；满窗不阻塞编码 | 1–2 周 |
| **O5** | GCL trace 记录 `plan_hash` / `shadow.path` / `BLOCKED` 预 GCL 阻断 | 中 | O1/O4 | 随 M3 或 O1 |
| **O6** | CodeGraph pre-commit soft→hard（有 binary 才 fail；无 binary 仍 skip + warn） | 中（L3 缺口） | 无 | 0.5 天 |
| **O7** | `links_lint.py`（SR-4 anchor 检查）进 pre-commit / CI | 中低 | 无 | 0.5 天 |
| **O8** | Failure-pattern 去手工化：`_reflexion` 覆盖率报表 + 候选去重预览（为 M4 铺路，**不自动晋升**） | 中 | 无 | 1 天 |
| **O9** | ADR M4 Governed Learning（候选→replay→人工批准） | 高但靠后 | M3 + 满窗 | M3 后 |
| **O10** | 自动 skill 生成闭环（人工仅审批） | 中（非证据主线） | 独立 spec | 可并行低优 |
| **O11** | Shadow 扩到「全仓 destructive」（非五高风险） | 低–中 | O2 + 容量 | M3 后可选 |

---

## 3. 推荐执行波次（Todo Plan）

### Wave A — 快赢 hardening（批准后可立刻做，不改 ADR 主叙事）

- [x] **A1** O1：补 `test_safe_tool_proxy` region-drift；核对 dry-run allowlist 与 EC2 常见写操作一致
- [x] **A2** O5 轻量：`gcl_runner` / proxy 输出可选带上 `plan_hash`（已有则文档化）
- [x] **A3** O6：pre-commit CodeGraph 策略文档化 + 可选 hard-fail when `command -v codegraph`
- [x] **A4** O7：`scripts/links_lint.py` MVP（仅 SKILL.md `#anchor`）+ 1 个 CI step 或 pre-commit soft

**Acceptance A**: 相关 pytest 绿；不破坏 `--all-high-risk` 58/58 / shadow 27/27。

### Wave B — 证据与 telemetry（与 A/C 并行）

- [x] **B1** O3：约定 `telemetry_dashboard.py dashboard` 刷新节奏（CI artifact 或 cron 说明写进 ADR §M1 STILL OPEN）
- [ ] **B2** O3：满窗 checklist（日期、信号源、pass_rate 无告警）→ 关 M1 满窗 checkbox
- [x] **B3** O2（可选）：五高风险 `risk: write` 场景接入 `shadow_coverage`（simulate 即可）

**Acceptance B**: 满窗关闭有书面证据；write shadow 覆盖率数字写入 ADR/maturity。

### Wave C — 主路径 M3（需单独 spec+plan，本文件只排期）

- [x] **C0** 落盘 `docs/superpowers/specs/2026-07-31-adr-m3-transactional-design.md` + plan（**批准后再编码**）
- [ ] **C1** `ExecutionDAG` / 节点 `precondition|postcondition|compensation|non_compensable`
- [ ] **C2** 补偿路径强制 `safe_tool_proxy` + shadow（复用 M2）
- [ ] **C3** 三条链 fixture + 成功 / 节点失败 / 补偿失败测试
- [ ] **C4** ADR §M3 Progress + maturity next=M4

**Acceptance C**: 对齐 ADR M3 exit criteria（三条链 × 三态；不可补偿 100% MANUAL）。

### Wave D — 学习与生成（M3 后或穿插低优）

- [ ] **D1** O8 候选 pattern 去重预览 CLI（晋升率保持 0%）
- [ ] **D2** O9 M4 spec+plan
- [ ] **D3** O10 自动 skill 生成 spec（与证据主线解耦）

---

## 4. 建议默认批准范围

若只批一句话：**先做 Wave A + 开 Wave C0（M3 spec）**；Wave B 日历驱动；Wave D 暂缓。

| 批准选项 | 含义 |
|---|---|
| **A only** | 只做 hardening / lint / CodeGraph |
| **A + C0** | hardening + 写 M3 design/plan（仍不写 M3 代码） |
| **A + B3 + C0** | 加上 write-risk shadow 扩展 |
| **Full C** | 直接进入 M3 实现（仍须先有 C0 spec 定稿） |

---

## 5. 非目标（再次钉死）

- 新 AWS skill 数量扩张作为 KPI
- 满窗前 / 无 compensation 前扩大 `AUTO_HEAL`
- 改 GCL 技能文档 `confirm=` 操作员体验（M2 已锁定）
- 让 Critic / Telemetry / Learning 直接 mutate AWS

---

## 6. 验证命令（任何 Wave 收尾）

```bash
pytest -p no:rerunfailures scripts/tests/test_execution_plan.py \
  scripts/tests/test_shadow_exec.py scripts/tests/test_safe_tool_proxy.py \
  scripts/tests/test_shadow_coverage.py scripts/tests/test_runtime_safety.py -q
python3 scripts/shadow_coverage.py check --all-high-risk --shadow-dir /tmp/shadow-m2
python3 scripts/golden_eval.py run --all-high-risk --out audit-results/golden/high-risk.json
python3 scripts/te_gate.py --all --strict
```
