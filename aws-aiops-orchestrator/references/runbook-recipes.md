# Runbook Recipes — Cross-Service Remediation Library

## 1. Recipe Schema

Each runbook is a deterministic, multi-skill execution plan. It is the
orchestrator's primary unit of "self-heal" action.

```yaml
runbook:
  id: <RB-NNN>
  name: <short>
  trigger_rules: [<rule-id>, ...]        # which detection rules map here
  intent: <rca | self-heal | cost-forecast | change-impact>
  default_decision_tier: <AUTO_HEAL | AI_ASSIST | MANUAL>
  preconditions: [<free text or rule ids>]
  steps:
    - id: <S1, S2, ...>
      skill: <aws-*-ops or 'orchestrator'>
      action: <verb phrase>
      params: { ... }
      on_failure: <halt | skip | fallback>
      rollback: <how to undo>
      idempotency_key: <key template>
      requires_confirm: <bool>
  post_checks:
    - <verification step>
  estimated_mttr: <ISO-8601 duration>
  rollback_strategy: <free text>
  owner: <team>
  tested_in: <environments>
```

## 2. RB-001 — Target Health Flapping

**Trigger**: FD-01
**Decision tier**: AUTO_HEAL
**Goal**: stop the flapping loop without losing capacity.

```yaml
runbook:
  id: RB-001
  name: "Target Health Flapping"
  trigger_rules: [FD-01]
  default_decision_tier: AUTO_HEAL

  steps:
    - id: S1
      skill: aws-cloudwatch-ops
      action: capture_last_15m_metrics
      params: { metric: "TargetResponseTime,UnHealthyHostCount", period: PT1M }
      on_failure: halt

    - id: S2
      skill: aws-elb-ops
      action: describe_target_health
      params: { target_group_arn: "{{u.tg_arn}}" }
      on_failure: halt

    - id: S3
      skill: aws-cloudtrail-ops
      action: check_recent_config_changes
      params: { resource: "{{u.tg_arn}}", window: PT30M }
      on_failure: skip

    - id: S4
      skill: aws-elb-ops
      action: deregister_flapping_targets
      params:
        target_group_arn: "{{u.tg_arn}}"
        targets: "{{S2.flapping_targets}}"
      requires_confirm: false    # non-destructive
      on_failure: halt
      rollback: register_targets

    - id: S5
      skill: aws-autoscaling-ops
      action: increase_desired_capacity
      params:
        asg_name: "{{S2.associated_asg}}"
        delta: "{{S4.deregistered_count}}"
      on_failure: AI_ASSIST

    - id: S6
      skill: aws-elb-ops
      action: wait_for_new_targets_healthy
      params: { timeout: PT5M }

  post_checks:
    - verify: UnHealthyHostCount == 0 for PT5M
    - verify: ASG InServiceCapacity >= original count

  estimated_mttr: PT5M
  rollback_strategy: "Register the original targets back; reduce ASG capacity."
```

## 3. RB-002 — Target Unhealthy (Persistent)

**Trigger**: FD-06 (status check fail)
**Decision tier**: AUTO_HEAL
**Goal**: replace unhealthy instance.

```yaml
runbook:
  id: RB-002
  name: "Target Unhealthy (Persistent)"
  trigger_rules: [FD-06]
  default_decision_tier: AUTO_HEAL

  steps:
    - id: S1
      skill: aws-cloudwatch-ops
      action: get_status_check_history
      params: { instance_id: "{{u.instance_id}}", window: PT30M }

    - id: S2
      skill: aws-cloudtrail-ops
      action: check_recent_ec2_state_changes
      params: { resource: "{{u.instance_id}}", window: PT1H }

    - id: S3
      decision: |
        If status check is "System" → reboot instance (AUTO_HEAL).
        If status check is "Instance" → terminate + replace via ASG (AUTO_HEAL).

    - id: S4 [system check path]
      skill: aws-ec2-ops
      action: reboot_instance
      params: { instance_id: "{{u.instance_id}}" }
      requires_confirm: false
      on_failure: terminate_instance
      idempotency_key: "reboot-{{u.instance_id}}-{{u.incident_id}}"

    - id: S5 [instance check path]
      skill: aws-autoscaling-ops
      action: terminate_instance_and_wait_for_replacement
      params: { instance_id: "{{u.instance_id}}" }

    - id: S6
      skill: aws-elb-ops
      action: wait_for_replacement_healthy
      params: { tg_arn: "{{u.tg_arn}}", timeout: PT10M }

  post_checks:
    - verify: instance StatusCheckFailed == 0
    - verify: TG has healthy replacement

  estimated_mttr: PT8M
  rollback_strategy: "If reboot worsens state, escalate to terminate+replace."
```

## 4. RB-003 — Latency Spike (P99)

**Trigger**: FD-02
**Decision tier**: AI_ASSIST
**Goal**: find the slowest dependency and propose mitigation.

```yaml
runbook:
  id: RB-003
  name: "Latency Spike (P99)"
  trigger_rules: [FD-02]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-cloudwatch-ops
      action: get_p99_latency_breakdown
      params: { lb_arn: "{{u.lb_arn}}", window: PT1H }

    - id: S2
      skill: aws-ec2-ops
      action: check_instance_cpu_and_status
      params: { instance_ids: "{{u.target_instance_ids}}" }

    - id: S3
      skill: aws-rds-ops
      action: check_db_performance
      params: { db_instance_id: "{{u.associated_db}}" }
      # Includes Performance Insights if enabled.

    - id: S4
      skill: aws-cloudwatch-ops
      action: logs_insights_query
      params:
        log_groups: ["/aws/elb/{{u.lb_name}}"]
        query: "stats avg(@duration) by bin(5m)"

    - id: S5 [orchestrator]
      skill: orchestrator
      action: rank_likely_causes
      params: { data_from: [S1, S2, S3, S4] }
      # Pure orchestration logic; outputs ranked hypotheses.

    - id: S6 [recommended mitigations, all AI_ASSIST]
      skill: aws-autoscaling-ops
      action: propose_scale_out
      requires_confirm: true

    - id: S7
      skill: aws-rds-ops
      action: propose_query_optimization
      requires_confirm: true

  estimated_mttr: PT30M
  rollback_strategy: "All proposed actions are scale-out / read-replica; safe to revert."
```

## 5. RB-004 — Certificate 7-Day Expiry

**Trigger**: PD-01 (severity=high)
**Decision tier**: AUTO_HEAL
**Goal**: renew certificate and re-validate.

