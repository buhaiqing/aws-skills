# CodeGraph vs Grep 交互质量 A/B 实验 — 设计文档（Spec）

> 落盘日期：2026-07-19
> 作者：bohaiqing + CodeBuddy Code（协同）
> 关联 plan：`docs/superpowers/plans/2026-07-19-codegraph-ab-experiment.md`

## 1. 背景与动机（Why）

本仓库 `aws-skills` 是一组 AWS 技能 Markdown runbook + 少量 AIOps Python 脚本。
`AGENTS.md` §12 规定：改代码前必跑 `codegraph sync .` + `codegraph explore` 做跨技能
引用校验与影响半径（blast radius）检查。CodeGraph 通过 tree-sitter 建本地 SQLite
代码符号图谱，并以 MCP（`codegraph_explore`）或等价 CLI 集成。

但在 2026-07-19 的一次长 session 中，Agent **全程用 Grep/Bash 替代了 CodeGraph**，
违反 §12。复盘时发现一个更深的疑问：

> **引入 CodeGraph MCP 的本质目的，是提升「整个交互的沟通质量」，从而更高质量地
> 完成工作——而不是「为了用新工具而用新工具」。**

因此，是否采用 CodeGraph、还是沿用当前 Grep 方式，**不能凭感觉（vibe）决定**，
必须用**真实、可度量、可评估、数据化**的对比实验来择优。本 Spec 定义该实验的设计。

## 2. 待验证的假设（Hypotheses）

| ID | 假设 | 方向 |
|----|------|------|
| H1 | 对于「跨技能 Markdown 委托/路由表」类查询，CodeGraph 能正确回答 | 待验证（预期：否，因 CodeGraph 不索引 `.md`） |
| H2 | 对于「Python 代码符号影响半径」类查询，CodeGraph 比 Grep 信息更丰富（去重 + 测试覆盖标注） | 待验证（预期：是） |
| H3 | 单一工具强制（全用 CodeGraph 或全用 Grep）会导致约一半查询质量下降 | 待验证 |
| H4 | 无论哪种工具，**查询构造错误**（正则/参数写错）都会导致静默错答 | 待验证 |

## 3. 实验设计（已核实磁盘的事实）

### 3.1 被测对象
- **方法 A（当前方式 / baseline）**：`Grep` 工具 + `git grep` / `grep -rln` Bash 命令。
- **方法 B（候选方式）**：CodeGraph CLI（`codegraph explore "<symbol>"`）；与 MCP
  `codegraph_explore` 等价（§12 明确 CLI 不依赖 MCP 也可用）。

### 3.2 基础设施核实（已实测）
- 二进制：`/Users/bohaiqing/.local/bin/codegraph`（v1.1.6）。
- 索引：`.codegraph/codegraph.db` 2.15 MB，595 nodes / 1,393 edges，今天 16:02 更新。
- `.mcp.json` 已声明 `codegraph` stdio MCP server。
- **关键局限（实测）**：CodeGraph 用 tree-sitter 建**代码**符号图谱，
  **不索引 Markdown frontmatter**。本仓库 ~95% 是 `aws-<svc>-ops/SKILL.md` 等
  Markdown，其 `metadata:` / `delegate:` / 委托目录引用对 CodeGraph **不可见**。

### 3.3 实验列表（3 个，覆盖交互质量维度）
| 实验 | 查询类型 | 度量指标 |
|------|----------|----------|
| **E1** 跨技能引用召回率 | Markdown 委托图（"谁引用 X？"） | recall@N、false-negative 数、耗时 |
| **E2** 代码影响半径 | Python 符号调用点（"X 的 caller？"） | 调用者去重数、是否含测试覆盖标注、耗时 |
| **E3** 端到端路由质量 | 5 个混合查询（3 Markdown + 2 Python） | 是否路由到正确工具、最终答案是否正确 |

### 3.4 真值（Ground Truth）构造方式
- E1/E3 的 Markdown 真值：用 `git grep -l "PATTERN" -- 'aws-*-ops/SKILL.md'` 独立统计。
- E2 的代码真值：用 `grep -rn "SYMBOL(" --include=*.py` 独立统计原始调用点行数。

## 4. 度量与验收（Metrics）

| 维度 | 度量 | 胜出判据 |
|------|------|----------|
| 正确性 | recall（找到的真值比例）、false-negative | 越高越好 |
| 信息密度 | 是否去重、是否标注「无测试覆盖」 | CodeGraph 预期占优（代码类） |
| 耗时 | 端到端 wall-clock（含工具选择） | 差距 <0.2s 时视为可忽略 |
| 交互风险 | 是否静默返回答非所问 / 漏报 | 越低越好（H4：查询写错时两者都危险） |

## 5. 范围边界（Scope）

- **In scope**：上述 3 个实验 + 数据化结论 + 据此做出的采纳/分流决策。
- **Out of scope**：给 CodeGraph 加 Markdown frontmatter 提取器（那会使 CodeGraph 覆盖
  技能 corpus，是独立 plan）；任何业务技能或 AIOps 脚本的功能改动。
- 本实验**不改变**任何技能代码；只读取磁盘状态并测量。

## 6. 预期产出（Deliverable）

1. 一份**完整的实验记录**（Spec + Plan + 执行结果），落盘于
   `docs/superpowers/`，以通俗、清晰、可复核的方式呈现。
2. 一个**数据驱动的决策**：采纳「按文件类型强制分流」策略，并作为**强制门禁**
   写入 `AGENTS.md` §12（而非建议）。
3. 后续每个动作**严格贯彻**该分流（用户硬约束）。
