# k8s-workload-ops Pilot — 执行计划 (Plan)

> 依据 [`specs/2026-07-26-k8s-workload-ops-design.md`](../specs/2026-07-26-k8s-workload-ops-design.md)。
> 每个任务带验收标准;完成即勾选。

## Phase 0 — 骨架落地

- [ ] **T1** 建目录 `k8s-workload-ops/{references,assets}/`
- [ ] **T2** 写 `k8s-workload-ops/SKILL.md`
  - 验收:单 `---` frontmatter 块;`type: base` + `provides`(6 op);Trigger 双向;
    Variable Convention(D2 变量);6 op 各含 Pre-flight→Execute→Validate→Recover 概览;
    破坏性 op 含确认串(D3);≤120 行(TE G1)。
- [ ] **T3** 写 `references/mcp-usage.md`(MCP-first 主路径)
  - 验收:6 op 的 MCP 工具映射;工具名与 `GetMcpTools(user-hdops_mcp)` 实际一致;
    参数用 `{{user.*}}` 占位;不硬编码返回 schema(TE-1)。
- [ ] **T4** 写 `references/kubectl-usage.md`(兜底 + 变更安全门)
  - 验收:只读兜底命令 + 3 个变更 op 的 kubectl 命令 + 确认串门禁;`--dry-run=client` 预演。
- [ ] **T5** 写 `references/core-concepts.md`(工作负载治理 checklist,对齐 JD #3)
- [ ] **T6** 写 `references/troubleshooting.md`(紧凑错误表,TE G6)
- [ ] **T7** 写 `assets/example-config.yaml`(YAML anchors,`{{env.*}}`/`{{user.*}}`)

## Phase 1 — 可运行 check + 自审

- [ ] **T8** 写 `k8s-workload-ops/golden-scenarios.yaml`(≥5 场景,§16 矩阵)
  - 验收:`python3 scripts/golden_eval.py run --skill k8s-workload-ops
    --scenarios k8s-workload-ops/golden-scenarios.yaml` 可解析并跑通(= ponytail 的"一个可运行 check")。
- [ ] **T9** R1 结构自审(Charter C1–C6 + TE G1–G6)+ 修复
- [ ] **T10** R2 内容自审(MCP 工具名核对 + 安全门 + 链接完整 + 去重)+ 修复
- [ ] **T11** CADL 沉淀:把"MCP-first + 变更 kubectl-only"模式记入本 plan 结论;
    若发现可复用 pitfall 写 `docs/failure-patterns.md`。

## 验收门(Phase 完成后一次性全量复查)

1. 结构:markdown 表格/围栏闭合,frontmatter 单块。
2. 一致性:MCP 工具名 vs 实际、路径 vs 现有 skill 惯例。
3. 范围:`git status` 仅含 `k8s-workload-ops/` + 2 个 docs。
4. 门禁:SKILL.md ≤120 行,golden_eval 可跑。
