# k8s-workload-ops Pilot — 设计文档 (Spec)

> **Purpose**: 为 repo 引入首个**非 AWS、云中立**的运维 skill 试点,验证"同一套
> L1 runbook 结构 + Charter/GCL/CADL 纪律,可复用到 Kubernetes 工作负载治理域"。
> 对齐 SRE Leader JD #2(云原生标准 / K8s 规模化)与 #3(容器平台运行规范)。

- **作者**: 主 Agent
- **创建日期**: 2026-07-26
- **决策来源**: 2026-07-26 session,用户三选:
  1. pilot = `k8s-workload-ops`
  2. **不改 `aws-skill-generator`**(独立试点,验证后再决定是否泛化工厂)
  3. 执行/数据路径 = **MCP(`hdops_mcp`)优先,CLI/kubectl 兜底**
- **关联**:
  - `docs/agentic-maturity-model.md`(L1/L2/L4 能力基线,repo 现状 AWS-only)
  - `aws-skill-generator/references/aws-skill-template.md`(L1 SKILL.md 骨架)
  - `AGENTS.md` §Spec+Plan Before Implement / §11 GCL / §13 CADL / §14 TE Hard Gate

---

## 1. 需求 / 缺口分析(disk-verified)

盘点证据(2026-07-26 实跑):

- `ls -d aws-*-ops` → **36 个 AWS base skill**;`aws-eks-ops/SKILL.md` frontmatter 证实
  其 scope 为"托管 EKS 集群 + 基础 kubectl",**无云中立的工作负载层治理**
  (Deployment / HPA / PDB / ResourceQuota / 资源规范 / Pod 诊断闭环)。
- `ls -d *terraform* *iac* *k8s* *gitops*` → **无匹配**,确认 K8s workload / IaC 为硬缺口。
- `GetMcpTools(user-hdops_mcp, k8s|pod|loki)` → 24 个相关工具,**几乎全为只读观测**:
  `get_k8s_exception_pod` / `get_k8s_pod_resource_usage` / `get_k8s_pod_info` /
  `get_k8s_app_deployment_spec` / `get_naming_k8s_pod_events` / `get_k8s_current_alert` /
  `get_k8s_core_metrics` / `get_loki_query_range` / `get_k8s_pod_jvm_*`。
  **无变更类工具**(无 scale / rollout / delete)。

**结论**:真实环境(海鼎/爱婴室生产等 K8s 集群 + Loki + JVM)的**诊断能力已在 MCP 侧齐备**,
但缺一个把这些工具**编排成 AI-native runbook**的 skill;**变更操作**必须由 kubectl 承担并加安全门。

## 2. 目标(Scope)

一个 base(L1)skill `k8s-workload-ops`,提供以下 operation,每个走
`Pre-flight → Execute → Validate → Recover`:

| operation | 类型 | 首选路径 | 兜底路径 |
|---|---|---|---|
| `diagnose-workload` | 只读 | MCP(exception_pod + pod_resource_usage + pod_events + loki) | `kubectl describe/logs` |
| `inspect-deployment` | 只读 | MCP(`get_k8s_app_deployment_spec` + `get_naming_k8s_app_infos`) | `kubectl get deploy -o yaml` |
| `governance-audit` | 只读 | MCP(app_infos requests/limits)+ 规范规则比对 | `kubectl get` + 规则 |
| `scale-workload` | **变更** | kubectl(MCP 无变更工具) | — |
| `rollout-restart` | **变更** | kubectl | — |
| `rollback-deployment` | **变更** | kubectl | — |

## 3. 非目标(Out of Scope)

- **不改 `aws-skill-generator`**(用户决策 2):本 skill 手工按模板落地,不注册进工厂前缀约束。
- 不做 EKS 集群生命周期(create/upgrade cluster)→ 归 `aws-eks-ops`。
- 不做 CD / GitOps / 灰度发布 → 未来 `deploy-release-ops`(P1)。
- 不做 IaC / 日志平台成本治理 → 未来独立 skill(P1)。
- 不新增 MCP 变更工具(超出 repo 范围)。

## 4. 关键设计决策

### D1 — MCP-first 执行契约(区别于 AWS skill 的 CLI-first)
AWS skill 是 CLI 主 / boto3 备。本 skill **只读操作 MCP 主 / kubectl 备**,
**变更操作 kubectl 唯一**(MCP 无变更工具,fail-safe:不假造变更能力)。
`references/mcp-usage.md` 声明工具映射与参数;`references/kubectl-usage.md` 声明兜底 + 变更安全门。

### D2 — 寻址变量约定(区别于 AWS region/account)
`hdops_mcp` 按 `k8s_cluster_name`(如"爱婴室生产")+ `project/profile/stack/app` 寻址。
Variable Convention 用 `{{user.k8s_cluster_name}}` / `{{user.project}}` / `{{user.profile}}` /
`{{user.app}}`;kubectl 兜底用 `{{user.kubectl_context}}` / `{{user.namespace}}`。
**无 AWS 凭证节**;凭证由 MCP server / kubeconfig 各自持有,skill 不碰密钥(fail-closed)。

### D3 — 破坏性操作安全门(复用 Charter + GCL A-rule 精神)
`scale-workload`(尤其缩容到 0)、`rollout-restart`(全量重启)、`rollback-deployment`
必须显式人工确认;确认串 `CONFIRM SCALE <deploy> <n>` / `CONFIRM ROLLBACK <deploy>`。
运行时可接 `scripts/runtime_safety.py`(§15)对 destructive op 实时查 failure-patterns。

### D4 — 运行规范内化(对齐 JD #3"统一运行规范")
`references/core-concepts.md` 收敛一份**工作负载治理 checklist**(requests/limits 必填、
副本数下限、PDB、探针、镜像 tag 非 latest、资源利用率红线),`governance-audit` 据此比对
`get_naming_k8s_app_infos` 返回的实际配置,输出违规清单。

## 5. 验收标准

- SKILL.md 通过 Charter C1–C6 + TE G1–G6(≤120 行,单 `---` 块,Trigger 双向,变量约定,
  破坏性确认,JSON/工具路径集中声明)。
- `golden-scenarios.yaml` ≥5 场景(§16 覆盖矩阵:≥2 只读 happy path / ≥2 带确认变更 /
  ≥1 无确认变更 SAFETY_FAIL / ≥1 幂等),`scripts/golden_eval.py` 可跑 = 本 skill 的可运行 check。
- `references/mcp-usage.md` 每个引用的 MCP 工具名与 `GetMcpTools(user-hdops_mcp)` 实际一致。
- 2 轮自审(R1 结构 / R2 内容)clean。

## 6. 风险 / 权衡

- **R1**: MCP 工具签名可能随环境演进 → 缓解:mcp-usage.md 只声明工具名+关键参数,
  不硬编码返回 schema(TE-1 精神);运行时以 `GetMcpTools` 为准。
- **R2**: 变更操作只能 kubectl,若目标环境未配 kubeconfig 则变更不可用 → 缓解:
  Pre-flight 明确检查 `kubectl config current-context`,缺失则 HALT 并提示,不静默失败。
- **R3**: 试点不进工厂 → 短期一致性靠人工模板对齐;验证成功后再评估泛化 generator(用户决策 2)。
