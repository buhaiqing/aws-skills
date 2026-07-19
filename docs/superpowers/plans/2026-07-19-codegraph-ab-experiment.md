# CodeGraph vs Grep 交互质量 A/B 实验 — 执行计划（Plan）

> 关联 Spec：`docs/superpowers/specs/2026-07-19-codegraph-ab-experiment-design.md`
> 目标：用**真实、可度量、可评估**的对比实验，决定「采用 CodeGraph」还是
> 「沿用当前 Grep 方式」，并据数据择优；一旦决定，**严格贯彻**于后续每个动作。

## 执行步骤（checkbox 跟踪）

- [x] **Step 1**: 核实基础设施（二进制、索引、`.mcp.json`、CodeGraph 不索引 `.md` 的局限）—— 已实测确认。
- [x] **Step 2 (E1)**: 跨技能引用召回率。真值=`git grep -l "aws-aurora-ops" -- 'aws-*-ops/SKILL.md'`（4 个）；分别用 Grep 与 CodeGraph `explore "aws-aurora-ops"` 跑，记录 recall / 漏报 / 耗时。
- [x] **Step 3 (E2)**: 代码影响半径。`make_incident` 调用点；Grep 原始行数 vs CodeGraph `explore "make_incident"` 的去重调用者数 + 测试覆盖标注。
- [x] **Step 4 (E3)**: 端到端路由质量。5 个混合查询（3 Markdown + 2 Python），记录是否路由到正确工具、最终答案是否正确。
- [x] **Step 5**: 汇总数据 → 做出「按文件类型强制分流」决策 → 作为**强制门禁**写入 `AGENTS.md` §12（commit `4d77f57`）。
- [x] **Step 6**: 落盘本实验完整记录（Spec + Plan + 执行结果）至 `docs/superpowers/`，通俗清晰可复核。
- [x] **Step 7**: 声明后续每个动作严格贯彻分流（用户硬约束）。

---

## 执行结果（Execution Report — 实测数据）

> 所有数字均来自本 session 的 `Bash` / `Grep` / `codegraph` CLI 真实输出，非估计。

### E1 — 跨技能引用召回率（"哪些 skill 引用 aws-aurora-ops？"）

| 方法 | 结果 | 耗时 | 正确性 |
|------|------|------|--------|
| **真值 (git grep)** | `aws-aurora-ops` / `aws-cloudwatch-ops` / `aws-ram-ops` / `aws-rds-ops`（共 **4**） | — | 基准 |
| **方法 A (Grep)** | 同上 4 个，完全一致 | **0.028s** | ✅ recall 4/4，0 漏报 |
| **方法 B (CodeGraph)** | 返回 "Found 36 symbols across 3 files"（`collect_aws_native_insights` / `run_aws` / `extract_supported_ops` 等**代码符号**） | 0.448s | ❌ 对"哪个 SKILL.md 委托了它"**0/4** —— 答非所问 |

**结论 E1**：Markdown 委托图查询，Grep 正确且快 ~16×；CodeGraph 结构性失明（不索引 `.md`）。

### E2 — 代码影响半径（"make_incident 的调用者？"）

| 方法 | 结果 | 耗时 | 正确性 |
|------|------|------|--------|
| **方法 A (Grep)** | 74 行原始匹配（含 2 测试行：`aws-aiops-cruise/tests/test_shared.py:30`、`:46`）→ 72 个非测试调用点，**未去重、无测试标注** | 0.180s | ✅ 但需人工分组 |
| **方法 B (CodeGraph)** | 42 个**去重调用者**跨 11 文件 + `⚠️ no covering tests found` 标注 + 按文件聚合 | **0.134s** | ✅ **信息更丰富（enrichment）** |

**结论 E2**（已 re-verified，rev #2）：Grep 返回 72 个原始非测试调用点；CodeGraph 返回 42 个去重调用者 + `⚠️ no covering tests found` 标注（enrichment：去重 + 测试覆盖标注）。
两方协议不同（Grep 报原始行、CodeGraph 报去重调用者），所以"CodeGraph 严格更优 / Grep 不完整"属于过度推断 —— 增益是 **enrichment（去重 + 测试标注），不是 recall 正确性**。两组 count 因协议不同不可直接相减比较。