```yaml
runbook:
  id: RB-004
  name: "Certificate 7-Day Expiry"
  trigger_rules: [PD-01]
  default_decision_tier: AUTO_HEAL

  steps:
    - id: S1
      skill: aws-acm-ops
      action: check_validation_method
      params: { cert_arn: "{{u.cert_arn}}" }
      # DNS validation is preferred; email requires human intervention.

    - id: S2 [DNS validation path]
      skill: aws-acm-ops
      action: renew_certificate
      params: { cert_arn: "{{u.cert_arn}}" }

    - id: S3
      skill: aws-route53-ops
      action: verify_or_create_validation_records
      params: { cert_arn: "{{u.cert_arn}}" }

    - id: S4
      skill: aws-acm-ops
      action: wait_for_issued
      params: { cert_arn: "{{u.cert_arn}}", timeout: PT30M }

    - id: S5
      skill: aws-elb-ops
      action: verify_listener_binding
      params: { lb_arn: "{{u.lb_arn}}", cert_arn: "{{u.cert_arn}}" }

  post_checks:
    - verify: cert status == ISSUED
    - verify: TLS handshake succeeds against LB endpoint

  estimated_mttr: PT20M
  rollback_strategy: "Old cert remains until new one is validated."
```

## 6. RB-005 — WAF DDoS Pattern

**Trigger**: WAF rate spike
**Decision tier**: AUTO_HEAL
**Goal**: enable rate limiting or AWS Managed Rules.

```yaml
runbook:
  id: RB-005
  name: "WAF DDoS Pattern"
  trigger_rules: ["WAF-rate-spike"]
  default_decision_tier: AUTO_HEAL

  steps:
    - id: S1
      skill: aws-waf-ops
      action: analyze_traffic_pattern
      params: { web_acl_arn: "{{u.web_acl_arn}}", window: PT15M }

    - id: S2
      skill: aws-elb-ops
      action: get_request_rate_per_source_ip
      params: { lb_arn: "{{u.lb_arn}}" }

    - id: S3
      skill: aws-waf-ops
      action: create_or_update_rate_based_rule
      params:
        web_acl_arn: "{{u.web_acl_arn}}"
        limit: 2000   # 2000 req / 5min per IP
        action: block
      requires_confirm: false   # rate-limiting rule is safe to add

    - id: S4
      skill: aws-waf-ops
      action: enable_aws_managed_rule_known_bad_inputs
      params: { web_acl_arn: "{{u.web_acl_arn}}" }

    - id: S5
      skill: aws-cloudwatch-ops
      action: create_alarm_on_blocked_requests
      params: { web_acl_arn: "{{u.web_acl_arn}}" }

  post_checks:
    - verify: WAF blocked-request rate declines within 10m
    - verify: false-positive rate < 1% (sampled requests)

  estimated_mttr: PT5M
  rollback_strategy: "Remove rate rule + revert Managed Rule priority."
```

## 7. RB-006 — Cost Spike Investigation

**Trigger**: CO-09
**Decision tier**: MANUAL (cost is never auto-remediated)
**Goal**: identify driver, recommend mitigations.

```yaml
runbook:
  id: RB-006
  name: "Cost Spike Investigation"
  trigger_rules: [CO-09]
  default_decision_tier: MANUAL

  steps:
    - id: S1 [orchestrator]
      skill: orchestrator
      action: get_cost_anomaly_details
      params: { window: P7D }
      # Uses Cost Explorer anomaly detection directly.

    - id: S2
      skill: orchestrator
      action: group_anomaly_by_service_and_tag
      # Pure orchestration.

    - id: S3
      skill: aws-s3-ops
      action: check_storage_class_distribution
      params: { buckets: "{{S2.top_s3_buckets}}" }
      # if S3 is the driver.

    - id: S4
      skill: aws-ec2-ops
      action: check_running_instances_and_rates
      params: { instance_ids: "{{S2.top_ec2_instances}}" }
      # if EC2/Compute Optimizer flags.

    - id: S5
      skill: aws-elb-ops
      action: check_lb_consumption
      params: { lb_arns: "{{S2.top_lbs}}" }

    - id: S6 [orchestrator]
      skill: orchestrator
      action: emit_recommendations
      requires_confirm: true   # all recommendations require human approval

  estimated_mttr: PT1H
  rollback_strategy: "N/A — recommendation only."
```

## 8. RB-007 — Production 5xx Surge

**Trigger**: FD-03 + FD-10 correlation
**Decision tier**: AUTO_HEAL (with safety gates)
**Goal**: triage, mitigate, notify.

```yaml
runbook:
  id: RB-007
  name: "Production 5xx Surge"
  trigger_rules: [FD-03, FD-10]
  default_decision_tier: AUTO_HEAL

  preconditions:
    - At least 1 unhealthy target (NOT all — see FD-10 downgrade).
    - Recent code deploy in last 30m? If yes, consider RB-002 alternative.

  steps:
    - id: S1
      skill: aws-elb-ops
      action: capture_5xx_metrics_and_target_health
      params: { lb_arn: "{{u.lb_arn}}", window: PT15M }

    - id: S2
      skill: aws-cloudtrail-ops
      action: check_recent_changes
      params: { resources: "{{S1.targets}}", window: PT30M }

    - id: S3
      skill: aws-ec2-ops
      action: check_instance_health
      params: { instance_ids: "{{S1.targets}}" }

    - id: S4
      skill: aws-rds-ops
      action: check_db_health
      params: { db_id: "{{u.associated_db}}" }

    - id: S5 [decision gate]
      skill: orchestrator
      action: decide_remediation
      # branches to: target_re_register | scale_out | dns_failover | notify_only

    - id: S6 [scale-out branch]
      skill: aws-autoscaling-ops
      action: scale_out
      params: { asg_name: "{{u.asg}}", delta: +2 }
      requires_confirm: false

    - id: S7 [dns failover branch, if multi-region]
      skill: aws-route53-ops
      action: failover_to_secondary_region
      requires_confirm: true   # affects user-visible traffic

    - id: S8 [always]
      skill: aws-sns-ops
      action: publish_incident_notification
      params: { topic_arn: "{{u.incident_topic}}" }
      requires_confirm: false

  post_checks:
    - verify: 5xx rate returns to <0.1% within 15m
    - verify: All targets healthy

  estimated_mttr: PT15M
  rollback_strategy: "DNS failover reversal; ASG scale-in (if manual)."
```

## 9. RB-008 — Compliance Drift (S3 Block Public Access)

