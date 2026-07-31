# SKILL.md Body Extras — aws-aiops-cruise

> Bulky tables and sections moved from `SKILL.md` for TE G1 compliance. Primary entry remains `SKILL.md`; this file is the expanded reference.

## AWS AIOps Stack (not Aliyun port)

Patrol follows the **AWS reference stack** in [`aws-aiops-stack.md`](aws-aiops-stack.md):

| Layer | AWS services | Native AIOps signal |
|-------|--------------|---------------------|
| Edge | Route53 HC, CloudFront (+ S3 static origin OAC), WAFv2, API Gateway REST/HTTP | HC failure, OriginLatency/5xxErrorRate, S3 OAC/PAB, BlockedRequests, API GW 5xx/throttle |
| Entry | ALB/NLB, ACM | Target health, 5xx, cert expiry |
| Compute | EC2, ECS (Fargate/EC2), EKS, Lambda, API Gateway (REST/HTTP) | ASG cap, task drift, throttles, ECS task deficit, API GW latency/errors |
| Data | RDS+Aurora (PI), RDS Proxy→Aurora targets, ElastiCache, DynamoDB, EBS volumes (AttachState, VolumeQueueLength) | db.load, connections, proxy target health, cluster status, volume performance |
| Egress | NAT Gateway | Port allocation errors |
| Governance | Config, Security Hub, GuardDuty | Compliance + threats |
| Insight | CloudWatch Alarms, DevOps Guru, Compute Optimizer, X-Ray | Customer + ML + trace graph (`--enable-xray`) |

## Cross-Skill References

| Need | Delegate To | Notes |
|------|-------------|-------|
| Metrics / anomaly / forecast | `aws-cloudwatch-ops` | Namespace/MetricName conventions |
| DB deep diagnosis (RDS instance) | `aws-rds-ops` | Performance Insights, slow query |
| Aurora cluster diagnosis | `aws-aurora-ops` | Replica lag, failover, Serverless v2, Global DB, Proxy path |
| In-instance checks | `aws-ssm-ops` | Run Command (optional deep mode) |
| Topology manifest + health overlay | `aws-topo-discovery` | `topo-scan.sh`, `--render-topology`, `cruise-topo-render.py` |
| ELB deep diagnosis | `aws-elb-ops` | Target health, 5xx RCA patterns |
| Threat findings | `aws-guardduty-ops` | HIGH/CRITICAL count |
| Change audit | `aws-cloudtrail-ops` | API event correlation |
| DynamoDB diagnosis | `aws-dynamodb-ops` | Throttling, GSI hot shard, TTL |
| ElastiCache diagnosis | `aws-elasticache-ops` | Memory pressure, failover, evictions |
| OpenSearch diagnosis | `aws-opensearch-ops` | Heap pressure, shard imbalance, 5xx |
| EKS diagnosis | `aws-eks-ops` | Node NotReady, OOM, pod eviction |
| CloudFront diagnosis | `aws-cloudfront-ops` | Origin latency, cache hit rate, 5xx |
| Athena diagnosis | `aws-athena-ops` | Query cost, scan volume, timeouts |
| RAM diagnosis | `aws-ram-ops` | Resource share status, principal association |
| Secrets Manager diagnosis | `aws-secretsmanager-ops` | Rotation age, secret access |
| Capacity forecast | `aws-cloudwatch-ops` | 14-day trend prediction, proactive resize recommendations |

## EKS Node & Pod Detection

Phase-3 inference adds two EKS signal rules (details in [`inference-rules-addendum.md`](inference-rules-addendum.md)):

| Rule | Severity | Trigger | Source |
|------|----------|---------|--------|
| EKS-NODE-01 | WARNING | `node_status_condition_ready` Minimum < 1.0 over window → a node is NotReady | CloudWatch Container Insights (`EKS/ContainerInsights`) |
| EKS-OOM-01 | CRITICAL | `pod_container_status_terminated_reason_oom_killed` Sum > 0 → a pod was OOM-killed | CloudWatch Container Insights (`EKS/ContainerInsights`) |

**Production prerequisite**: both rules read kube-state-metrics published by the CloudWatch agent. EKS-OOM-01 only fires if the agent DaemonSet runs with `securityContext.privileged: true` (required to capture OOM events); otherwise the OOM metric is not emitted. Node-ready detection has no such constraint.

## Perceive Layer — 7 Agents

Agents live under `scripts/agents/perceive/`; orchestrated via `__init__.sh --mode`.

