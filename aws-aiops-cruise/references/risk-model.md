# Risk Model — aws-aiops-cruise

> Unified risk evidence chain. Rule engine primary; ML optional via env (default off).

## Risk synthesis

```text
risk_score = max(static_threshold_score, wow_score, trend_score)
```

| risk_score | risk_level |
|------------|------------|
| ≥ 0.75 | CRITICAL |
| ≥ 0.50 | WARNING |
| ≥ 0.25 | INFO |
| < 0.25 | NORMAL |

## `risk_evidence[]` fields

See `runbooks/scripts/_inference.py` → `build_risk_evidence()`.

| Field | Description |
|-------|-------------|
| `resource_type` / `resource_id` / `metric` | Target |
| `current_value` | Latest CloudWatch aggregate |
| `risk_level` / `risk_score` / `confidence` | Composite |
| `static_level` | Fixed threshold only |
| `trend.wow_percent` | Week-over-week % change (same 6h window) |
| `duration.consecutive_points` | Reserved for 5min series (future) |
| `ml_shadow_result` | Populated when `AIOPS_ML_MODE != off` |

## ML gray release (optional)

```bash
export AIOPS_ML_MODE=off    # default
export AIOPS_ML_MODE=shadow # run ML, do not change grade
```

Implementation: stub in v1.1 — wire to CloudWatch anomaly detectors or external model in v1.2.

## Output location

`daily-health-check.py` embeds `risk_evidence[]` in cruise JSON (cap 200 rows).