**Trigger**: SD-02
**Decision tier**: AI_ASSIST
**Goal**: confirm intent, then enable BPA.

```yaml
runbook:
  id: RB-008
  name: "S3 Public Access Drift"
  trigger_rules: [SD-02]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-s3-ops
      action: audit_bucket_policy_and_acl
      params: { bucket: "{{u.bucket}}" }

    - id: S2 [orchestrator]
      skill: orchestrator
      action: assess_breaking_risk
      # Check for static-website hosting, public-read CDN origin, etc.

    - id: S3
      skill: aws-s3-ops
      action: enable_block_public_access
      params:
        bucket: "{{u.bucket}}"
        block_public_acls: true
        ignore_public_acls: true
        block_public_policy: true
        restrict_public_buckets: true
      requires_confirm: true   # always — this can break public sites

  estimated_mttr: PT10M
  rollback_strategy: "Disable BPA via the same API."
```

## 10. RB-009 — Idle LB Detection

**Trigger**: CO-01, CO-02
**Decision tier**: MANUAL
**Goal**: identify and recommend removal.

```yaml
runbook:
  id: RB-009
  name: "Idle Load Balancer"
  trigger_rules: [CO-01, CO-02]
  default_decision_tier: MANUAL

  steps:
    - id: S1
      skill: aws-elb-ops
      action: gather_lcu_consumption_30d
      params: { lb_arn: "{{u.lb_arn}}" }

    - id: S2
      skill: aws-elb-ops
      action: check_incoming_outgoing_traffic_30d
      params: { lb_arn: "{{u.lb_arn}}" }

    - id: S3 [orchestrator]
      skill: orchestrator
      action: confirm_idle_threshold
      # Must be below threshold for full 14 consecutive days.

    - id: S4
      skill: aws-route53-ops
      action: check_dns_records_pointing_to_lb
      params: { lb_dns_name: "{{u.lb_dns}}" }

    - id: S5 [orchestrator]
      skill: orchestrator
      action: emit_recommendation
      requires_confirm: true   # deletion is destructive

  estimated_mttr: PT1H
  rollback_strategy: "Deletion is irreversible within 24h; can recreate LB with same name after that."
```

## 11. RB-010 — RDS Connection Saturation

**Trigger**: PD-04
**Decision tier**: AI_ASSIST
**Goal**: identify connection leak or scale up.

```yaml
runbook:
  id: RB-010
  name: "RDS Connection Saturation"
  trigger_rules: [PD-04]
  default_decision_tier: AI_ASSIST
  preconditions:
    - If target is Aurora cluster behind RDS Proxy, prefer RB-027 (aws-aurora-ops)

  steps:
    - id: S1
      skill: aws-rds-ops
      action: get_connection_breakdown_by_user
      params: { db_id: "{{u.db_id}}" }
      # Uses Performance Insights.

    - id: S2
      skill: aws-ssm-ops
      action: sample_active_app_connections
      params: { targets: "{{u.app_instance_ids}}" }

    - id: S3
      skill: aws-rds-ops
      action: get_recent_slow_queries
      params: { db_id: "{{u.db_id}}" }

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_action
      # branches: scale_up_class | enable_connection_pooling | kill_idle_sessions

    - id: S5
      skill: aws-rds-ops
      action: modify_db_instance_class
      requires_confirm: true

  estimated_mttr: PT30M
  rollback_strategy: "DB instance class modification requires a brief failover but is reversible."
```

## 11. RB-011 — Lambda Throttling

**Trigger**: FD-11
**Decision tier**: AI_ASSIST
**Goal**: raise concurrency to absorb invocation burst.

```yaml
runbook:
  id: RB-011
  name: "Lambda Throttling"
  trigger_rules: [FD-11]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-cloudwatch-ops
      action: get_throttle_rate_and_duration
      params: { function_name: "{{u.function_name}}", window: PT30M }

    - id: S2
      skill: aws-lambda-ops
      action: check_reserved_concurrency
      params: { function_name: "{{u.function_name}}" }

    - id: S3
      skill: aws-eventbridge-ops
      action: check_incoming_event_rate
      params: { source: "{{u.event_source_arn}}", window: PT30M }

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_concurrency_adjustment
      # branches: raise_reserved | enable_provisioned | scale_source

    - id: S5
      skill: aws-lambda-ops
      action: put_reserved_concurrency
      params: { reserved: "{{S4.target_reserved}}" }
      requires_confirm: true

    - id: S6
      skill: aws-cloudwatch-ops
      action: wait_for_throttle_count_to_zero
      params: { function_name: "{{u.function_name}}", timeout: PT10M }

  estimated_mttr: PT15M
  rollback_strategy: "Reduce reserved concurrency; provisioned concurrency settles within 24h."
```

## 12. RB-012 — Lambda Iterator Age (Stream Sources)

**Trigger**: FD-12
**Decision tier**: AI_ASSIST
**Goal**: increase batch size or parallelism.

```yaml
runbook:
  id: RB-012
  name: "Lambda Iterator Age"
  trigger_rules: [FD-12]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-lambda-ops
      action: get_event_source_mapping
      params: { function_name: "{{u.function_name}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_iterator_age_and_concurrency
      params: { function_name: "{{u.function_name}}", window: PT30M }

    - id: S3 [decision gate]
      skill: orchestrator
      action: decide_adjustment
      # branches: increase_batch_size | increase_parallelism | scale_function

    - id: S4
      skill: aws-lambda-ops
      action: update_event_source_mapping
      params: { uuid: "{{S1.uuid}}", batch_size: "{{S4.new_batch_size}}", parallelization_factor: "{{S4.new_parallelism}}" }
      requires_confirm: true

  estimated_mttr: PT10M
  rollback_strategy: "Revert ESM parameters; changes are reversible."
```

## 13. RB-013 — VPC Flow Log Anomaly

**Trigger**: Network anomaly detected via VPC Flow Logs
**Decision tier**: AI_ASSIST
**Goal**: identify unusual egress/ingress patterns.

