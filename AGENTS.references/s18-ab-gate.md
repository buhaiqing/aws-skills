> 见 [AGENTS.md §18](../AGENTS.md) 索引

## 18. A/B Test Hard Gate Protocol (L4 #9)

P2.2 (`§16 Eval-Driven Dev`) ships the **what to test** (golden scenarios).
P2.3 (`§17 Telemetry Dashboard`) ships the **aggregate view**.
**§18 (A/B Hard Gate)** ships the **CI gate**: when you change a skill,
the build fails if any golden scenario regressed.

> **Hard rule**: every PR that touches `aws-<svc>-ops/SKILL.md`, its
> `references/`, or any L2 composite's `metadata.cross_skill_deps`
> MUST pass `python3 scripts/ab_gate.py gate --baseline <before.json>
> --candidate <after.json>` with exit 0. CI uses the `--json` form.

### Decision matrix

| Scenario state | baseline ↦ candidate | Action | exit_code |
|---|---|---|---|
| matched | True ↦ True | **unchanged** | 0 |
| matched | True ↦ False | **regression** | 1 |
| matched | False ↦ True | **fixed** | 0 |
| missing_in_baseline | new scenario | not a regression | 0 |
| missing_in_candidate | scenario disappeared | **regression** | 1 |
| file not found | n/a | error | **2** |
| invalid JSON | n/a | error | **2** |

Exit codes follow POSIX conventions: 0 = pass, 1 = regression, 2 = misuse.

### CLI reference

```bash
# 1. Standard CI gate
python3 scripts/ab_gate.py gate \
  --baseline audit-results/golden/aws-ec2-ops-baseline.json \
  --candidate audit-results/golden/aws-ec2-ops.json

# 2. JSON output (CI consumes directly)
python3 scripts/ab_gate.py gate \
  --baseline ... --candidate ... --json
# stdout: {"regressions":["..."],"fixed":["..."],"unchanged":["..."],"exit_code":1}

# 3. Cascade discovery (advisory, not part of gate decision)
python3 scripts/ab_gate.py cascade --skill aws-aiops-copilot
# stdout: cascaded skills for aws-aiops-copilot:
#         - aws-aiops-cruise
#         - aws-aiops-orchestrator
```

### CI workflow integration

```yaml
# .github/workflows/ab-gate.yml
- name: A/B gate
  run: |
    # baseline is the saved baseline.json from main branch
    git show origin/main:audit-results/golden/aws-ec2-ops-baseline.json \
      > /tmp/baseline.json || echo '{"results":[]}' > /tmp/baseline.json
    python3 scripts/golden_eval.py run \
      --skill aws-ec2-ops \
      --scenarios aws-ec2-ops/golden-scenarios.yaml \
      --out /tmp/candidate.json
    python3 scripts/ab_gate.py gate \
      --baseline /tmp/baseline.json \
      --candidate /tmp/candidate.json \
      --json
```

### Library API

```python
from ab_gate import ABReport, run_ab_gate, cascaded_skills

report = run_ab_gate(
    Path("audit-results/baseline.json"),
    Path("audit-results/candidate.json"),
)
if report.exit_code == 1:
    raise SystemExit(f"regressions: {report.regressions}")

cascaded = cascaded_skills("aws-aiops-copilot")
# Returns list[str] of cross_skill_deps dir names.
# Advisory; the gate does NOT recurse automatically.
```

### Why separate from §17 (Telemetry)?

| | §17 Telemetry | §18 A/B Gate |
|---|---|---|
| Input | All signals over 30 days | Two snapshots (T0, T1) |
| Granularity | Per-skill pass-rate delta | Per-scenario matched_status |
| Latency | Real-time after data accumulates | At PR time |
| Exit | 1 if any skill regressed | 1 if any scenario regressed |
| Use case | "is prod healthy?" | "is this PR safe to merge?" |

Both can run in the same CI: gate (fast, per-PR) → telemetry (slow, post-merge).
A regression caught by gate SHOULD also surface in telemetry within 1 day.

Spec: [`docs/superpowers/specs/2026-07-25-ab-gate-design.md`](docs/superpowers/specs/2026-07-25-ab-gate-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-ab-gate.md`](docs/superpowers/plans/2026-07-25-ab-gate.md).

