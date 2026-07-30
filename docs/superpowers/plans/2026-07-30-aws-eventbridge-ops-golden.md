# Plan: aws-eventbridge-ops golden scenarios

**Spec:** `docs/superpowers/specs/2026-07-30-aws-eventbridge-ops-golden-design.md`

## Tasks

- [x] Add `aws-eventbridge-ops/golden-scenarios.yaml` (6 scenarios, ram-shaped)
- [x] Validate load + run: `golden_eval.py run` → all matched (6/6)
- [x] TE Monitor disposition on the new fixture

## Acceptance

```bash
python3 -c "from pathlib import Path; import sys; sys.path.insert(0,'scripts'); from golden_eval import load_scenarios; assert len(load_scenarios(Path('aws-eventbridge-ops/golden-scenarios.yaml'))) >= 5"
python3 scripts/golden_eval.py run --skill aws-eventbridge-ops \
  --scenarios aws-eventbridge-ops/golden-scenarios.yaml \
  --out audit-results/golden/aws-eventbridge-ops.json
# expect: scenarios: 6/6 matched expected_status
```