```yaml
runbook:
  id: RB-013
  name: "VPC Flow Log Anomaly"
  trigger_rules: ["VPC-flow-anomaly"]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-vpc-ops
      action: query_flow_logs_logs_insights
      params:
        log_group: "{{u.vpc_flow_log_group}}"
        query: "stats sum(bytes) by srcaddr, dstaddr, dstport | sort desc | limit 20"
        window: PT1H

    - id: S2
      skill: aws-vpc-ops
      action: identify_top_talkers
      params: { data: "{{S1.results}}" }

    - id: S3
      skill: aws-guardduty-ops
      action: check_correlated_findings
      params: { window: PT2H }

    - id: S4 [orchestrator]
      skill: orchestrator
      action: classify_pattern
      # benign (backup, deploy) | suspicious (data exfil, port scan) | misconfig

    - id: S5 [suspicious path]
      skill: aws-vpc-ops
      action: create_isolation_sg_proposal
      requires_confirm: true

    - id: S6 [always]
      skill: aws-sns-ops
      action: publish_network_anomaly_finding
      requires_confirm: false

  estimated_mttr: PT30M
  rollback_strategy: "N/A — investigation and notification only at this tier."
```

## 14. RB-014 — Security Group 0.0.0.0/0 Drift

**Trigger**: SD-03
**Decision tier**: MANUAL (network exposure change is risky)
**Goal**: confirm intent before revoking open ingress.

```yaml
runbook:
  id: RB-014
  name: "Security Group Open Ingress Drift"
  trigger_rules: [SD-03]
  default_decision_tier: MANUAL

  steps:
    - id: S1
      skill: aws-ec2-ops
      action: describe_sg_rules
      params: { sg_id: "{{u.sg_id}}" }

    - id: S2
      skill: aws-cloudtrail-ops
      action: check_recent_sg_changes
      params: { resource: "{{u.sg_id}}", window: PT7D }

    - id: S3
      skill: aws-vpc-ops
      action: identify_attached_resources
      params: { sg_id: "{{u.sg_id}}" }

    - id: S4
      skill: aws-elb-ops
      action: check_lb_dependency
      params: { lb_arns: "{{S3.attached_lbs}}" }

    - id: S5 [orchestrator]
      skill: orchestrator
      action: emit_remediation_proposal
      # propose: revoke the offending rule, OR scope to specific CIDR, OR add WAF in front

    - id: S6
      skill: aws-ec2-ops
      action: revoke_security_group_ingress
      params: { sg_id: "{{u.sg_id}}", ip_permissions: "{{S5.to_revoke}}" }
      requires_confirm: true

  estimated_mttr: PT1H
  rollback_strategy: "Re-authorize the ingress rule via authorize-security-group-ingress."
```

## 15. RB-015 — EBS Volume Saturation

**Trigger**: PD-02
**Decision tier**: AI_ASSIST
**Goal**: resize volume or clean up before disk fills.

```yaml
runbook:
  id: RB-015
  name: "EBS Volume Saturation"
  trigger_rules: [PD-02]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-ec2-ops
      action: describe_volume_usage
      params: { volume_id: "{{u.volume_id}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_disk_used_percent_trend
      params: { instance_id: "{{u.attached_instance}}", window: P7D }

    - id: S3
      skill: aws-cloudwatch-ops
      action: forecast_disk_full_date
      params: { instance_id: "{{u.attached_instance}}" }
      # Linear extrapolation from S2 trend.

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_action
      # branches: grow_volume | cleanup_logs | rotate_logs | migrate_to_larger_instance

    - id: S5
      skill: aws-ec2-ops
      action: modify_volume_size
      params: { volume_id: "{{u.volume_id}}", new_size_gb: "{{S4.new_size}}" }
      requires_confirm: true

    - id: S6
      skill: aws-ssm-ops
      action: extend_filesystem
      params: { instance_id: "{{u.attached_instance}}", mount_point: "{{u.mount_point}}" }
      requires_confirm: true

  estimated_mttr: PT20M
  rollback_strategy: "Volume can be grown but not shrunk; restore from snapshot if size is wrong."
```

## 16. RB-016 — KMS Key Compliance Failure

**Trigger**: SD-05, KMS health audit findings
**Decision tier**: AI_ASSIST
**Goal**: ensure rotation enabled, deletion cancelled, grants intact.

```yaml
runbook:
  id: RB-016
  name: "KMS Key Compliance Failure"
  trigger_rules: [SD-05]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-kms-ops
      action: describe_key
      params: { key_id: "{{u.key_id}}" }

    - id: S2
      skill: aws-kms-ops
      action: list_grants
      params: { key_id: "{{u.key_id}}" }

    - id: S3
      skill: aws-cloudwatch-ops
      action: check_rotation_status
      params: { key_id: "{{u.key_id}}" }

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_action
      # branches: enable_rotation | cancel_deletion | reattach_grant

    - id: S5 [enable rotation path]
      skill: aws-kms-ops
      action: enable_key_rotation
      requires_confirm: false   # rotation is safe and reversible

    - id: S6 [cancel deletion path]
      skill: aws-kms-ops
      action: cancel_key_deletion
      requires_confirm: true    # reverses intentional pending deletion

  estimated_mttr: PT10M
  rollback_strategy: "Disable rotation; deletion cannot be re-queued from cancelled state."
```

## 17. RB-017 — IAM Credential Leak Response

**Trigger**: SD-04
**Decision tier**: MANUAL (security incident; legal implications)
**Goal**: contain and rotate exposed credentials.

```yaml
runbook:
  id: RB-017
  name: "IAM Credential Leak Response"
  trigger_rules: [SD-04]
  default_decision_tier: MANUAL

  steps:
    - id: S1
      skill: aws-iam-ops
      action: identify_user_and_access_keys
      params: { finding: "{{u.finding}}" }

    - id: S2
      skill: aws-cloudtrail-ops
      action: check_recent_api_calls_by_principal
      params: { principal: "{{S1.user_arn}}", window: PT24H }

    - id: S3
      skill: aws-iam-ops
      action: disable_access_key
      params: { user: "{{S1.user_name}}", access_key: "{{S1.compromised_key}}" }
      requires_confirm: true

    - id: S4
      skill: aws-iam-ops
      action: create_new_access_key
      requires_confirm: true

    - id: S5
      skill: aws-iam-ops
      action: delete_old_access_key
      requires_confirm: true

    - id: S6
      skill: aws-sns-ops
      action: notify_security_team
      requires_confirm: false

  estimated_mttr: PT1H
  rollback_strategy: "N/A — credentials rotation is forward-only; record incident in audit log."
```

## 18. RB-SEC-01 — Compromised Instance Isolation

**Trigger**: SD-01 (GuardDuty CRITICAL finding, severity >= 7.0 — CryptoCurrency/Backdoor/Trojan on EC2)
**Decision tier**: AI_ASSIST (non-destructive SG swap, but blast radius on prod instance is large; human confirms)
**Goal**: snapshot evidence, isolate the instance behind a forensic quarantine SG, archive the finding, notify security oncall.

