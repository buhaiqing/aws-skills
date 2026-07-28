# TE Gate C6 Debt — Pilot Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:test-driven-development`.
> 任何代码改动前必走 **RED → GREEN → REFACTOR**；测试有效性 > 覆盖率。
>
> **Spec**: `docs/superpowers/specs/2026-07-28-te-gate-c6-debt-design.md`
> **Scope**: Pilot batch (2 skills) — `aws-cloudwatch-ops` (light) + `aws-ram-ops` (heavy) + `scripts/te_gate.py` regex tightening + new `scripts/tests/test_te_gate.py`.

**Goal**: 取 2 个形态不同的 skill 验证 SKILL.md 拆解模板 + te_gate.py 正则扩展，2/37 跑出 G1+G3 双绿；为 P0-B 批量铺到 35 个 skill 沉淀可复用模式。

**Architecture**:
- `scripts/te_gate.py` —— 扩展 `JSON_PATH_LINE_RE` 接受 `# Label: .path.{...}` 与 `;` / `→` 分隔的多路径
- `scripts/tests/test_te_gate.py` —— 新增 6+ 测试覆盖正向 / 负向 / 边界
- `aws-cloudwatch-ops/SKILL.md` —— 135 → ≤120 行 + G3 块改写
- `aws-ram-ops/SKILL.md` —— 666 → ≤120 行
- `aws-ram-ops/references/operations.md` —— 新增；收纳 14 个 Operation 块

**Tech Stack**: Python 3.12 stdlib, regex, pytest, ruff.

---

## 通用纪律

1. **RED**: 写 6+ 个 `test_te_gate.py` 测试，**针对真实 fixture**（不复用 mock）。先跑出失败截屏。
2. **VERIFY RED**: 跑 `pytest scripts/tests/test_te_gate.py -x`，确认每个测试因 `feature missing` 失败（不是 typo）。
3. **GREEN**: 写**最小** `te_gate.py` 改动让测试过；不动 `gate_skill` / `main` 接口。
4. **VERIFY GREEN**: 跑 `te_gate.py aws-cloudwatch-ops --strict` 和 `aws-ram-ops --strict`，全绿。
5. **REFACTOR**: 在保持绿的前提下统一两个 pilot skill 的 G3 块格式。
6. **反模式**:
   - 不要 mock `te_gate.gate_skill` 本身
   - 不要把 G1/G4 逻辑顺手改掉
   - 不要在不改 tests 的前提下动 `JSON_PATH_LINE_RE` 之外的正则

---

## Task T1 — `scripts/te_gate.py` 扩展 + new `test_te_gate.py`

### T1.1 RED: 写 6 个失败测试

- [ ] `test_g3_accepts_simple_key_equals_path` — `key = .path.foo` → 1 path
- [ ] `test_g3_accepts_label_prefixed_path` — `# Label: .path.{key1,key2}` → 1 path, 且 dedupe 后续行不算
- [ ] `test_g3_accepts_multi_path_line_split_on_semicolon` — `key1 → .a; key2 → .b` → 2 paths
- [ ] `test_g3_rejects_empty_after_strip` — `key = .path` 后跟空行 → 仍然算 empty block
- [ ] `test_g3_dedupes_repeated_paths` — 同一 path 出现 2 行 → 算 1 path
- [ ] `test_g3_body_dupe_still_caught_for_new_format` — body 出现 `# Label: .path.foo` → 仍判 title

### T1.2 GREEN: 最小实现

- [ ] `JSON_PATH_LINE_RE` 扩展（增加 `# Label: .path.{...}` 与 `;` / `→` split）
- [ ] 在 `check_g3` 中 split line 为 `sublines`，每个 subline 独立匹配
- [ ] `declared_tokens` 收集时按 subline 收集
- [ ] `body_dupe` 检查保持现状（已经覆盖 `.path` 字符串）

### T1.3 REFACTOR

- [ ] 提取 `_iter_path_declarations(header_block_lines) -> list[str]` helper
- [ ] 提取 `_extract_path_token(line) -> str | None` 集中正则

### T1 验收

- [ ] RED + GREEN 截屏
- [ ] `python3 -m pytest -p no:rerunfailures scripts/tests/test_te_gate.py -v` 全绿
- [ ] `python3 scripts/te_gate.py aws-cloudwatch-ops --strict` 仍 FAIL（G3 还没改 skill）
- [ ] `python3 scripts/te_gate.py aws-ram-ops --strict` 仍 FAIL

---

## Task T2 — Pilot A: `aws-cloudwatch-ops`

### T2.1 RED: 记录 RED 状态

- [ ] `te_gate.py aws-cloudwatch-ops --strict` 当前 FAIL（G1: 135 > 120; G3: empty header）
- [ ] 记录失败原因在 PR body

### T2.2 GREEN: 改 SKILL.md

- [ ] 改 `## Common JSON Paths` 块：每行一个 `key = .path` 形式
- [ ] 压缩 `## Reference Files` 列表 → 单行（每 ref 一行）
- [ ] 检查 `wc -l aws-cloudwatch-ops/SKILL.md` ≤ 120
- [ ] 跑 `te_gate.py aws-cloudwatch-ops --strict` 期望 0