| Agent | Path | Schedule | Role |
|-------|------|----------|------|
| HealthCruise | `infra/healthcruise.sh` | every 6h | EIP→ALB→EC2→RDS/ElastiCache→NAT→SG |
| TopoScan | `infra/toposcan.sh` | daily | Delegates `aws-topo-discovery/scripts/topo-scan.sh` |
| ConfigDrift | `infra/configdrift.sh` | on-demand | Baseline diff via topo-discovery baseline |
| CostWatch | `cost/costwatch.sh` | daily | Cost Explorer anomalies + budget |
| SecurityScan | `security/securityscan.sh` | daily | SG audit + GuardDuty + Security Hub |
| AuditTrail | `security/audittrail.sh` | daily | CloudTrail anomaly API patterns |
| AdvisorScan | `advisor/advisorscan.sh` | daily | Trusted Advisor + Compute Optimizer summary |

See [`perceive-design.md`](perceive-design.md).

## Variable Convention (full)

| Placeholder | Source | Agent Action |
|-------------|--------|--------------|
| `{{env.AWS_ACCESS_KEY_ID}}` | Runtime env | Fail closed if unset (unless `AWS_PROFILE`/role) |
| `{{env.AWS_SECRET_ACCESS_KEY}}` | Runtime env | Never log; mask as `AKIA******` |
| `{{env.AWS_DEFAULT_REGION}}` | Runtime env | Default region when user omits |
| `{{env.AWS_PROFILE}}` | Runtime env | Overrides explicit keys |
| `{{user.scope_name}}` | User input | Workload label (customer / app name) |
| `{{user.safety_confirm}}` | User input | Explicit scope confirmation for full-account patrol |
| `{{user.tag_key}}` | User input | e.g. `customer`, `Environment` |
| `{{user.tag_value}}` | User input | e.g. `prod-acme` |
| `{{user.resource_group}}` | User input | AWS Resource Group name (preferred scope) |
| `{{user.scenario}}` | User input | `daily_check` / `emergency` / `capacity` / … |
| `{{user.enable_ssm}}` | User input | Y/N — SSM Run Command deep checks |
| `{{user.enable_pi}}` | User input | Y/N — RDS Performance Insights (default Y) |
| `{{user.enable_guru}}` | User input | Y/N — DevOps Guru insights (default Y) |
| `{{user.assume_role_arn}}` | User input | Cross-account STS role ARN |
| `{{user.regions}}` | User input | Comma-separated regions |
| `{{user.enable_xray}}` | User input | Y/N — X-Ray service graph (502/latency) |
| `{{output.topology}}` | TopoScan / topo-discovery | JSON manifest |
| `{{output.metrics}}` | CloudWatch aggregation | JSON |
| `{{output.chain_inference}}` | Phase 3 inference | Markdown |

## Safety Gates (Read-Only)

| Rule | Requirement |
|------|-------------|
| No delete/terminate/stop/modify | HALT; Safety = 0 |
| No SG rule changes | Recommend only via `aws-vpc-ops` after user confirm |
| No credential exposure | Mask keys; no secret values in reports |
| Scope required | Must filter by Resource Group or tag; no full-account unless user confirms `scope=full` |
| Findings schema | All findings MUST match [`incident-schema.md`](incident-schema.md) |
| Report persistence | JSON → `audit-results/` (git-ignored) |

## Pre-flight & Execution Flow

Every runbook follows: **Pre-flight → Execute → Validate → Recover**

| Step | Actions |
|------|---------|
| Pre-flight | `aws sts get-caller-identity`, scope confirmation (RG/tag), CLI/jq check, interactive prompts per [`runbooks/01-daily-health-check.md`](../runbooks/01-daily-health-check.md). Non-interactive: `--resource-group`, `--tag-key`/`--tag-value`, `--non-interactive` |
| Execute | **3-phase execution** (details in `runbooks/`):<br>1 — Sniff + topology: Resource Groups Tagging API, VPC/ELB/EC2/RDS inventory → Sniff report<br>2 — Deep collect: CloudWatch 6h + WoW, optional SSM/PI, CloudTrail window → Metric bundles<br>3 — Infer + report: Rules in [`inference-rules.md`](inference-rules.md) → Markdown + JSON incidents |
| Validate | Grade PASS/WARNING/CRITICAL per [`incident-schema.md`](incident-schema.md) |
| Recover | Throttle backoff 3×; AccessDenied → HALT; empty scope → HALT |

**CLI entry**:

```bash
python3 runbooks/scripts/daily-health-check.py \
  --resource-group prod-web-rg \
  --region us-east-1,us-west-2 \
  --enable-xray --render-topology \
  --assume-role arn:aws:iam::123456789012:role/ReadOnlyCruise \
  --non-interactive
```

**Alarm-driven**:

```bash
bash runbooks/scripts/alarm-trigger.sh --alarm-name prod-alb-5xx \
  --resource-group prod-web-rg --region us-east-1 --symptom 502
```

