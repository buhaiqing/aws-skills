# Telemetry Dashboard

Generated: 2026-07-25 15:34:20 UTC  
Window: 30 days (signals: 30 of 30)

## Overview

- Skills covered: **4**
- Regressions flagged: 0

## Per-skill pass-rate (last 30 days vs prior 30 days)

| Skill | Pass | Fail | Total | Pass-rate | Prior | Δ | Regression |
|-------|------|------|-------|-----------|-------|---|------------|
| aws-ec2-ops | 13 | 0 | 13 | 1.00 | 1.00 | +0.00 |  |
| aws-s3-ops | 0 | 14 | 14 | 0.00 | 0.00 | +0.00 |  |
| ec2-ops | 0 | 2 | 2 | 0.00 | 0.00 | +0.00 |  |
| rds-ops | 0 | 1 | 1 | 0.00 | 0.00 | +0.00 |  |

## Fail-mode distribution

| Dimension | Count |
|-----------|-------|
| safety | 13 |
| idempotency | 1 |

## Sources

- gcl-trace: per-run GCL final status (real production traces)
- golden: per-scenario eval results
- reflexion: failure patterns with count >= 3
