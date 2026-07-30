# Plan: Batch cw / ddb / elb fidelity

Spec: `docs/superpowers/specs/2026-07-30-batch-cw-ddb-elb-fidelity-design.md`

- [x] T1 aws-cloudwatch-ops: golden + confirm= + Confirmation Strings + MemoryUtilization + boto3 fence/json import + trim prompt-examples
- [x] T2 aws-dynamodb-ops: golden + SKILL confirm= + Confirmation Strings + Lambda EventSourceArn + {{user.region}} + link prompt-examples
- [x] T3 aws-elb-ops: golden + SKILL confirm= align rubric + Confirmation Strings + ALB active + CW dimension note + trim prompt-examples
- [x] T4 te_gate ×3 + golden_eval ×3 + TE monitor