```yaml
runbook:
  id: RB-SEC-01
  name: "Compromised Instance Isolation"
  trigger_rules: [SD-01]
  default_decision_tier: AI_ASSIST
  preconditions:
    - finding.resource.type == "EC2 instance"
    - instance state != "terminated"

  steps:
    - id: S1 [orchestrator]
      skill: orchestrator
      action: enrich_finding
      params: { finding: "{{u.finding}}" }
      # Pull instance-id, attached ENIs/volumes, current SG, account/region,
      # detector_id; emit forensic context used by S3-S6.

    - id: S2
      skill: aws-cloudtrail-ops
      action: lookup_events
      params:
        # Filter by resource ARN or username to find instance-related API calls
        LookupAttributes: [{Key: Resource, Value: "arn:aws:ec2:{{user.region}}:{{user.account_id}}:instance/{{S1.instance_id}}"}]
        StartTime: "{{u.window_start}}"
        EndTime: "{{u.window_end}}"
      on_failure: skip

    - id: S3
      skill: aws-ec2-ops
      action: create_forensic_snapshots
      params:
        instance_id: "{{S1.instance_id}}"
        finding_id: "{{u.finding.id}}"
      on_failure: halt
      # EVIDENCE — preserve before any isolation. Backs the rollback path.

    - id: S4
      skill: aws-ec2-ops
      action: modify_instance_attribute
      params:
        instance_id: "{{S1.instance_id}}"
        # EC2 ModifyInstanceAttribute --groups replaces ALL security groups
        Groups: ["{{u.forensic_quarantine_sg_id}}"]
      requires_confirm: true   # SG swap is the only write — large blast radius
      on_failure: halt
      idempotency_key: "rbs01-{{u.finding.id}}"
      rollback: modify_instance_attribute -> restore original Groups list

    - id: S5
      skill: aws-guardduty-ops
      action: archive_finding
      params:
        detector_id: "{{S1.detector_id}}"
        finding_id: "{{u.finding.id}}"
      on_failure: skip

    - id: S6
      skill: aws-sns-ops
      action: publish
      params:
        topic_arn: "{{u.security_topic_arn}}"
        subject: "GuardDuty CRITICAL — instance isolation ({{u.finding.id}})"
        message: "{{S1.context}}"
      requires_confirm: false

    - id: S7 [orchestrator]
      skill: orchestrator
      action: schedule_post_checks
      params:
        window: PT30M
        checks:
          - verify: SSM session reachable on instance
          - verify: no new outbound connections via VPC Flow Logs

  post_checks:
    - verify: instance still reachable via SSM Session Manager
    - verify: zero new outbound connections for PT30M (via VPC Flow Logs)

  estimated_mttr: PT15M
  rollback_strategy: "Restore original SG association via modify-instance-attribute (groups). Snapshots retained 90d minimum; no destructive action beyond SG swap."
  owner: security
  tested_in: [staging]
```

## 19. RB-SEC-18 — Root Account Usage Alert

**Trigger**: SD-07 (CloudTrail event with `userIdentity.type == Root`)
**Decision tier**: AI_ASSIST (notify + propose hard-mitigations; human confirms writes)
**Goal**: capture the root event, install a durable alarm, notify security oncall, and propose account-hardening actions.

```yaml
runbook:
  id: RB-SEC-18
  name: "Root Account Usage Alert"
  trigger_rules: [SD-07]
  default_decision_tier: AI_ASSIST
  preconditions:
    - event occurred in last PT5M
    - event.userIdentity.invokedBy != "aws-internal"   # exclude known break-glass chain

  steps:
    - id: S1
      skill: aws-cloudtrail-ops
      action: lookup_events
      params:
        # Filter for root user events
        LookupAttributes: [{Key: Username, Value: "Root"}]
        StartTime: "{{u.start_time}}"
        EndTime: "{{u.end_time}}"
      on_failure: halt

    - id: S2
      skill: aws-cloudtrail-ops
      action: lookup_events
      params:
        LookupAttributes: [{Key: Username, Value: "Root"}]
        StartTime: "{{u.window_24h_start}}"
        EndTime: "{{u.window_24h_end}}"
      on_failure: skip

    - id: S3 [orchestrator]
      skill: orchestrator
      action: enrich_event
      params: { event: "{{S1.event}}" }
      # Tag with severity, geo-IP if available, source-IP reputation.

    - id: S4
      skill: aws-cloudwatch-ops
      action: put_metric_alarm
      params:
        alarm_name: "RootAccountUsage"
        namespace: "AWS/CloudTrail"
        metric_name: "RootUserActivityCount"
        threshold: 1
        period: 300
        statistic: Sum
        treat_missing_data: notBreaching
      requires_confirm: false   # durable monitor; idempotent
      idempotency_key: "rbs18-alarm-RootAccountUsage"

    - id: S5
      skill: aws-sns-ops
      action: publish
      params:
        topic_arn: "{{u.security_oncall_topic_arn}}"
        subject: "HIGH — AWS root account usage detected ({{u.event_id}})"
        message: "{{S3.enriched}}"
      requires_confirm: false

    - id: S6
      skill: aws-iam-ops
      action: get_credential_report
      params: {}
      # Read-only: generate+get credential report; filter rows where user=="<root_account>"
      on_failure: skip
      on_failure: skip

    - id: S7 [orchestrator]
      skill: orchestrator
      action: propose_mitigations
      params: { source: [S1, S2, S6] }
      # Text-only output: disable/delete root access keys, enable root MFA,
      # restrict break-glass role chain. Emitted to operator for review.

  estimated_mttr: PT5M
  rollback_strategy: "N/A — alarm creation is idempotent; SNS notify is forward-only."
  owner: security
  tested_in: [staging]
```

## 20. RB-018 — ElastiCache Connection Saturation

**Trigger**: ElastiCache CPU/connection pressure
**Decision tier**: AI_ASSIST
**Goal**: scale cluster or fix connection leaks.

```yaml
runbook:
  id: RB-018
  name: "ElastiCache Connection Saturation"
  trigger_rules: ["ElastiCache-connection-saturation"]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-elasticache-ops
      action: get_current_connections_and_evictions
      params: { replication_group: "{{u.replication_group}}", window: PT30M }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_cpu_and_evictions_trend
      params: { replication_group: "{{u.replication_group}}", window: P7D }

    - id: S3 [decision gate]
      skill: orchestrator
      action: decide_action
      # branches: scale_out | scale_up_node_type | client_pooling_review

    - id: S4 [scale out]
      skill: aws-elasticache-ops
      action: increase_replica_count
      requires_confirm: true

    - id: S5 [scale up]
      skill: aws-elasticache-ops
      action: modify_replication_group_node_type
      requires_confirm: true    # causes brief failover

  estimated_mttr: PT20M
  rollback_strategy: "Reduce replica count or revert node type (next maintenance window)."
```

