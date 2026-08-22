> 见 [AGENTS.md §16](../AGENTS.md) 索引

## 16. Eval-Driven Dev Protocol (L4 #7)

The compile-time gates (§11 / §12 / §14) enforce invariants; the runtime gate
(§15) catches dangerous executions. **Eval-Driven Dev** (L4 #7) catches
*silent capability regressions*: a SKILL.md change that breaks a happy-path
scenario without violating any compile-time rule.

> **Hard rule**: every L1/L2 skill must ship a `golden-scenarios.yaml`
> fixture with **≥5 scenarios**. Any PR that touches `aws-<svc>-ops/SKILL.md`
> or its `references/` MUST re-run `python3 scripts/golden_eval.py diff`
> and report `0 regressions` before merge.

### Scenario anatomy

```yaml
# aws-<svc>-ops/golden-scenarios.yaml
---
skill: aws-<svc>-ops
description: |
  Golden suite for aws-<svc>-ops v<version>. <N> scenarios.
scenarios:
  - id: <unique-scenario-id>
    description: <1-line human description>
    request: <user natural-language request>
    expected_status: PASS | SAFETY_FAIL | MAX_ITER
    user_region: <aws-region>       # optional, defaults to ""
    safety_confirm: <token>         # optional, defaults to ""
```

`expected_status` MUST be one of `PASS`, `SAFETY_FAIL`, `MAX_ITER` (the
three GCL termination outcomes from `gcl-spec.md` §5). Other strings
rejected at load time.

### Coverage minimums

Per skill, scenarios should cover the matrix:

| Bucket | Min count | Examples |
|---|---|---|
| Read-only happy path | ≥2 | `list X`, `describe Y` |
| Confirmed destructive | ≥2 | `terminate with --confirm=...` |
| Destructive without confirm | ≥1 | `terminate without --confirm` |
| Idempotency check | ≥1 | request followed by same request |

For a base skill that is small (e.g. `aws-ram-ops`), 5 scenarios is
acceptable. For composite skills (`aws-aiops-copilot` etc.), 10+.

### CLI reference

```bash
# 1. Run all scenarios, persist JSON results
python3 scripts/golden_eval.py run \
  --skill aws-ec2-ops \
  --scenarios aws-ec2-ops/golden-scenarios.yaml \
  --out audit-results/golden/aws-ec2-ops.json

# 2. Save the current run as the canonical baseline (one-time, in CI hook)
python3 scripts/golden_eval.py run ... --out /path/to/baseline.json
git add aws-ec2-ops/golden-scenarios.yaml audit-results/golden/aws-ec2-ops.json

# 3. Detect regressions on subsequent runs
python3 scripts/golden_eval.py diff \
  --current audit-results/golden/aws-ec2-ops.json \
  --baseline audit-results/golden/aws-ec2-ops-baseline.json
# exit 0 = no regression, 1 = regression detected
```

### Library API

```python
from golden_eval import (
    Scenario, ScenarioResult, BaselineReport,
    load_scenarios, run_scenario, run_scenarios,
    compare_to_baseline, save_results, load_results,
)

scenarios = load_scenarios(Path("aws-ec2-ops/golden-scenarios.yaml"))
results = run_scenarios(scenarios, skill="aws-ec2-ops")
baseline = load_results(Path("audit-results/golden/baseline.json"))
report = compare_to_baseline(results, baseline)
if report.has_regression:
    raise SystemExit(f"regressions: {report.regressions}")
```

### Decision table — when to add scenarios

| Trigger | Action |
|---|---|
| New skill published | bootstrap with 5 scenarios |
| New operation in `references/aws-cli-usage.md` | add ≥1 scenario |
| Operator reports a real-world failure | add scenario that **reproduces** the failure (`expected_status: SAFETY_FAIL`) |
| F-# (failure-pattern) added with count ≥ 5 | promote the failure to a golden scenario so the suite covers it |
| Quarterly review | scan last 30 days of `gcl-trace-*.json`, derive new scenarios from real user requests |

### Strict-mode gate (CI integration)

Add to `.github/workflows/golden.yml` (out of scope for this PR):

```yaml
- run: python3 scripts/golden_eval.py diff --current audit-results/golden/$SKILL.json --baseline audit-results/golden/$SKILL-baseline.json
  name: golden regression check
```

Spec: [`docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md`](docs/superpowers/specs/2026-07-25-eval-driven-dev-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-eval-driven-dev.md`](docs/superpowers/plans/2026-07-25-eval-driven-dev.md).

