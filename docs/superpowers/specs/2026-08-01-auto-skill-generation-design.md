# Auto Skill Generation — Design (O10 / P3.3 MVP)

- **Date**: 2026-08-01
- **Status**: **工程 DONE**（D1–D3 MVP 2026-08-01）；D1 scaffold + D2 gate 已交付；**LLM 填充仍为人工/agent 步骤**；auto merge rate = 0%
- **Backlog**: post-m2 `O10` / Wave **D3**
- **Plan**: [`../plans/2026-08-01-auto-skill-generation.md`](../plans/2026-08-01-auto-skill-generation.md)
- **Depends on**: `aws-skill-generator` meta-skill；现有 `te_gate` / Charter / golden / GCL helpers
- **Positioning**: L4 **研究性 MVP**（`l4-final.md` P3.3）— 非 ADR-0001 证据主线；**不扩大 AUTO_HEAL**

## 1. Goal

给定**结构化 P0 输入** → 机械 scaffold + LLM 填充 → **机器门禁** → **人工批准 PR** 才合入。  
**自动合入率 = 0%**（对齐 M4：长期资产 / 新 skill 均需人批）。

```text
ServiceSpec (P0 form)
  → scaffold layout from aws-skill-template + new-skill-template
  → fill SKILL.md + references (docs URL + `aws <svc> help` evidence only)
  → seed golden-scenarios.yaml (≥5)
  → if destructive: _gen_rubric + thin prompt-templates + optional _add_gcl
  → gate: te_gate --strict + links_lint + frontmatter deps + golden load
  → open PR / queue for human approve
  → merge only after human sign-off
```

## 2. Non-goals

- 扩大 `AUTO_HEAL` / 自动接线 orchestrator runbook
- 无 docs URL / CLI help 证据时臆造 API（Scenario E → HALT）
- Auto-merge `main`；无限 auto-fix 直到绿（门禁失败 → HALT 交人）
- 替换 `aws-skill-generator` meta-skill 为另一套框架
- L5 自演化 / 自主发现新服务
- 全仓非五高风险 shadow / composite AIOps 自动生成

## 3. ServiceSpec (P0 form — machine + human)

| Field | Required | Notes |
|---|---|---|
| `service_id` | yes | e.g. `glue` → dir `aws-glue-ops` |
| `product_name` | yes | display name |
| `primary_resource` | yes | e.g. `Job` |
| `docs_url` | yes | official AWS docs |
| `cli_namespace` | yes | `aws <ns> help` must succeed in preflight |
| `boto3_module` | yes | e.g. `glue` |
| `destructive_ops` | yes | list; may be empty |
| `cross_skill_deps` | no | existing dirs only |
| `gcl_tier` | no | default from docs/gcl-per-skill-defaults heuristics |

Reject generation if any required field missing or `docs_url` host not `docs.aws.amazon.com` / `aws.amazon.com`.

## 4. Architecture (MVP)

| Piece | Role |
|---|---|
| `scripts/skill_scaffold.py` | **机械**：mkdir、复制模板占位、写 `ServiceSpec` sidecar、调用现有 `_gen_rubric` / skeleton copy |
| Agent / LLM step | **填充**：按 meta-skill checklist 写内容（仍可读 `aws-skill-generator/SKILL.md`） |
| `scripts/skill_gen_gate.py` | **门禁**：te_gate / links_lint / golden load / no-host-path；失败非零退出 |
| Approval | **人**：PR review；可选 `audit-results/skill-gen/approvals.jsonl` 记录 approver（镜像 M4） |

No public API merges or writes README without `--approver` / PR merge by human.

## 5. Exit criteria (MVP)

| Criterion | Measure |
|---|---|
| Scaffold 可重复 | 同一 ServiceSpec fixture → 稳定目录树 |
| Gate 红/绿明确 | 故意缺 C2 子标题 / 超长 SKILL → gate fail |
| 自动合入率 | **0%**（测试断言无 merge helper） |
| 证据约束 | 无 `docs_url` → refuse；fixture 文档注明 CLI help stub |
| 不碰 AUTO_HEAL | grep 生成物无 `AUTO_HEAL` 扩权 |

## 6. Phases

| Phase | Scope | Needs approval? |
|---|---|---|
| **D0** | 本 spec + plan | —（DONE） |
| **D1** | `skill_scaffold.py` + fixture ServiceSpec + tests | DONE |
| **D2** | `skill_gen_gate.py` + CI optional job | DONE |
| **D3** | 一次真实 dry-run skill（prefer obscure / `--dry-run` 不落仓）+ 文档 | DONE |

## 7. Acceptance (post-approval)

```bash
pytest -p no:rerunfailures scripts/tests/test_skill_scaffold.py scripts/tests/test_skill_gen_gate.py -q
python3 scripts/skill_gen_gate.py --skill <tmp-dir> --strict
```

## 8. Risks

| Risk | Mitigation |
|---|---|
| LLM 臆造 API | gate + 人工抽查 CLI JSON paths；无 live AWS 不强制 |
| Over-scaffold | 只复用现有 helper；禁止新编排 runtime |
| 与证据主线抢带宽 | D1+ 排在 M1 满窗 hygiene 之后或并行低优 |
