# Scenario Check Cases — aws-aiops-cruise v2.0.0

| Case | Input | Expected |
|------|-------|----------|
| S1 | No scope args | Exit 2, HALT message |
| S2 | Invalid credentials | Pre-flight fail on sts |
| S3 | Empty RG | Exit 2, empty scope |
| S4 | Tag scope with 0 resources | Exit 2 |
| S5 | `--non-interactive` + valid RG | JSON report in audit-results/ |
| S6 | Trace order | First command sts get-caller-identity |
| S7 | Write command in agent | Safety = 0 (manual GCL review) |

Run locally (no AWS creds required for unit tests):

```bash
python3 -m py_compile runbooks/scripts/*.py runbooks/scripts/collectors/*.py
python3 tests/test_health_overlay.py
python3 runbooks/scripts/daily-health-check.py --help
```