## 19. RB-019 — OpenSearch Cluster Yellow/Red

**Trigger**: FD-14
**Decision tier**: AI_ASSIST
**Goal**: rebalance shards and investigate.

```yaml
runbook:
  id: RB-019
  name: "OpenSearch Cluster Yellow/Red"
  trigger_rules: [FD-14]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-opensearch-ops
      action: describe_cluster_health
      params: { domain: "{{u.domain}}" }

    - id: S2
      skill: aws-opensearch-ops
      action: identify_unassigned_shards
      params: { domain: "{{u.domain}}" }

    - id: S3
      skill: aws-cloudwatch-ops
      action: check_storage_and_jvm
      params: { domain: "{{u.domain}}", window: PT1H }

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_action
      # branches: increase_nodes | increase_storage | reduce_shards | restore_snapshot

    - id: S5
      skill: aws-opensearch-ops
      action: update_domain_config
      params: { instance_type: "{{S4.new_type}}", instance_count: "{{S4.new_count}}" }
      requires_confirm: true

  estimated_mttr: PT45M
  rollback_strategy: "Revert domain config; original config retained as prior configuration."
```

## 20. RB-020 — S3 Lifecycle Gap Remediation

**Trigger**: CO-06
**Decision tier**: MANUAL
**Goal**: propose and apply lifecycle policy.

```yaml
runbook:
  id: RB-020
  name: "S3 Lifecycle Gap Remediation"
  trigger_rules: [CO-06]
  default_decision_tier: MANUAL

  steps:
    - id: S1
      skill: aws-s3-ops
      action: analyze_object_age_distribution
      params: { bucket: "{{u.bucket}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_storage_metrics_30d
      params: { bucket: "{{u.bucket}}" }

    - id: S3 [orchestrator]
      skill: orchestrator
      action: generate_lifecycle_policy_proposal
      # Generate YAML lifecycle config based on access patterns.

    - id: S4
      skill: aws-s3-ops
      action: put_bucket_lifecycle_configuration
      params: { bucket: "{{u.bucket}}", configuration: "{{S3.proposal}}" }
      requires_confirm: true

  estimated_mttr: PT15M
  rollback_strategy: "Delete the lifecycle configuration to revert."
```

## 21. RB-021 — Multi-Region DNS Failover

**Trigger**: FD-03 + Route53 health check failure
**Decision tier**: AI_ASSIST (DNS change is user-visible)
**Goal**: shift traffic to healthy region.

```yaml
runbook:
  id: RB-021
  name: "Multi-Region DNS Failover"
  trigger_rules: [FD-03]
  default_decision_tier: AI_ASSIST

  steps:
    - id: S1
      skill: aws-route53-ops
      action: check_health_check_status
      params: { health_check_id: "{{u.primary_health_check_id}}" }

    - id: S2
      skill: aws-elb-ops
      action: verify_secondary_region_healthy
      params: { lb_arn: "{{u.secondary_lb_arn}}" }

    - id: S3
      skill: aws-cloudwatch-ops
      action: verify_secondary_capacity_available
      params: { scope: "{{u.secondary_region}}", metric: "RequestCount" }

    - id: S4 [orchestrator]
      skill: orchestrator
      action: decide_failover
      # branches: fail_over | wait_and_observe | both_regions_down

    - id: S5
      skill: aws-route53-ops
      action: update_failover_record_set
      params: { hosted_zone: "{{u.zone_id}}", primary_weight: 0, secondary_weight: 100 }
      requires_confirm: true    # affects user-visible traffic

    - id: S6
      skill: aws-sns-ops
      action: notify_failover_complete
      requires_confirm: false

  estimated_mttr: PT10M (plus DNS TTL)
  rollback_strategy: "Revert record weights to restore primary."
```

## 22. RB-022 — Cost Spike Containment (Manual)

**Trigger**: CO-09 (Cost anomaly impact > $500/day)
**Decision tier**: MANUAL
**Goal**: identify driver and present cost-saving actions.

```yaml
runbook:
  id: RB-022
  name: "Cost Spike Containment"
  trigger_rules: [CO-09]
  default_decision_tier: MANUAL

  steps:
    - id: S1 [orchestrator]
      skill: orchestrator
      action: get_cost_anomaly_details
      params: { window: P7D }

    - id: S2
      skill: aws-s3-ops
      action: audit_s3_storage_classes_and_lifecycle
      params: { buckets: "{{S1.top_s3_buckets}}" }

    - id: S3
      skill: aws-ec2-ops
      action: list_running_instances_with_rates
      params: { instance_ids: "{{S1.top_ec2_instances}}" }

    - id: S4
      skill: aws-elb-ops
      action: list_lbs_with_consumption
      params: { lb_arns: "{{S1.top_lbs}}" }

    - id: S5
      skill: aws-rds-ops
      action: list_db_instances_with_utilization
      params: { db_ids: "{{S1.top_dbs}}" }

    - id: S6
      skill: aws-vpc-ops
      action: list_nat_gateway_traffic
      params: { nat_gw_ids: "{{S1.top_nat_gateways}}" }

    - id: S7 [orchestrator]
      skill: orchestrator
      action: aggregate_and_rank_savings_opportunities

    - id: S8
      skill: aws-sns-ops
      action: publish_cost_review_report
      requires_confirm: false

  estimated_mttr: PT2H
  rollback_strategy: "N/A — investigation and report only."
```

## 22. RB-023 — Aurora Replica Lag

**Trigger**: FD-15, AURORA-LAG-01
**Decision tier**: AI_ASSIST
**Goal**: diagnose read-side lag and scale readers or writer.