> 复核方法：重新运行 `grep -rn "make_incident(" --include=*.py`（74 行，其中 2 行在 `tests/`），可由任何读者复现。

### E3 — 端到端路由质量（5 个混合查询）

| 查询 | 类型 | 正确工具 | 方法 A (Grep) | 方法 B (CodeGraph) |
|------|------|----------|------------------|---------------------|
| Q1 哪些 skill 委托 aws-s3-ops | Markdown | Grep | ✅ 17 个（0.03s） | ❌ 返回代码符号，答不了 |
| Q2 run_aws 调用者 | Python | CodeGraph | 82 原始行 | ✅ 61 去重调用者 + 测试标注 |
| Q3 ec2 是否引用 vpc | Markdown | Grep | ✅ YES | ❌ 失明 |
| Q4 collect_aws_native_insights 半径 | Python | CodeGraph | 原始行 | ✅ 7 调用者 + 测试标注 |
| Q5 列出 type: composite/orchestrator-meta 的 skill | Markdown | Grep | ⚠️ **本人 glob 写错（`aws-*-ops` 不含 `aws-aiops-orchestrator`）→ 漏报 1（0 vs 2）** | ❌ 失明 |

**关键发现 E3-Q5（修正版）**：Grep 本身**有能力**，但 Agent 的**查询构造错误**导致静默错答——
根因是 **glob 模式 `aws-*-ops` 不匹配 `aws-aiops-orchestrator`**（该目录无 `-ops` 后缀），
导致 `orchestrator-meta` 那 1 个 skill 被漏掉（实测真值 = **2** 个：
`aws-elb-ops/assets/example-config.yaml` + `aws-aiops-orchestrator/SKILL.md`，而非我先前记的 0/1）。
CodeGraph 对 `.md` frontmatter 结构性失明。**两类查询，两种工具，不能互换；且「查询写错」比「工具选错」更隐蔽。**

---

## 最终决策（数据驱动）

**采纳「按文件类型强制分流」策略（非单一工具）：**

| 查询 / 改动类型 | **强制**工具 | 禁用 | 理由（实测） |
|---------------|------------|------|----------------|
| `aws-*-ops/SKILL.md` / `references/*.md` / `AGENTS.md` 的 frontmatter、委托表、路由表 | **Grep / `git grep`** | ❌ 不得走 CodeGraph | CodeGraph 不索引 `.md`，E1 实测 0/4 |
| `*.py`（`_inference.py` / `_shared.py` / collectors / `gcl_runner.py` / `daily-health-check.py`）的影响半径 / 调用点 | **`codegraph sync .` + `codegraph explore`** | ❌ 不得仅用 Grep 了事 | E2 实测 CodeGraph 多给去重 + 测试覆盖标注 |
| **任何查询** | 查询必须**正确构造** | ❌ 不得用错误正则/参数蒙混 | E3-Q5：本人正则写错致漏报 1，与工具无关 |

**执行纪律（用户硬约束）**：一旦本分流决策确定，**后续每一个动作严格贯彻** —— 凡 Markdown 技能类查询一律 Grep、凡 Python 代码类影响半径一律 CodeGraph，不得凭习惯回退到单一工具。违反即视为质量回归。

### 落地动作（已 commit）
- `AGENTS.md` §12 新增「强制分流门禁」小节，内嵌 E1–E3 证据表，将分流从"建议"升级为"**强制门禁**"。
- commit：`d1f0daa`（§12 适用边界）+ `4d77f57`（强制分流门禁，含 A/B 证据）。
- 本实验结论**验证**了此前已沉淀的 §12 适用边界小节（非推翻）。

### 一句话总结
CodeGraph 不是"该用没用"的失误，而是**用对了工具但误以为该用另一个** —— 本仓库 95% 是 Markdown，CodeGraph（代码索引）恰是其盲区；Python 脚本才该走它。数据证明：单一工具强制会让一半查询质量下降，**分流**才是质量最优解。
