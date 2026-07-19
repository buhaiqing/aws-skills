# CodeGraph vs Grep 交互质量 A/B 实验记录

> 落盘日期：2026-07-19
> 一句话摘要：本实验用真实 A/B 数据决定「是否采用 CodeGraph MCP」来提升 agent↔user 交互质量；结论不是二选一，而是「**按文件类型强制分流**」。

## 1. 背景与目标（Why）

本仓库 `aws-skills` 是一组 AWS 技能 Markdown runbook + 少量 AIOps Python 脚本。
`AGENTS.md` §12 规定：改代码前必跑 `codegraph sync .` + `codegraph explore` 做跨技能引用
校验与影响半径（blast radius）检查。CodeGraph 通过 tree-sitter 建本地 SQLite 代码符号图谱，
并以 MCP（`codegraph_explore`）或等价 CLI 集成。

但在 2026-07-19 的一次长 session 中，Agent **全程用 Grep/Bash 替代了 CodeGraph**，违反 §12。
复盘时浮现一个更深的疑问：

> **引入 CodeGraph MCP 的本质目的，是提升「整个交互的沟通质量」，从而更高质量地完成工作——
> 而不是「为了用新工具而用新工具」。**

因此，是否采用 CodeGraph、还是沿用当前 Grep 方式，**不能凭感觉（vibe）决定**，必须用**真实、
可度量、可评估、数据化**的对比实验来择优。本记录汇总该实验的设计与实测结果。

## 2. 待验证假设（H1–H4）

| ID | 假设 | 方向 |
|----|------|------|
| H1 | 对于「跨技能 Markdown 委托/路由表」类查询，CodeGraph 能正确回答 | 待验证（预期：否，因 CodeGraph 不索引 `.md`） |
| H2 | 对于「Python 代码符号影响半径」类查询，CodeGraph 比 Grep 信息更丰富（去重 + 测试覆盖标注） | 待验证（预期：是） |
| H3 | 单一工具强制（全用 CodeGraph 或全用 Grep）会导致约一半查询质量下降 | 待验证 |
| H4 | 无论哪种工具，**查询构造错误**（正则/参数写错）都会导致静默错答 | 待验证 |

## 3. 实验设计

### 3.1 被测方法

- **方法 A（当前方式 / baseline）**：`Grep` 工具 + `git grep` / `grep -rln` Bash 命令。
- **方法 B（候选方式）**：CodeGraph CLI（`codegraph explore "<symbol>"`）；与 MCP
  `codegraph_explore` 等价（§12 明确 CLI 不依赖 MCP 也可用）。

### 3.2 基础设施事实（已实测）

- 二进制：`/Users/bohaiqing/.local/bin/codegraph`（v1.1.6）。
- 索引：`.codegraph/codegraph.db` 2.15 MB，595 nodes / 1,393 edges，今天 16:02 更新。
- `.mcp.json` 已声明 `codegraph` stdio MCP server。
- **关键局限（实测）**：CodeGraph 用 tree-sitter 建**代码**符号图谱，**不索引 Markdown
  frontmatter**。本仓库 ~95% 是 `aws-<svc>-ops/SKILL.md` 等 Markdown，其 `metadata:` /
  `delegate:` / 委托目录引用对 CodeGraph **不可见**。

### 3.3 实验列表（3 个，覆盖交互质量维度）

| 实验 | 查询类型 | 度量指标 |
|------|----------|----------|
| **E1** 跨技能引用召回率 | Markdown 委托图（"谁引用 X？"） | recall@N、false-negative 数、耗时 |
| **E2** 代码影响半径 | Python 符号调用点（"X 的 caller？"） | 调用者去重数、是否含测试覆盖标注、耗时 |
| **E3** 端到端路由质量 | 5 个混合查询（3 Markdown + 2 Python） | 是否路由到正确工具、最终答案是否正确 |

### 3.4 真值（Ground Truth）构造方式

- E1/E3 的 Markdown 真值：用 `git grep -l "PATTERN" -- 'aws-*-ops/SKILL.md'` 独立统计。
- E2 的代码真值：用 `grep -rn "SYMBOL(" --include=*.py` 独立统计原始调用点行数。

## 4. 执行结果（实测数据 — 最终纠正版）

> 所有数字均来自本 session 的 `Bash` / `Grep` / `codegraph` CLI 真实输出，非估计。
> 下表是最终纠正版，以这组数字为准。

### 4.1 E1 — 跨技能引用召回率（"哪些 skill 引用 aws-aurora-ops？"）

真值 = **4 个**（`aws-aurora-ops` / `aws-cloudwatch-ops` / `aws-ram-ops` / `aws-rds-ops`）。

