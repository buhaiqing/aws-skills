> 见 [AGENTS.md §17](../AGENTS.md) 索引

## 17. Telemetry Dashboard Protocol (L4 #8)

§11 (GCL) writes traces; §13 (CADL) writes reflection; §15 (Runtime Safety)
writes blocks; §16 (Golden Eval) writes baselines. **§17 (Telemetry Dashboard)**
unifies all of them into a single 30-day rolling view that human reviewers
and CI bots can both read.

> **Hard rule**: every CI pipeline that runs GCL/Golden must also
> run `python3 scripts/telemetry_dashboard.py alert` and respect exit
> code 1 as a blocking alert.

### Sources (3 readers, 1 schema)

| Source | Path | Schema |
|---|---|---|
| GCL trace | `audit-results/gcl-trace-*.json` | `{skill, final.status, iterations[].critic.scores}` |
| Golden run | `audit-results/golden/*.json` | `{skill, results:[{matched_status, ...}]}` |
| Reflexion | `docs/failure-patterns.md` (count >= 3 rows) | `{skill, command, count}` |

All three sources normalize into `SignalSlice { skill, status, timestamp, source }`,
then aggregate into `Dashboard { by_skill: [SkillMetric], by_fail_mode, ... }`.

### CLI reference

```bash
# Render dashboard
python3 scripts/telemetry_dashboard.py dashboard \
  --audit-dir audit-results/ \
  --window-days 30 \
  --out docs/telemetry/dashboard.md

# CI alert: exit 1 if any skill's pass_rate drops ≥ threshold vs prior 30 days
python3 scripts/telemetry_dashboard.py alert \
  --audit-dir audit-results/ \
  --window-days 30 \
  --drop-threshold 0.05
# stdout: ## Alerts
#         - aws-ec2-ops: pass_rate 1.00 -> 0.77 (Δ-0.23)
# exit 0 = no regression, 1 = regression detected
```

### Library API

```python
from telemetry_dashboard import (
    SignalSlice, SkillMetric, Dashboard,
    load_signals, compute_dashboard,
    detect_regressions, render_markdown,
)

signals = load_signals(Path("audit-results/"))
dash = compute_dashboard(signals, window_days=30, prior_window_days=30)
flagged = detect_regressions(dash, drop_threshold=0.05)
md = render_markdown(dash)
```

### Alert decision table

| Current window | Prior window | Delta | Threshold=0.05 | Action |
|---|---|---|---|---|
| ≥1 signal | ≥1 signal | >= -0.05 | safe | **exit 0** |
| ≥1 signal | ≥1 signal | < -0.05 (e.g. -0.10) | regressed | **exit 1** alert |
| ≥1 signal | 0 signals | n/a | insufficient history | **exit 0** (do not alert on first 30 days) |
| 0 signals | any | n/a | no recent activity | **exit 0** |

The "first 30 days" exclusion prevents false alarms when telemetry is
first wired up — it's a generous warm-up window.

### CI integration

```yaml
# .github/workflows/telemetry-alert.yml
- name: Telemetry regression check
  run: |
    python3 scripts/telemetry_dashboard.py alert \
      --audit-dir audit-results/ \
      --drop-threshold 0.05
- name: Generate dashboard artifact
  if: always()
  run: |
    python3 scripts/telemetry_dashboard.py dashboard \
      --audit-dir audit-results/ \
      --out docs/telemetry/dashboard.md
- uses: actions/upload-artifact@v4
  with:
    name: telemetry-dashboard
    path: docs/telemetry/dashboard.md
```

Spec: [`docs/superpowers/specs/2026-07-25-telemetry-dashboard-design.md`](docs/superpowers/specs/2026-07-25-telemetry-dashboard-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-telemetry-dashboard.md`](docs/superpowers/plans/2026-07-25-telemetry-dashboard.md).

