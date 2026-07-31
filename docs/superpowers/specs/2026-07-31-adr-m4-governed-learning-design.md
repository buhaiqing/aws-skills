# ADR-0001 M4 — Governed Learning Design

- **Date**: 2026-07-31
- **Status**: 定稿（工程 DONE 2026-07-31）
- **ADR**: [`docs/adr/0001-l4-production-evidence-loop.md`](../../adr/0001-l4-production-evidence-loop.md) §Milestone 4
- **Depends on**: M1–M3（eval / shadow / compensation outcomes）
- **Plan**: [`../plans/2026-07-31-adr-m4-governed-learning.md`](../plans/2026-07-31-adr-m4-governed-learning.md)

## 1. Goal

失败经验 **自动产生候选** → **离线验证** → **人工批准后** 才写入长期资产（`docs/failure-patterns.md`）。  
**自动晋升率恒为 0%。**

```text
GCL/proxy/compensation outcomes
  → harvest candidates (SAFETY_FAIL|MAX_ITER|BLOCKED|COMPENSATION_FAIL)
  → dedupe / minimize (signature)
  → offline replay + before/after eval evidence
  → approval queue (human only)
  → approve → append_or_increment(failure-patterns.md) + approval audit record
```

## 2. Non-goals

- 自动写入 `AGENTS.md` / Charter / runtime thresholds
- 扩大 `AUTO_HEAL`
- Critic/Telemetry 直接 mutate AWS
- 替换现有 `_reflexion.append_or_increment` 热路径（M4 **编排**批准；热路径仍可记 raw）

## 3. Data model

### CandidateRule

| Field | Notes |
|---|---|
| `id` | `cand-<hash12>` |
| `signature` | `skill\|command\|error[:50]`（同 `_reflexion`） |
| `skill` / `command` / `error` / `root_cause` / `fix` | pattern body |
| `source_status` | SAFETY_FAIL \| MAX_ITER \| BLOCKED \| COMPENSATION_FAIL |
| `sources` | trace paths / fixture ids |
| `status` | `pending` \| `approved` \| `rejected` |
| `before_eval` / `after_eval` | dict evidence |
| `approval` | `{approver, at, record_id}` \| null |

### ApprovalRecord

Append-only JSONL under `audit-results/governed-learning/approvals.jsonl`.

## 4. Exit criteria (ADR)

| Criterion | Measure |
|---|---|
| 候选重复率 &lt;10% | `1 - unique_signatures/raw_count` |
| 提升有 before/after eval | approve 拒绝无 evidence 的候选 |
| 自动晋升率 = 0% | 无代码路径可跳过 `approve`；CI 断言 |

## 5. Phases

| Phase | Scope |
|---|---|
| **A** | `governed_learning.py` harvest/dedupe/replay/queue + tests |
| **B** | CLI `harvest` / `evaluate` / `queue` / `approve` / `reject` |
| **C** | CI smoke + ADR/maturity Progress |

## 6. Acceptance

```bash
pytest -p no:rerunfailures scripts/tests/test_governed_learning.py -q
python3 scripts/governed_learning.py harvest --fixtures --out /tmp/gl-queue.json
python3 scripts/te_gate.py --all --strict
```
