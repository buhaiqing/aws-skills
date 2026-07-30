# Design: aws-ec2-ops CLI fidelity + TE cleanup

**Date:** 2026-07-30  
**Scope:** Fix CLI/API factual errors, TE violations, confirm-token drift, AIOps duplication in `aws-ec2-ops`.

## Canonical decisions

1. **GCL confirm tokens:** `confirm=<OP> <id>` (template / rubric). Examples: `confirm=TERMINATE i-xxx`, `confirm=STOP i-xxx`, `confirm=DELETE_KEY_PAIR name`, `confirm=DETACH vol-xxx`, `confirm=DEREGISTER_IMAGE ami-xxx`.
2. **Runtime hook** (`build_confirmation_token` → `CONFIRM {op} {hash}`) remains a separate L4 layer; skill docs document GCL format; do not invent hash tokens in golden YAML.
3. **AIOps single source:** keep detailed flows in `troubleshooting.md`; `prompt-examples.md` and `boto3-sdk-usage.md` link only.
4. **AMI default:** Amazon Linux 2023 + `sort_by(Images,&CreationDate)[-1].ImageId`.

## Acceptance

- [ ] No broken `get-metric-data` flag misuse; no fictional `InstanceCount`.
- [ ] boto3 fence closed; AIOps Python removed or comment-only; no `"""` docstrings.
- [ ] core-concepts: no hardcoded instance-type size table (TE-1).
- [ ] Confirm tokens aligned across SKILL / rubric / prompt-templates / golden.
- [ ] prompt-templates has Confirmation Strings table.
- [ ] golden ≥7 scenarios including idempotency; golden_eval 0 regressions vs expected.
- [ ] SKILL.md still ≤120 lines; links cost-tracking + prompt-examples.