```yaml
runbook:
  id: RB-023
  name: "Aurora Replica Lag"
  trigger_rules: [FD-15, AURORA-LAG-01]
  default_decision_tier: AI_ASSIST
  preconditions:
    - Target is Aurora cluster (engine aurora-mysql or aurora-postgresql)
    - At least one reader instance exists OR writer write load is elevated

  steps:
    - id: S1
      skill: aws-aurora-ops
      action: describe_cluster_and_members
      params: { cluster_id: "{{u.cluster_id}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_metric_statistics
      params:
        namespace: AWS/RDS
        metric: AuroraReplicaLag
        dimensions: { DBClusterIdentifier: "{{u.cluster_id}}" }
        window: PT1H

    - id: S3
      skill: aws-aurora-ops
      action: get_writer_pi_top_sql_and_waits
      params: { cluster_id: "{{u.cluster_id}}" }

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_replica_lag_remediation
      # branches: add_reader | scale_reader_class | scale_writer_class | recommend_app_read_split

    - id: S5
      skill: aws-aurora-ops
      action: create_db_instance_reader
      params:
        cluster_id: "{{u.cluster_id}}"
        instance_class: "{{S4.instance_class}}"
      requires_confirm: true
      idempotency_key: "aurora-add-reader-{{u.cluster_id}}-{{S4.branch}}"

  post_checks:
    - AuroraReplicaLag < {{u.replica_lag_threshold_ms}} for PT15M

  estimated_mttr: PT30M
  rollback_strategy: "Delete added reader if lag unchanged; revert instance class change (brief outage)."
```

## 23. RB-024 — Aurora Serverless v2 Capacity Ceiling

**Trigger**: PD-08, AURORA-SLV2-01
**Decision tier**: AUTO_HEAL
**Goal**: raise MaxCapacity when ACU pegged at configured max.

```yaml
runbook:
  id: RB-024
  name: "Aurora Serverless v2 Capacity Ceiling"
  trigger_rules: [PD-08, AURORA-SLV2-01]
  default_decision_tier: AUTO_HEAL
  preconditions:
    - Cluster has db.serverless instance(s)
    - ServerlessDatabaseCapacity ≥ 90% of current MaxCapacity for PT15M

  steps:
    - id: S1
      skill: aws-aurora-ops
      action: describe_serverless_scaling_config
      params: { cluster_id: "{{u.cluster_id}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_metric_statistics
      params:
        metric: ServerlessDatabaseCapacity
        dimensions: { DBInstanceIdentifier: "{{u.serverless_instance_id}}" }
        window: PT1H

    - id: S3
      skill: aws-aurora-ops
      action: modify_serverless_v2_max_capacity
      params:
        cluster_id: "{{u.cluster_id}}"
        new_max: "{{S3.computed_max}}"
        ceiling: "{{u.serverless_max_cap_ceiling}}"
      idempotency_key: "aurora-slv2-max-{{u.cluster_id}}-{{S3.computed_max}}"

  post_checks:
    - ServerlessDatabaseCapacity < 85% of new MaxCapacity for PT15M

  estimated_mttr: PT10M
  rollback_strategy: "Lower MaxCapacity after peak; no data loss."
```

## 24. RB-025 — Aurora Writer Failure (Manual Failover)

**Trigger**: FD-16, RDS-PROXY-AURORA-01
**Decision tier**: MANUAL
**Goal**: confirm writer health and execute controlled failover if Aurora did not auto-promote.

```yaml
runbook:
  id: RB-025
  name: "Aurora Writer Failure"
  trigger_rules: [FD-16, RDS-PROXY-AURORA-01]
  default_decision_tier: MANUAL
  preconditions:
    - Writer DBInstanceStatus != available OR cluster Status != available
    - Healthy reader exists with lower promotion tier

  steps:
    - id: S1
      skill: aws-aurora-ops
      action: describe_cluster_and_members
      params: { cluster_id: "{{u.cluster_id}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_cluster_endpoint_reachability
      params: { cluster_id: "{{u.cluster_id}}" }

    - id: S3 [optional]
      skill: aws-aurora-ops
      action: describe_db_proxy_targets
      params: { proxy_name: "{{u.proxy_name}}" }
      on_failure: skip

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_failover_or_wait
      # branches: wait_auto_failover | manual_failover | escalate_no_reader

    - id: S5
      skill: aws-aurora-ops
      action: failover_db_cluster
      params:
        cluster_id: "{{u.cluster_id}}"
        target_instance_id: "{{S4.target_reader_id}}"
      requires_confirm: true
      idempotency_key: "aurora-failover-{{u.cluster_id}}-{{S4.target_reader_id}}"

  post_checks:
    - describe-db-clusters Status=available
    - New writer IsClusterWriter=true

  estimated_mttr: PT15M
  rollback_strategy: "Failover is forward-only; re-balance readers after recovery."
```

## 25. RB-026 — Aurora Global Database Replication Lag

**Trigger**: PD-09, AURORA-GDB-01
**Decision tier**: MANUAL
**Goal**: assess cross-region lag and DR posture; no automatic promotion.

```yaml
runbook:
  id: RB-026
  name: "Aurora Global Database Replication Lag"
  trigger_rules: [PD-09, AURORA-GDB-01]
  default_decision_tier: MANUAL

  steps:
    - id: S1
      skill: aws-aurora-ops
      action: describe_global_cluster
      params: { global_cluster_id: "{{u.global_cluster_id}}" }

    - id: S2
      skill: aws-cloudwatch-ops
      action: get_metric_statistics
      params:
        metric: AuroraGlobalDBReplicationLag
        dimensions: { DBClusterIdentifier: "{{u.primary_cluster_id}}" }
        window: PT1H

    - id: S3
      skill: aws-aurora-ops
      action: assess_primary_write_pressure
      params: { cluster_id: "{{u.primary_cluster_id}}" }

    - id: S4
      skill: orchestrator
      action: emit_dr_recommendations
      # branches: throttle_writes | network_review | planned_dr_test | promote_secondary (MANUAL only)

  estimated_mttr: PT1H
  rollback_strategy: "Investigation only unless operator confirms secondary promotion."
```

## 26. RB-027 — Aurora Connection Storm (Proxy Path)

**Trigger**: PD-04, RDS-PROXY-AURORA-02, RDS-PROXY-CONN-01
**Decision tier**: AI_ASSIST
**Goal**: relieve connection pressure on Aurora cluster behind RDS Proxy.

