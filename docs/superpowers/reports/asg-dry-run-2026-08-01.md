# ASG dry-run evidence (O10 D3) — 2026-08-01

Not committed into `aws-*-ops/` (throwaway under `/tmp`).

```bash
python3 scripts/skill_scaffold.py init \
  --spec /tmp/asg-fixture-spec.json \
  --out /tmp/asg-dry-run2
python3 scripts/skill_gen_gate.py --skill /tmp/asg-dry-run2/aws-examplebatch-ops --strict --json
# → ok: true, auto_merge_rate: 0.0
```

Fixture used fictional `examplebatch` + real `docs.aws.amazon.com/batch/` host for URL policy only — content still scaffold stubs; LLM fill not claimed done.

pytest: `test_skill_scaffold` + `test_skill_gen_gate` = **23 passed**.