### T2.3 REFACTOR

- [ ] 与 Task T3 统一 G3 块格式
- [ ] 跑全量 pytest + ruff 不退化

### T2 验收

- [ ] `wc -l aws-cloudwatch-ops/SKILL.md` ≤ 120
- [ ] `te_gate.py aws-cloudwatch-ops --strict` exit 0
- [ ] G3 / G4 仍 PASS

---

## Task T3 — Pilot B: `aws-ram-ops`（heavy）

### T3.1 RED: 记录 RED 状态

- [ ] `te_gate.py aws-ram-ops --strict` 当前 FAIL（G1: 666 > 120; G3: empty header）
- [ ] `grep -c "^### Operation:" aws-ram-ops/SKILL.md` 记录 14 个 Operation 块

### T3.2 GREEN: 提取 operations.md + 简化 SKILL.md

- [ ] 新增 `aws-ram-ops/references/operations.md`
  - 包含：Pre-flight (Step 1/2/3 表) + 14 个 Operation 块（Create / Associate / Disassociate / Accept / Reject / Promote / Create Permission / Associate Permission / Delete Resource Share / Delete Permission / Delete Permission Version / List + 其余 4 个）
  - 用 `## Operation: <name>` 二级标题保留锚点
- [ ] 改 `aws-ram-ops/SKILL.md`:
  - `## Common JSON Paths` 块按 G3 格式重写
  - `## Config File Placeholders` 段（行 109–125）→ 移到 `references/operations.md#config-placeholders`
  - `## Execution Flow Pattern` 段（行 126–545）→ 保留首段说明 + 链接，Pre-flight 步骤表移到 `operations.md`
  - `## Operations Index` 表（新增）→ 链向 `operations.md` 各锚点
  - 删除已迁出的内容
- [ ] `wc -l aws-ram-ops/SKILL.md` ≤ 120
- [ ] `wc -l aws-ram-ops/references/operations.md` 不限（参考 aws-ram-ops/references/aws-cli-usage.md 140 行基线）

### T3.3 REFACTOR

- [ ] 在 SKILL.md 头部 `## Operations Index` 表给每个 Operation 一行：`| <name> | [operations.md#<anchor>](references/operations.md#<anchor>) |`
- [ ] `references/operations.md` 顶部加 `<!-- upstream: aws-ram-ops/SKILL.md §Operation: <name> -->` 标注来源

### T3 验收

- [ ] `wc -l aws-ram-ops/SKILL.md` ≤ 120
- [ ] `te_gate.py aws-ram-ops --strict` exit 0
- [ ] `grep -c "^## Operation:" aws-ram-ops/references/operations.md` == 14 (原 SKILL.md 数量)
- [ ] SKILL.md 不再含 `aws ram create-resource-share` 等完整命令（这些都在 references/）

---

## Task T4 — 串行收尾 + 验证

- [ ] **P1 — 全量验证**:
  - `python3 -m pytest -p no:rerunfailures scripts/tests/ -q` → 全绿
  - `ruff check .` → clean
  - `python3 scripts/composite_lint.py lint --all` → exit 0
  - `python3 scripts/cross_runtime_lint.py lint --all --json` → min score 1.0
  - `python3 scripts/self_review.py verify` → stale_p0=0
  - `python3 scripts/te_gate.py --all --strict` → 35/37 FAIL（预期）；本 pilot 仅承诺 2/37 → PASS
- [ ] **P2 — Self-Reflection R1 (结构)**: AGENTS.md "Self-reflection rule" 表 R1 范围，跑 Charter C1–C6 + TE-1…TE-6 + frontmatter 单块校验 + delegation 引用 + 破坏性操作确认
- [ ] **P3 — Self-Reflection R2 (内容)**: CLI 验证 / 错误码 / 安全门禁 / 链接完整 / dedup
- [ ] **P4 — Self-Reflection R3 (Cross-cutting)**: 拆解模板如在 2 个 pilot 都成立，记录到
  `docs/superpowers/reports/te-gate-c6-debt-pilot-2026-07-28.md` + 1 lesson 写
  `docs/superpowers/learnings.md`（如该文件不存在则创建）
- [ ] **P5 — Worktree 决策**: 单 commit 不强求 worktree；如果是 worktree 模式，merge 路径：
  - `git worktree add ../aws-skills-p0a-tegate feature/te-gate-c6-debt-pilot`
  - 切换目录工作，merge 时 `git merge --no-ff feature/te-gate-c6-debt-pilot`
- [ ] **P6 — commit & push**: 单 commit, message:
  `feat(te-gate): C6 debt pilot — 2 skills pass te_gate --strict (aws-cloudwatch-ops light, aws-ram-ops heavy split)` 

## Token Budget

预估新增 < 350 行（operations.md 提取 +250，测试 +60，te_gate.py 微调 +40，其他 -20）。
整体净增 < 200 行。
