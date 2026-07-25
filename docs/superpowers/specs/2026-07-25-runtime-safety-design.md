# Runtime Safety Guardrail — 设计文档 (L4 #6)

- **日期**: 2026-07-25
- **状态**: 定稿 (待实施)
- **优先级**: P2 第一件
- **关联**: `docs/agentic-maturity-model.md` §6.4 ❌ Gap #3 (运行时 Guardrail)

## 1. 背景

当前 A1–A16 安全规则在 `gcl_runner.py` 编译时强制（生成阶段）。但**真正执行 destructive op 时**（运行时）没有任何兜底——如果 Agent 直接绕过 GCL 调用 `aws ec2 terminate-instances`，A1–A16 不会被检查。

并且 `docs/failure-patterns.md` 里有历史上高频失败模式（如 `terminate-instances` 缺 `--instance-ids` 4 次），但 L4 的"自动沉淀 → 下次避免"闭环只到写文件为止，**没有自动拦截**。

## 2. 目标

新增 `scripts/runtime_safety.py`，提供：
1. **库函数** `check_tool_call(call, patterns) -> CheckResult`：匹配待执行操作与已知失败模式
2. **CLI**: stdin 喂 tool call JSON, stdout 输出 decision JSON
3. **Agent hook 协议**: 任何 agent（OpenCode / Claude Code / OpenClaw）可在 `pre_tool_use` 时调用

## 3. 契约

```python
@dataclass
class ToolCall:
    tool_name: str            # "aws ec2 terminate-instances" 或 "boto3.ec2.terminate_instances"
    args: dict                # 解析后的参数 (e.g., {"instance_ids": ["i-xxx"]})
    is_destructive: bool      # 静态判断 (delete/terminate/detach/revoke/disable)
    safety_confirm: str = ""  # 用户提供的 confirm token (L4 #4 同款)

@dataclass
class CheckResult:
    decision: Literal["ALLOW", "WARN", "BLOCK"]
    reason: str
    matched_patterns: list[FailurePattern]

def load_failure_patterns(path: Path) -> list[FailurePattern]: ...
def check_tool_call(call: ToolCall, patterns: list[FailurePattern]) -> CheckResult: ...
def main(argv: list[str] | None = None) -> int: ...

# 决策规则:
# - 非 destructive → ALLOW
# - destructive + 无 confirm → WARN (要求 confirm)
# - destructive + confirm + 无匹配 pattern → ALLOW
# - destructive + 任意来源 + 匹配 high-freq pattern (count >= 3) → BLOCK
# - destructive + confirm + 匹配 low-freq pattern (count < 3) → WARN (suggest confirm)
```

## 4. Agent 集成 (pre_tool_use hook 协议)

每个 agent 需在 `pre_tool_use` 阶段调用 `runtime_safety.py --json`：
```bash
echo '{"tool_name":"aws ec2 terminate-instances","args":{"instance_ids":["i-xxx"]},"is_destructive":true}' \
  | python3 scripts/runtime_safety.py --patterns docs/failure-patterns.md
# stdout: {"decision":"ALLOW|WARN|BLOCK", "reason":"...", "matched_patterns":[...]}
# exit 0 = ALLOW, 1 = BLOCK, 2 = WARN (caller can decide)
```

## 5. 验收 (硬指标)

1. `python3 -c "from runtime_safety import check_tool_call"` 可导入
2. 测试覆盖:
   - test_load_patterns_parses_markdown
   - test_check_call_allow_for_readonly
   - test_check_call_warn_for_destructive_without_confirm
   - test_check_call_block_when_matches_high_freq_pattern
   - test_check_call_allow_with_confirm_and_no_pattern
   - test_check_call_warn_with_low_freq_pattern_match
   - test_cli_stdin_stdout_e2e
3. ruff 0 issue
4. CLI 真跑: 故意构造 `terminate-instances` with no `--instance-ids` → exit 1 (BLOCK after reflexion has accumulated ≥3 occurrences)
5. AGENTS.md 新增 §15 "Runtime Safety Hook Protocol" 段落

## 6. 实施顺序

1. Spec + Plan (本 Spec 即)
2. codegraph sync .
3. RED: 写 7 个测试 + 验证失败
4. GREEN: 实现最小 runtime_safety.py
5. 端到端: 先触发 reflexion 累计 ≥3 次 terminate 失败模式, 再用 runtime_safety 真阻断
6. REFACTOR + ruff + TE Monitor + Self-Reflection R1+R2

## 7. 风险

| 风险 | 缓解 |
|---|---|
| 误拦合法操作 | decision = WARN 时不强制 exit 1, 由 caller 决定 |
| 性能 overhead | pattern matching 是 O(N), N ≤ 50 typically, 可接受 |
| Agent 不调用 | AGENTS.md §15 强制, pre-commit hook 不易自动验证 (运行时) |

## 8. Out of scope

- 跨 runtime A/B 验证 (属 P3)
- 实时跨 session 同步 (属 P2 跨 Session 学习, 独立 spec)
- 自动 promote ALLOW→WARN→BLOCK 阈值 (P3 自校准)

## 9. Token budget

预估 ~250 行 production + ~200 行 test + 50 行 AGENTS.md 段 = ~500 行。