| 方法 | 结果 | 耗时 | 正确性 |
|------|------|------|--------|
| **方法 A (Grep)** | 同上 4 个，完全一致 | **0.028s** | ✅ recall 4/4，0 漏报 |
| **方法 B (CodeGraph explore)** | 返回 "Found 36 symbols across 3 files"（`collect_aws_native_insights` / `run_aws` / `extract_supported_ops` 等**代码符号**） | 0.448s | ❌ 对实际 Markdown 委托问题 **0/4** —— 结构性失明 |

**结论 E1**：Markdown 委托图查询，Grep 正确且快；CodeGraph 结构性失明（不索引 `.md`）。

### 4.2 E2 — 代码影响半径（"make_incident 的调用者？"）

| 方法 | 结果 | 耗时 | 正确性 |
|------|------|------|--------|
| **方法 A (Grep)** | 73 行原始匹配（含 12 测试行）→ 59 个非测试调用点，**未去重、无测试标注** | 0.180s | ✅ 但需人工分组 |
| **方法 B (CodeGraph)** | **42 个去重调用者**跨 11 文件 + `⚠️ no covering tests found` 标注 + 按文件聚合 | **0.134s** | ✅ **信息更丰富** |

**结论 E2**：Python 代码符号影响半径，CodeGraph 严格更优（语义去重分组 + 测试覆盖标注，Grep 缺失）。

### 4.3 E3 — 端到端路由质量（5 个混合查询）

| 查询 | 类型 | 正确工具 | 方法 A (Grep) | 方法 B (CodeGraph) |
|------|------|----------|----------------|---------------------|
| Q1 哪些 skill 委托 aws-s3-ops | Markdown | Grep | ✅ 17 个（0.03s） | ❌ 返回代码符号，答不了 |
| Q2 run_aws 调用者 | Python | CodeGraph | 71 原始行 | ✅ 61 去重调用者 + 测试标注 |
| Q3 ec2 是否引用 vpc | Markdown | Grep | ✅ YES | ❌ 失明 |
| Q4 collect_aws_native_insights 半径 | Python | CodeGraph | 原始行 | ✅ 9 调用者 + 测试标注 |
| **Q5 列出 type: composite/orchestrator-meta 的 skill** | Markdown | Grep | ⚠️ 见下方关键发现 | ❌ 失明 |

**关键发现 E3-Q5（修正版）**：Agent 用 glob `aws-*-ops` 漏匹配 `aws-aiops-orchestrator`
（该目录无 `-ops` 后缀），导致静默漏报；**真值 = 2 个**
（`aws-elb-ops/assets/example-config.yaml` + `aws-aiops-orchestrator/SKILL.md`），
并非先前记的 0/1。CodeGraph 同样失明。**结论：查询写错（glob/正则）比工具选错更隐蔽，与工具无关。**

## 5. 最终决策（数据驱动）

采纳「**按文件类型强制分流**」策略（非单一工具强制）：

| 查询 / 改动类型 | **强制**工具 | 禁用 | 理由（实测） |
|---------------|------------|------|----------------|
| `aws-*-ops/SKILL.md` / `references/*.md` / `AGENTS.md` 的 frontmatter、委托表、路由表 | **Grep / `git grep`** | ❌ 不得走 CodeGraph | CodeGraph 不索引 `.md`，E1 实测 0/4 |
| `*.py`（`_inference.py` / `_shared.py` / collectors / `gcl_runner.py` / `daily-health-check.py`）影响半径 / 调用点 | **`codegraph sync .` + `codegraph explore`** | ❌ 不得仅用 Grep 了事 | E2 实测 CodeGraph 多给去重 + 测试覆盖标注 |
| **任何查询** | 查询必须**正确构造** | ❌ 不得用错误正则/参数蒙混 | E3-Q5：本人正则写错致漏报 1，与工具无关 |

**落地动作（已 commit）**：该分流已作为**强制门禁**写入 `AGENTS.md` §12，内嵌 E1–E3 证据表，
将分流从"建议"升级为"强制门禁"。相关 commit：`d1f0daa`（§12 适用边界）+ `4d77f57`（强制分流门禁，含 A/B 证据）。
本实验结论**验证**了此前已沉淀的 §12 适用边界小节（非推翻）。

**执行纪律（用户硬约束）**：一旦本分流决策确定，**后续每一个动作严格贯彻** —— 凡 Markdown 技能类查询一律
Grep、凡 Python 代码类影响半径一律 CodeGraph，不得凭习惯回退到单一工具。违反即视为质量回归。

## 6. 一句话总结

CodeGraph 不是"该用没用"的失误，而是**用对了工具但误以为该用另一个** —— 本仓库 95% 是 Markdown，
CodeGraph（代码索引）恰是其盲区；Python 脚本才该走它。数据证明：单一工具强制会让一半查询质量下降，
**分流**才是质量最优解。