**Orchestrator**: `python3 runbooks/scripts/cruise-orchestrator.py --scenario daily_check`

**Workflow (deterministic)**: `python3 runbooks/scripts/workflow-runner.py --runbook 01 --resource-group <name>`

## Orchestrator Integration

Patrol scripts emit `aiops_context` JSON (compatible with `aws-aiops-orchestrator`). See [`orchestrator-integration.md`](orchestrator-integration.md). Escalate when ≥ 3 CRITICAL findings.

## Risk Model

Unified `risk_evidence[]` with WoW trend + static thresholds. ML gray release via `AIOPS_ML_MODE` (default `off`). See [`risk-model.md`](risk-model.md).

## CI/CD

Scheduled patrol (includes topology overlay): [`assets/ci-cd-templates/github-actions-cruise.yml`](../assets/ci-cd-templates/github-actions-cruise.yml)

GitLab CI: [`assets/ci-cd-templates/gitlab-ci-cruise.yml`](../assets/ci-cd-templates/gitlab-ci-cruise.yml)

GitLab OIDC (no static keys): [`assets/ci-cd-templates/gitlab-ci-cruise-oidc.yml`](../assets/ci-cd-templates/gitlab-ci-cruise-oidc.yml) — see [`gitlab-oidc-integration.md`](gitlab-oidc-integration.md)

OIDC trust policy generator (GitHub + GitLab): `runbooks/scripts/generate-oidc-trust-policy.py` — [`ci-oidc-trust.md`](ci-oidc-trust.md)

Alarm → cruise: [`assets/ci-cd-templates/eventbridge-alarm-cruise.json`](../assets/ci-cd-templates/eventbridge-alarm-cruise.json) + [`eventbridge-alarm-integration.md`](eventbridge-alarm-integration.md)

## Quality Gate (GCL) — full rubric

| Dimension | Threshold | Notes |
|-----------|-----------|-------|
| Correctness | ≥ 0.5 | Findings match live state |
| Safety | = 1 | Any write → ABORT |
| Idempotency | ≥ 0.8 | Same scope → consistent structure |
| Traceability | ≥ 0.8 | `run_id`, commands, `audit-results/` path |
| Spec Compliance | ≥ 0.8 | Runbook + incident schema |

GCL: **optional**, `max_iter=3`. Prompts: [`prompt-templates.md`](prompt-templates.md). Rubric: [`rubric.md`](rubric.md).

## Token Efficiency (TE-1…TE-6)

| Rule | Status | Notes |
|------|--------|-------|
| TE-1: No hardcoded version/port/state tables | Partial | Thresholds in [`threshold-definitions.md`](threshold-definitions.md) are AWS-stable conventions; flagged as "default starting points" |
| TE-2: No SDK docstrings | Pass | Inline code comments only |
| TE-3: Compact error tables | Pass | Single-row Recover table |
| TE-4: JSON paths centralized at file top | Pass | [`execution-guide.md`](execution-guide.md) centralizes all paths |
| TE-5: YAML anchors in example config | N/A | No `example-config.yaml` (read-only skill) |
| TE-6: No duplicated flows across SKILL.md and references | Pass | Execution flow consolidated in this file |

## Runbook Index

| ID | Scenario | Risk | Time |
|----|----------|------|------|
| 01 | Daily health check | Low | 5–15 min |
| 02 | Emergency troubleshoot | High | 3–8 min |
| 03 | Capacity planning | Medium | 5–10 min |
| 04 | Pre-launch check | High | 10–20 min |
| 05 | Slow query diagnosis | Medium | 5–15 min |
| 06 | Connection storm | High | 3–8 min |
| 07 | Bottleneck localization | High | 5–12 min |
| 08 | ElastiCache performance | Medium | 3–8 min |
| 09 | Auto Scaling optimization | Medium | 3–10 min |

Index: [`runbooks/00-index.md`](../runbooks/00-index.md).

## Reference Index

See [`runbooks/00-index.md`](../runbooks/00-index.md) for runbooks 01–09. Key references: [`execution-guide.md`](execution-guide.md), [`threshold-definitions.md`](threshold-definitions.md), [`inference-rules.md`](inference-rules.md), [`incident-schema.md`](incident-schema.md), [`orchestrator-integration.md`](orchestrator-integration.md), [`topo-overlay-integration.md`](topo-overlay-integration.md), [`changelog.md`](changelog.md).

### Parallel GCL

For composite rules that decompose into independent subtasks (e.g., WAF-ALB-01 requiring both `_shared.py` PRODUCTS entry and `_inference.py` rule), use **Parallel GCL**: fan out to multiple Generators (each edits a different file), then a single Critic audits all outputs with cross-referencing. See [`execution-guide.md`](execution-guide.md) §Parallel GCL and `gcl-spec.md` §12.
