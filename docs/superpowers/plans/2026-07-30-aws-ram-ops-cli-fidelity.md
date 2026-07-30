# Plan: aws-ram-ops CLI fidelity + TE cleanup

Spec: `docs/superpowers/specs/2026-07-30-aws-ram-ops-cli-fidelity-design.md`

## Tasks

- [x] **T1** Fix `references/aws-cli-usage.md`: resource-owner on all list-resources; fix association-type; replace-permission (account-wide, no share ARN) + per-share `--replace` pattern; AWSRAMDefaultPermissionSubnet; list-permissions note for RO/RDS.
- [x] **T2** Fix `references/boto3-sdk-usage.md`: `resourceOwner='SELF'|'OTHER-ACCOUNTS'` on list_resources.
- [x] **T3** Fix `references/integration.md`: consumer verify → `OTHER-ACCOUNTS`.
- [x] **T4** Fix `assets/example-config.yaml`: permission → AWSRAMDefaultPermissionSubnet (or document list-permissions).
- [x] **T5** Rewrite `references/prompt-examples.md`: all P0/P1 fixes; dedupe bash → links; uniform 流程; target ≤200 lines.
- [x] **T6** Add `aws-ram-ops/golden-scenarios.yaml` (≥5).
- [x] **T7** Grep reverse-verify + TE monitor + lesson in post-update-self-review.

## Parallelism

T1–T4 + T6 can run in parallel; T5 depends on T1 patterns being known (can run parallel with same acceptance text); T7 after all.
