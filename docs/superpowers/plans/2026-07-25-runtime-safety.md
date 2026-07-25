# P2.1 Runtime Safety Guardrail 执行计划 (TDD 强制)

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:test-driven-development`。
> 任何代码改动前必须 **RED → GREEN → REFACTOR**；测试有效性 > 覆盖率。

**Goal**: 落地 Spec `2026-07-25-runtime-safety-design.md`，提供运行时 destructive op 拦截。

**Architecture**:
- `scripts/runtime_safety.py` (~250 行 production)
- `scripts/tests/test_runtime_safety.py` (~200 行, 7 测试)
- AGENTS.md 新增 §15 "Runtime Safety Hook Protocol" 段落
- 端到端验证: 先用 reflexion 累计 ≥3 次 terminate 失败模式, 再用 runtime_safety 真阻断

**Tech Stack**: Python 3.12 (stdlib + PyYAML), pytest, ruff.

---

## Task T1 — `scripts/runtime_safety.py` 核心库

### T1.1 RED: 写 7 个失败测试

- [ ] `test_load_patterns_parses_markdown` — load 真实 docs/failure-patterns.md fixture (用 tmp_path 副本)
- [ ] `test_check_call_allow_for_readonly` — `aws s3 ls` → ALLOW
- [ ] `test_check_call_warn_for_destructive_without_confirm` — `terminate-instances` 无 confirm → WARN
- [ ] `test_check_call_allow_with_confirm_and_no_pattern` — `terminate-instances` 有 confirm 无 pattern → ALLOW
- [ ] `test_check_call_block_when_matches_high_freq_pattern` — `terminate-instances` 无 `--instance-ids` 已记录 count=5 → BLOCK
- [ ] `test_check_call_warn_with_low_freq_pattern_match` — 同上但 count=1 → WARN (suggest confirm)
- [ ] `test_cli_stdin_stdout_e2e` — 真 subprocess, 喂 JSON to stdin, 解析 stdout, 验 decision/exit code

### T1.2 GREEN: 最小实现

- [ ] `@dataclass ToolCall`: tool_name/args/is_destructive/safety_confirm
- [ ] `@dataclass CheckResult`: decision/reason/matched_patterns
- [ ] `load_failure_patterns(path) -> list[FailurePattern]`: 复用 _reflexion 的 table parser
- [ ] `check_tool_call(call, patterns) -> CheckResult`: 4 决策分支
- [ ] `main(argv)`: argparse + stdin JSON 读 + stdout JSON 写 + exit code 映射

### T1.3 REFACTOR

- [ ] 提取 `_is_destructive(tool_name)` 静态判断 (delete/terminate/detach/revoke/disable)
- [ ] 提取 `_match_score(call, pattern)` 模糊匹配 (tool_name + args keys 重叠)
- [ ] ruff 0 issue
- [ ] pytest 仍绿

### T1 验收

- [ ] 7 测试全绿
- [ ] ruff 0 issue
- [ ] 端到端: 喂 `{"tool_name":"aws ec2 terminate-instances","args":{},"is_destructive":true}` + 真实 failure-patterns.md 含 `count>=3` 的 terminate 行 → exit 1

---

## Task T2 — AGENTS.md §15 文档化

- [ ] 追加 §15 "Runtime Safety Hook Protocol" (~50 行):
  - 决策表 (ALLOW/WARN/BLOCK 何时触发)
  - 集成示例 (OpenCode / Claude Code / Cursor 各自如何调用 pre_tool_use hook)
  - 引用 runtime_safety.py 路径

---

## 端到端真验证（必须做）

```bash
# 1. 用 _reflexion 累积 ≥3 次 terminate-instances 失败模式
for i in 1 2 3; do
  cp docs/failure-patterns.md /tmp/fp.md
  python3 scripts/gcl_runner.py --skill aws-ec2-ops --request "terminate-instances" \
    --self-test --no-prune --on-fail --failure-patterns /tmp/fp.md
  cp /tmp/fp.md docs/failure-patterns.md
done
# 现在 docs/failure-patterns.md 含 count=3 的 terminate 失败模式

# 2. 真用 runtime_safety 阻断
echo '{"tool_name":"aws ec2 terminate-instances","args":{},"is_destructive":true}' \
  | python3 scripts/runtime_safety.py --patterns docs/failure-patterns.md
echo "exit: $?"
# 应: exit 1, decision=BLOCK, reason 含 terminate-instances 失败模式

# 3. cleanup: 把 docs/failure-patterns.md 恢复
git checkout docs/failure-patterns.md  # 或其他方式
```

---

## 串行收尾

- [ ] P1 — 集成验证: 全测试套件 (33 测试) 全绿
- [ ] P2 — Token Efficiency Monitor 评审
- [ ] P3 — Self-Reflection R1 结构 + R2 内容
- [ ] P4 — 更新 maturity-model.md (L4 45% → ~55%) + TODO.md
- [ ] P5 — 更新 scripts/commit-l3-p1.sh (或新增 commit-p2.sh) — sandbox 外执行

## Token budget

总新增 ~500 行 (production + test + docs)。预计 wall-time < 20 分钟。
