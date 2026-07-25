# Cross-Session Memory (`.omc/conventions.json`) — 设计 (L4 #10)

- **日期**: 2026-07-25
- **状态**: 定稿 (待实施)
- **优先级**: P3.1 (跨 Session 学习)
- **关联**: `docs/agentic-maturity-model.md` §6.4 (最后 1 个 Gap)

## 1. 背景

每次 agent session 启动时,前面 session 学到的约定/偏好/事实都丢失。
`.omc/project-memory.json` 已存在 (842 行) 但是 auto-scanned tech-stack,
不是 agent-derived convention facts。

P3.1 新增 sidecar `.omc/conventions.json`:
- **写**: agent 在完成任务时 derive 候选 MemoryRecord,人工/auto 审核后写入
- **读**: 新 session 启动时 `load + format_for_prompt` 注入 system prompt
- **检索**: keyword-match query API

## 2. 目标

新增 `scripts/session_memory.py`:
1. **库函数** `load_memory(path)` / `save_memory(...)` — 持久化
2. **库函数** `query_memory(records, q, top_k)` — keyword match
3. **库函数** `derive_candidates(transcript)` — 从对话提取 (heuristics v0)
4. **库函数** `format_for_prompt(records, max_chars)` — 注入 system prompt
5. **CLI** `record` / `query` / `load` / `render`

## 3. 数据契约

```python
@dataclass
class MemoryRecord:
    id: str              # "mem-001"
    timestamp: str       # ISO 8601
    scope: str           # "user-pref" | "repo-fact" | "convention" | "tool-choice"
    summary: str         # ≤ 120 chars
    detail: str = ""     # optional long form
    confidence: float = 1.0
    source_session: str = ""
    tags: list[str] = []
```

Sidecar file `.omc/conventions.json`:
```json
{
  "version": "1.0.0",
  "updated_at": "2026-07-25T12:34:56Z",
  "records": [MemoryRecord, ...]
}
```

## 4. CLI 协议

```bash
# 1. Add manually (agent invokes after derive review)
python3 scripts/session_memory.py record \
  --scope user-pref \
  --summary "User prefers Chinese documentation" \
  --detail "README_cn.md is canonical for zh-CN users" \
  --source-session $SESSION_ID

# 2. Query (retrieve top 5 matching)
python3 scripts/session_memory.py query "aws region" --top 5

# 3. Render to prompt (max 2000 chars; for system-message injection)
python3 scripts/session_memory.py render --max-chars 2000

# 4. List all
python3 scripts/session_memory.py list
```

## 5. Heuristics for derive_candidates

Pattern-match user (and agent-summary) messages for declarative project facts:
- "约定 ..." / "convention:"
- "always ..." / "never ..."
- "我们用 ..." / "we use ..."
- "the rule is ..."
- "user prefers ..."

Each hit → MemoryRecord(scope="convention" | "user-pref", confidence=0.6).

Heuristics v0 is **advisory**, not authoritative — agent reviews before save.

## 6. 验收

1. `python3 -c "from session_memory import MemoryRecord"` 可导入
2. RED → GREEN: 6+ 测试 (load/save/query/derive/format/cli-record/cli-query)
3. ruff 0 issue
4. 真跑: CLI record + query + render 完整 round-trip
5. AGENTS.md §19 "Cross-Session Memory Protocol"
6. maturity-model §6.4 最后 Gap 关闭 → 90%

## 7. 风险

| 风险 | 缓解 |
|---|---|
| Memory 累积失控 | 提供 `prune --older-than-days` 子命令 |
| 误记录敏感信息 | scope 限定 + optional `tags: [secret]` |
| Heuristic 误判 | 默认 confidence=0.6 + 人工 review |
| 命名冲突 | id 用 counter, scope 前缀确保唯一 |

## 8. Token budget

预估 ~250 行 production + ~150 行 tests + ~80 行 AGENTS.md = **~480 行**.
