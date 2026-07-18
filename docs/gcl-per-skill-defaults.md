# GCL Per-Skill Defaults

> 权威表见根 `AGENTS.md` §11.5（摘要）。本文件承载完整 Per-Skill Defaults 表，供 GCL rollout 与 generator 自检引用。

| Skill | GCL | Default `max_iter` | Notes |
|---|---|---|---|
| `aws-ec2-ops` | **required (pilot)** | 2 | `terminate-instances`, `delete-key-pair`, `deregister-image`, `detach-volume` |
| `aws-autoscaling-ops` | **required** | 2 | `delete-auto-scaling-group` (`--force-delete` guard + rule A16), `delete-launch-configuration`, `detach-instances` (decrement guard), `set-desired-capacity` → 0 — shipped v1.0.0 |
| `aws-config-ops` | **recommended** | 3 | `delete-config-rule`, `delete-configuration-recorder`, `stop-configuration-recorder` — shipped v1.0.0 |
| `aws-eventbridge-ops` | **recommended** | 3 | `delete-rule` (target cleanup guard), `delete-event-bus`, `delete-schedule`, `delete-pipe` — shipped v1.0.0 |
| `aws-iam-ops` | **required (pilot)** | 2 | `delete-user`, `detach-user-policy`, `delete-access-key`; `*:*` policy guard |
| `aws-kms-ops` | **required (pilot)** | 2 | `schedule-key-deletion` is irreversible; `--pending-window-in-days ≥ 7` |
| `aws-s3-ops` | **required (pilot)** | 2 | `delete-bucket` (Versioned guard), `delete-objects` (empty array refusal), `put-bucket-policy` widening (rule A15) |
| `aws-rds-ops` | **required** | 2 | `delete-db-instance` (`--skip-final-snapshot` → rule A14); `delete-db-cluster` in `aws-aurora-ops` |
| `aws-aurora-ops` | **required** | 2 | `delete-db-cluster` (rule A14), `delete-db-cluster-snapshot`, `failover-db-cluster`, `backtrack-db-cluster`, Global Database detach — shipped v1.1.0 |
| `aws-lambda-ops` | **required** | 2 | `delete-function` (irreversible), `delete-function-concurrency` — shipped v1.1.0 |
| `aws-dynamodb-ops` | **required** | 2 | `delete-table` (data loss), `update-table` (throughput) — shipped v1.1.0 |
| `aws-elasticache-ops` | **required** | 2 | `delete-replication-group`, `delete-cache-cluster` |
| `aws-route53-ops` | **required** | 2 | `delete-hosted-zone` (DNS cut) — shipped v1.2.0 |
| `aws-sqs-ops` | **required** | 2 | `delete-queue` (in-flight message loss) |
| `aws-sns-ops` | **required** | 2 | `delete-topic`, `unsubscribe` |
| `aws-cloudfront-ops` | **required** | 2 | `delete-distribution` (must disable→poll Deployed; rule A11) — shipped v1.1.0 |
| `aws-waf-ops` | **required** | 2 | `delete-rule-group`, `delete-web-acl` |
| `aws-secretsmanager-ops` | **required** | 2 | `delete-secret` (irrecoverable), `put-secret-value` |
| `aws-ssm-ops` | **required** | 2 | `send-command` (remote exec), `delete-parameter` |
| `aws-stepfunctions-ops` | **required** | 2 | `delete-state-machine`, `stop-execution` |
| `aws-vpc-ops` | **required** | 2 | `delete-vpc` 8-describe pre-flight (rule A13), `delete-security-group` (cross-ref) — shipped v1.3.0 |
| `aws-acm-ops` | required | 2 | `delete-certificate` (in-use guard) |
| `aws-eks-ops` | required | 2 | `delete-cluster` (irreversible) |
| `aws-elb-ops` | recommended | 3 | `delete-load-balancer`, `deregister-targets` ≥50% drain confirmation (rule A12) — shipped v2.2.0 |
| `aws-ecs-ops` | **required** | 2 | `delete-service` (scale-to-0, rule A16), `delete-cluster`, `deregister-task-definition` |
| `aws-ecr-ops` | **required** | 2 | `delete-repository` (`--force` guard), `batch-delete-image` — shipped v1.0.0 |
| `aws-efs-ops` | **required** | 2 | `delete-file-system` (dependency pre-flight: mount targets + access points), `delete-mount-target`, `delete-access-point` — shipped v1.0.0 |
| `aws-ebs-ops` | **required** | 2 | `delete-volume` (data loss), `detach-volume`, `delete-snapshot` |
| `aws-apigateway-ops` | **required** | 2 | `delete-rest-api` (irreversible), `delete-stage`, `delete-api-key` |
| `aws-cloudwatch-ops` | recommended | 3 | `delete-alarms` (silent-failure guard) |
| `aws-athena-ops` | **required** | 2 | `delete-work-group`, `delete-named-query`, `delete-data-catalog`, `delete-prepared-statement` — shipped v1.0.0 |
| `aws-guardduty-ops` | **required** | 2 | `delete-detector`, `delete-filter`, `delete-ip-set`, `delete-threat-intel-set`, `delete-publishing-destination` — shipped v1.0.0 |
| `aws-opensearch-ops` | **required** | 2 | `delete-domain` (data loss), `delete-snapshot`, `delete-vpc-endpoint`, `delete-ingestion` — shipped v1.0.0 |
| `aws-ram-ops` | **required** | 2 | `delete-resource-share` (breaks dependent accounts), `delete-permission`, `delete-permission-version` — shipped v1.0.0 |
| `aws-securityhub-ops` | **required** | 2 | `delete-insight`, `delete-action-target`, `delete-automation-rule`, `delete-configuration-policy`, `disable-securityhub` — shipped v1.0.0 |
| `aws-cloudtrail-ops` | optional | 3 | read-mostly; `delete-trail` = severe |
| `aws-skill-generator` | optional | 3 | meta operation; secret-leak guard |
| `aws-topo-discovery` | optional | 3 | read-only discovery; no destructive operations |
| `aws-aiops-cruise` | recommended | 3 | read-only full-chain patrol; 7 Perceive Agents; no destructive operations |

Each skill may override its own `max_iter` in its `SKILL.md` under
`## Quality Gate (GCL)`. A skill not yet listed has GCL **disabled** by
default — pilots are rolled out one at a time per the spec §10 roadmap.