```yaml
runbook:
  id: RB-027
  name: "Aurora Connection Storm (RDS Proxy)"
  trigger_rules: [PD-04, RDS-PROXY-AURORA-02, RDS-PROXY-CONN-01]
  default_decision_tier: AI_ASSIST
  preconditions:
    - Aurora cluster identified as proxy target (TRACKED_CLUSTER or describe-db-proxy-targets)

  steps:
    - id: S1
      skill: aws-aurora-ops
      action: describe_proxy_and_cluster_connections
      params: { cluster_id: "{{u.cluster_id}}", proxy_name: "{{u.proxy_name}}" }

    - id: S2
      skill: aws-aurora-ops
      action: get_cluster_max_connections
      params: { cluster_id: "{{u.cluster_id}}" }

    - id: S3
      skill: aws-ssm-ops
      action: sample_active_app_connections
      params: { targets: "{{u.app_instance_ids}}" }
      on_failure: skip

    - id: S4 [decision gate]
      skill: orchestrator
      action: decide_connection_remediation
      # branches: tune_proxy_pool | raise_max_connections | add_reader | app_pool_fix

    - id: S5
      skill: aws-aurora-ops
      action: modify_cluster_max_connections
      params: { cluster_id: "{{u.cluster_id}}", delta: 100 }
      requires_confirm: true

  estimated_mttr: PT30M
  rollback_strategy: "Revert parameter group max_connections if mis-tuned."
```

## 27. Runbook Library Summary

| ID | Name | Trigger Rules | Tier | MTTR | Primary Skills |
|----|------|--------------|------|------|----------------|
| RB-001 | Target Health Flapping | FD-01 | AUTO_HEAL | PT5M | elb, autoscaling |
| RB-002 | Target Unhealthy (Persistent) | FD-06 | AUTO_HEAL | PT8M | ec2, autoscaling, elb |
| RB-003 | Latency Spike (P99) | FD-02 | AI_ASSIST | PT30M | elb, ec2, rds, cloudwatch |
| RB-004 | Certificate 7-Day Expiry | PD-01 | AUTO_HEAL | PT20M | acm, route53, elb |
| RB-005 | WAF DDoS Pattern | WAF-rate-spike | AUTO_HEAL | PT5M | waf, elb, cloudwatch |
| RB-006 | Cost Spike Investigation | CO-09 | MANUAL | PT1H | s3, ec2, elb, rds, vpc |
| RB-007 | Production 5xx Surge | FD-03, FD-10 | AUTO_HEAL | PT15M | elb, ec2, rds, autoscaling, route53, sns |
| RB-008 | S3 Public Access Drift | SD-02 | AI_ASSIST | PT10M | s3 |
| RB-009 | Idle Load Balancer | CO-01, CO-02 | MANUAL | PT1H | elb, route53 |
| RB-010 | RDS Connection Saturation | PD-04 | AI_ASSIST | PT30M | rds, ssm |
| RB-011 | Lambda Throttling | FD-11 | AI_ASSIST | PT15M | lambda, cloudwatch, eventbridge |
| RB-012 | Lambda Iterator Age | FD-12 | AI_ASSIST | PT10M | lambda, cloudwatch |
| RB-013 | VPC Flow Log Anomaly | VPC-flow-anomaly | AI_ASSIST | PT30M | vpc, guardduty, sns |
| RB-014 | Security Group Open Ingress Drift | SD-03 | MANUAL | PT1H | ec2, vpc, cloudtrail, elb |
| RB-015 | EBS Volume Saturation | PD-02 | AI_ASSIST | PT20M | ec2, ssm, cloudwatch |
| RB-016 | KMS Key Compliance Failure | SD-05 | AI_ASSIST | PT10M | kms, cloudwatch |
| RB-017 | IAM Credential Leak Response | SD-04 | MANUAL | PT1H | iam, cloudtrail, sns |
| RB-SEC-01 | Compromised Instance Isolation | SD-01 | AI_ASSIST | PT15M | guardduty, cloudtrail, ec2, sns |
| RB-SEC-18 | Root Account Usage Alert | SD-07 | AI_ASSIST | PT5M | cloudtrail, cloudwatch, iam, sns |
| RB-018 | ElastiCache Connection Saturation | ElastiCache-sat | AI_ASSIST | PT20M | elasticache, cloudwatch |
| RB-019 | OpenSearch Cluster Yellow/Red | FD-14 | AI_ASSIST | PT45M | opensearch, cloudwatch |
| RB-020 | S3 Lifecycle Gap Remediation | CO-06 | MANUAL | PT15M | s3, cloudwatch |
| RB-021 | Multi-Region DNS Failover | FD-03 | AI_ASSIST | PT10M | route53, elb, cloudwatch, sns |
| RB-022 | Cost Spike Containment | CO-09 (high) | MANUAL | PT2H | s3, ec2, elb, rds, vpc, sns |
| RB-023 | Aurora Replica Lag | FD-15, AURORA-LAG-01 | AI_ASSIST | PT30M | aurora, cloudwatch |
| RB-024 | Aurora Serverless v2 Capacity | PD-08, AURORA-SLV2-01 | AUTO_HEAL | PT10M | aurora, cloudwatch |
| RB-025 | Aurora Writer Failure | FD-16, RDS-PROXY-AURORA-01 | MANUAL | PT15M | aurora, cloudwatch |
| RB-026 | Aurora Global DB Lag | PD-09, AURORA-GDB-01 | MANUAL | PT1H | aurora, cloudwatch |
| RB-027 | Aurora Connection Storm (Proxy) | PD-04, RDS-PROXY-AURORA-02 | AI_ASSIST | PT30M | aurora, ssm, cloudwatch |

**Coverage check**:

- All `FD-*` fault detection rules have at least one runbook (RB-001/002/003/007/011/012/019/021/023/025).
- All `PD-*` predictive rules have at least one runbook (RB-004/010/015/024/026/027).
- All `CO-*` cost rules have at least one runbook (RB-006/009/020/022).
- All `SD-*` security rules have at least one runbook (RB-008/014/016/017/SEC-01/SEC-18).
  RB-SEC-01 covers SD-01 (GuardDuty CRITICAL on EC2); RB-SEC-18 covers SD-07 (root account usage).
- All `CD-*` change rules use the orchestrator's standard change-impact flow.

## 12. Runbook Selection Logic

```
Given incident I with symptoms S and tier T:
  1. For each rule in detection-rules.md that fired for I:
       collect matching runbook IDs (runbook.trigger_rules).
  2. If multiple runbooks match:
       - Prefer the runbook with the highest specific trigger match.
       - If still tied, prefer runbooks with lower mttr.
  3. Validate preconditions.
  4. Run the runbook in the configured decision tier.
```

## 13. Runbook Library Maintenance

- Each runbook is owned by a team. Update owner field when reassigning.
- New runbooks are added via the same `references/runbook-recipes.md`
  file; the schema above must be followed exactly.
- Tested-in environments must include at least one non-prod before
  promoting to AUTO_HEAL tier.
- Quarterly review: archive runbooks not triggered in 6 months.