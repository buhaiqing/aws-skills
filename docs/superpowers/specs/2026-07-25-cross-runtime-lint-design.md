# Cross-Runtime Portability Lint — 设计 (L4 #11)

- **日期**: 2026-07-25
- **状态**: 定稿 (待实施)
- **优先级**: P3.2 (跨 Runtime 一致性)
- **关联**: `docs/agentic-maturity-model.md` §6.3 (Planned)

## 1. 背景

P3.1 之前,仓库已经在 §15 列了 runtime integration table:
```
| OpenCode / Codex CLI | `pre_tool_use` hook in `~/.codex/config.toml` |
| Claude Code | `PreToolUse` matcher in `settings.json` → call `runtime_safety.py` |
```

但**没有自动检测** — 当 SKILL.md 写时漏掉了其他 runtime 的 hook 路径,该谁发现?

P3.2 新增 `scripts/cross_runtime_lint.py`:
- 静态扫 SKILL.md 找 runtime-specific hardcodes
- 给每个 skill 输出 portability score (0..1)
- 自动生成 cross-runtime coverage matrix

注意: 真跨 runtime 跑(同一 prompt 在 OpenCode / Claude Code / Cursor 都跑)
需要外部 runtime — 这超出 sandbox。我们做**前置静态分析**。

## 2. 目标

`scripts/cross_runtime_lint.py`:
1. **库** `detect_runtime_coupling(skill_md)` → list[(runtime, pattern, line)]
2. **库** `score_portability(skill_md)` → float (1.0 = portable)
3. **库** `lint_repo(repo)` → dict[skill_name, SkillLintReport]
4. **CLI** `lint --skill X` 或 `--all` 输出 Markdown 报告

## 3. 契约

```python
@dataclass
class CouplingHit:
    runtime: str        # "codex" | "claude" | "cursor" | "home-path" | "binary-path"
    pattern: str        # the matched string
    line_number: int
    line_content: str   # for context

@dataclass
class SkillLintReport:
    skill: str
    score: float
    hits: list[CouplingHit]
    portable_hints: list[str]

def detect_runtime_coupling(skill_md: Path) -> list[CouplingHit]: ...
def score_portability(skill_md: Path) -> float: ...
def lint_repo(repo: Path = REPO) -> dict[str, SkillLintReport]: ...

KNOBS = {"high_score_threshold": 0.85, "medium_score_threshold": 0.6}
```

## 4. 已知 runtime-specific patterns

| Pattern | Runtime |
|---|---|
| `~/.codex/` | Codex CLI / OpenCode |
| `~/.claude/` | Claude Code |
| `~/.cursor/` | Cursor |
| `/Users/`, `/home/` (in skill content) | host path (portability issue) |
| `python3.12` (hard version) | env constraint |
| `pip install awscli` | dev setup |

## 5. CLI

```bash
# lint single skill
python3 scripts/cross_runtime_lint.py lint --skill aws-ec2-ops

# lint all
python3 scripts/cross_runtime_lint.py lint --all --out docs/runtime/cross-runtime-2026-07-25.md

# JSON output
python3 scripts/cross_runtime_lint.py lint --skill X --json
```

## 6. 验收

1. `from cross_runtime_lint import detect_runtime_coupling` 可导入
2. RED → GREEN: 6 测试 (detect × 2 + score × 2 + lint × 2)
3. ruff 0 issue
4. 真跑: lint all skills → Markdown report; at least 1 finding per skill
5. AGENTS.md §20 "Cross-Runtime Portability Protocol"

## 7. Token budget

预估 ~250 行 production + ~150 行 tests + ~80 行 AGENTS.md = **~480 行**.
