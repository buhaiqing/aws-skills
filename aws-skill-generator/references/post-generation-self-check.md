# Post-Generation Self-Check (生成后自检 — 宪章执行)

> **机制：生成完成后自动执行，不符合则循环修复直到通过。**
> **参考：** [`governance-review.md`](governance-review.md) §0 Charter

## Charter Compliance Checklist (强制执行)

| # | Check | Pass Criteria | Auto-Fix |
|---|-------|--------------|----------|
| C1 | Frontmatter | Starts with `---`, has `name`, `description`, `license`, `compatibility`, `metadata` | Add from aws-skill-template.md |
| C2 | SHOULD/SHOULD NOT | Both trigger sections present | Add Trigger & Scope section |
| C3 | Trigger & Scope | Complete with product keywords | Add from template |
| C4 | Variable Convention | `{{env.AWS_*}}`, `{{user.*}}`, `{{output.*}}` | Add placeholder table |
| C5 | Safety Gates | Destructive ops have confirmation | Add pre-flight safety gate |
| **C6** | **Token Efficiency** | Objective gates (all MUST pass): (1) `SKILL.md` ≤ 120 lines; (2) no hard-coded static tables >5 rows (TE-1); (3) JSON paths declared once at file top (TE-4); (4) no cross-file duplicated flow (TE-6); (5) boto3 has no docstrings (TE-2); (6) errors in compact table (TE-3) | HALT → report each violated gate → fix → re-check → LOOP |
| **C7** | **分层契约 (Layering Contract)** | If `metadata.type == composite` (or `orchestrator-meta`), must have `delegate` pointing to existing `aws-<svc>-ops` dirs; `base` skills may fill `provides` | composite missing delegate or dir not found → HALT |

> **自解流程**：C1-C7 失败 → HALT → REPORT → REMEDIATE → RE-CHECK → LOOP

Run machine checks:

```bash
python3 scripts/te_gate.py <your-skill> --strict
awk '/^---$/{c++; if(c==2){exit}} c==1' SKILL.md   # frontmatter integrity
```

Verify every `aws-<x>-ops` in SHOULD NOT / recovery / GCL rubric Safety cases exists in this repo.
