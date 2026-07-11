# Changelog — aws-aiops-cruise

| Version | Date | Change |
|---------|------|--------|
| 2.2.0 | 2026-07-11 | EKS node/Pod inference: `EKS-NODE-01` (node NotReady) + `EKS-OOM-01` (pod OOM-kill) via CloudWatch Container Insights; `audit_eks_nodes` collector; `EKS_NODE` signal layer; Prometheus/kube-state-metrics alt telemetry docs |
| 2.1.0 | 2026-07-04 | GCL compliance: shared skeleton prompt-templates migration; frontmatter GCL/cross_skill_deps/delegate metadata; TE-1 threshold disclaimer; TE-6 execution flow consolidation; TE checklist section; `{{user.safety_confirm}}` added |
|---------|------|--------|
| 1.9.0 | 2026-06-13 | P1: SKILL slim; boto3 CLI fallback; aiops_context `facts_info`; markdown topology link; Perceive `_cruise_env.sh`; TopoScan auto overlay; Mermaid health only WARNING+ |
| 2.0.0 | 2026-06-13 | P2: `_aws_native` split into `collectors/`; health overlay + cf-origins unit tests |
| 1.8.1 | 2026-06-13 | P0: RDS-PROXY-01 pool %; execution-guide sync; orchestrator delegate-routing cruise/topo |
| 1.8.0 | 2026-06-13 | API GW v2; CF Origin Group failover; OIDC trust generator |
| 1.7.0 | 2026-06-13 | CF→APIGW/Lambda URL edges; cache behavior labels; GitLab OIDC CI |
| 1.6.0 | 2026-06-13 | CF→ALB/S3 Mermaid; S3-METRICS-01; GitLab CI |
| 1.5.0 | 2026-06-13 | S3 4xx/5xx; Mermaid health classDef; GitHub `--render-topology` |
| 1.4.0 | 2026-06-13 | CF S3 OAC; RDS Proxy→Aurora; cruise-topo-render |
| 1.3.0 | 2026-06-13 | CloudFront; RDS Proxy; X-Ray; EventBridge alarm IaC |
| 1.2.0 | 2026-06-13 | AWS-native collectors; multi-region; runbooks 05–09 |
| 1.1.0 | 2026-06-13 | Parallel metrics; WoW; aiops_context |
| 1.0.0 | 2026-06-13 | Initial AWS port; 7 Perceive Agents; runbooks 01–09 |
