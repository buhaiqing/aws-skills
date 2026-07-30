# Plan: aws-ec2-ops CLI fidelity + TE cleanup

Spec: `docs/superpowers/specs/2026-07-30-aws-ec2-ops-cli-fidelity-design.md`

- [x] T1 troubleshooting.md — metric CLI, AMI AL2023+sort, SSM JSON, InstanceLimitExceeded → HALT note
- [x] T2 cost-tracking.md — utilization API, Coverage path, replace InstanceCount with describe-instances/CE
- [x] T3 boto3-sdk-usage.md — close fence, drop AIOps Python (link troubleshooting), no docstrings, thin error table → link
- [x] T4 aws-cli-usage.md + core-concepts.md — AL2023 AMI, client-token, TE-1, JSON path note
- [x] T5 confirm tokens — SKILL, rubric, prompt-templates Confirmation Strings, golden
- [x] T6 prompt-examples.md compress + SKILL refs + golden idempotency + self-review
- [x] T7 reverse-verify + golden_eval + TE monitor
