# Correlation Graph — AWS Resource Dependency Model

## 1. Purpose

The orchestrator needs a **machine-readable model** of how AWS resources
depend on each other so it can:

1. **Diagnose** cross-service incidents by traversing the graph from a
   reported symptom back to candidate root causes.
2. **Predict blast radius** of any proposed change (delete, modify, scale).
3. **Correlate** seemingly unrelated signals into a single incident
   (e.g., a security group change causes ELB health checks to fail).
4. **Plan** remediation workflows by ordering skill delegations along the
   dependency direction.

## 2. Graph Model

### 2.1 Vertices (nodes)

A vertex represents an AWS resource or logical group. Vertex schema:

```yaml
vertex:
  id: "<aws-resource-id>"           # e.g., i-0abc123, arn:...:my-alb
  type: <service>.<resource>        # e.g., ec2.instance, elbv2.load-balancer
  region: "<region>"
  account_id: "<account>"
  tags: { "<k>": "<v>", ... }
  aiops:
    in_scope: <bool>                # true if orchestrator should monitor
    tier: <production | staging | dev | sandbox>
    owner: <team or person>
```

### 2.2 Edges (relationships)

Edges express how resources depend on each other. They are directional
(`from → to` means "from depends on to").

```yaml
edge:
  from: "<vertex.id>"
  to: "<vertex.id>"
  kind: <one of: network-attachment, security-group-binding, dns-alias,
         iam-trust, kms-grant, route-target, subscription, parent-child,
         cross-stack-ref>
  weight: <0.0..1.0>                # criticality for blast radius
  observed_at: "<ISO-8601>"
  source: <how discovered: cloudtrail | describe | config | tag-walk>
```

### 2.3 Standard Edge Types

| Kind | Definition | Example |
|------|------------|---------|
| `network-attachment` | ENI attached to subnet/SG | `ec2.instance → ec2.network-interface` |
| `security-group-binding` | Resource uses SG | `ec2.instance → ec2.security-group` |
| `route-target` | Route table entry | `ec2.route-table → nat-gateway` |
| `listener-target` | LB listener forwards to TG | `elbv2.listener → elbv2.target-group` |
| `target-registered` | TG has registered instance | `elbv2.target-group → ec2.instance` |
| `dns-alias` | Route53 record points to AWS resource | `route53.record → elbv2.load-balancer` |
| `iam-trust` | Role assumed by | `iam.role → ec2.instance` |
| `kms-grant` | Resource uses CMK | `s3.bucket → kms.key` |
| `parent-child` | Owned by | `rds.cluster → rds.db-instance` |
| `subscription` | SNS topic subscribed by | `sns.topic → sqs.queue` |
| `event-source` | Lambda reads from | `lambda.function → sqs.queue` |
| `autoscaling-attached` | ASG manages | `autoscaling.group → ec2.instance` |
| `eks-owned` | EKS cluster owns node | `eks.cluster → ec2.instance` |

## 3. Resource Type Catalog

The graph builder walks these resource types. Each row lists the
`describe-*` command used and the edges it produces.

| Resource | Discover command | Outgoing edges |
|----------|-----------------|----------------|
| EC2 Instance | `describe-instances` | subnet, SG, ENI, IAM role, ASG (if any), EKS node (if any) |
| ALB / NLB | `describe-load-balancers` | listener → TG → instance |
| Target Group | `describe-target-groups` | listener, registered instances |
| Listener | `describe-listeners` | ALB, certificate (ACM) |
| Security Group | `describe-security-groups` | inbound/outbound rules (often used to discover implicit deps) |
| Subnet | `describe-subnets` | VPC, route table, NACL |
| VPC | `describe-vpcs` | — |
| Route Table | `describe-route-tables` | subnet, IGW, NAT GW, peering |
| NAT Gateway | `describe-nat-gateways` | subnet, EIP |
| Internet Gateway | `describe-internet-gateways` | VPC |
| RDS DB Instance | `describe-db-instances` | subnet group, SG, parameter group, KMS key |
| RDS Cluster | `describe-db-clusters` | DB instances |
| ElastiCache | `describe-replication-groups` | subnet group, SG |
| OpenSearch | `describe-domain` | VPC endpoint, SG, KMS |
| S3 Bucket | `list-buckets` + `get-bucket-*` | policy, lifecycle, KMS, CloudTrail destination |
| Lambda Function | `list-functions` | VPC config (subnet/SG), IAM role, event sources |
| EKS Cluster | `describe-cluster` | node group, Fargate profile, subnets |
| Auto Scaling Group | `describe-auto-scaling-groups` | launch template, subnets, instances |
| SNS Topic | `list-topics` + `list-subscriptions` | subscriptions, access policy |
| SQS Queue | `list-queues` + `get-queue-attributes` | policy, DLQ, Lambda triggers |
| EventBridge Rule | `list-rules` + `list-targets-by-rule` | targets |
| ACM Certificate | `list-certificates` | in-use-by (via reverse lookup on listeners) |
| KMS Key | `list-keys` + `get-key-policy` | grants, aliases |
| IAM Role | `list-roles` + `list-attached-role-policies` | trust policy, attached policies |
| GuardDuty Detector | `list-detectors` + `list-findings` | findings (security posture) |
| Security Hub | `describe-hub` | aggregated findings |
| Route53 Hosted Zone | `list-hosted-zones` + `list-resource-record-sets` | records, health checks |
| Cost Explorer | (read-only) | none — provides cost data, not edges |

## 4. Graph Build Algorithm

### 4.1 Build

```
Phase 1 — Seed
  Start from orchestrator scope (region / account / tags).
  For each (service, describe-*):
    build vertices from response.
    for each resource, run resource-specific discovery to find edges.
Phase 2 — Reverse lookup
  For each vertex, find resources that reference it
  (e.g., find listeners using cert arn, find SGs attached to instances).
Phase 3 — Validate
  Verify every edge points to a vertex that exists in the graph.
  Drop dangling edges (with a warning log).
Phase 4 — Tag-walk
  Propagate the orchestrator scope (e.g., {Env: prod}) by walking tags:
    if vertex A has {Env: prod} and vertex B references A,
    inherit B into prod scope (unless B has {Env: dev}).
Phase 5 — Cache
  Serialize to internal format (JSON / SQLite) keyed by
  (account_id, region, scope_tag_set, generated_at).
  TTL: 1h for steady state; rebuild on demand for change-impact queries.
```

### 4.2 Incremental update

On each delegated skill response with `aiops_context.facts[*]`, update
the relevant vertex state. If a fact changes an edge (e.g., new SG
attached), re-run Phase 2 reverse lookup for that vertex.

## 5. Traversal Algorithms

### 5.1 Forward traversal (blast radius)

```
blast_radius(resource_id, max_depth=5):
  visited = set()
  queue = [resource_id]
  results = []
  while queue and depth <= max_depth:
    current, depth = queue.pop()
    for edge in outgoing_edges(current):
      results.append((edge.to, edge.kind, edge.weight))
      if edge.to not in visited:
        visited.add(edge.to)
        queue.append(edge.to)
  return results
```

Used for: change-impact analysis, "what breaks if I delete X".

### 5.2 Backward traversal (root cause)

```
root_cause_paths(symptom_resource_id, max_paths=3):
  candidates = []
  for edge in incoming_edges(symptom_resource_id):
    upstream = traverse_backward(edge.from, max_depth=3)
    candidates.append((edge, upstream))
  rank candidates by:
    - recent CloudTrail change events on any vertex in upstream
    - anomaly scores from CloudWatch metrics on those vertices
    - config-rule compliance status
  return top max_paths candidates
```

Used for: RCA, incident diagnosis.

### 5.3 Subgraph extraction (incident scope)

For a detected incident:

1. Identify the symptom vertex (e.g., the ALB with 5xx).
2. Extract 1-hop neighborhood (upstream + downstream).
3. Add any vertex with an active anomaly in the last `time_window`.
4. Subgraph = incident boundary.

Used for: building the per-incident scope for RCA report.

## 6. Example: ALB 5xx Incident Subgraph

```
                        ┌──────────────┐
                        │ route53:api  │
                        └──────┬───────┘
                               │ dns-alias
                               ▼
                        ┌──────────────┐
                        │ elbv2:api    │
                        └──────┬───────┘
                               │ listener
                               ▼
                  ┌────────────────────────┐
                  │ elbv2:tg-api           │
                  └──┬──────────┬──────────┘
                     │          │
        target-registered     target-registered
                     ▼          ▼
           ┌──────────────┐ ┌──────────────┐
           │ ec2:i-aaaa   │ │ ec2:i-bbbb   │  ← Anomaly: FD-06
           └──────┬───────┘ └──────┬───────┘     (status check fail)
                  │                │
                  │   autoscaling-attached
                  ▼                ▼
           ┌────────────────────────────┐
           │ asg:api-prod               │
           └────────────────────────────┘
                  │
                  │ security-group-binding
                  ▼
           ┌────────────────────────────┐
           │ ec2:sg-api                 │
           └────────────────────────────┘
                  │
                  │ network-attachment
                  ▼
           ┌────────────────────────────┐
           │ ec2:subnet-api-private     │
           └──────┬─────────────────────┘
                  │ route-target
                  ▼
           ┌────────────────────────────┐
           │ ec2:nat-gw                 │  ← Candidate RC:
           └────────────────────────────┘    packet drop (FD-13)
```

The orchestrator would walk this graph from the symptom (ALB 5xx) backward
through candidate roots: instance status (FD-06) → ASG capacity → SG
configuration → NAT GW health. Each candidate gets a confidence score
based on whether a related anomaly is also firing.

## 7. Performance Considerations

- For accounts with > 10k resources: full graph build can take 1-3 min.
  Use paginated describe calls and incremental cache where possible.
- Subgraph extraction for a typical incident should be < 5s.
- Change-impact queries should be < 10s; pre-build hot subgraphs
  (production-tagged) every 15 min via EventBridge schedule.

## 8. Edge Cases & Limitations

1. **Cross-region edges**: not modeled in this version. Cross-region
   dependency (e.g., global accelerator) is documented in vertex tags
   but not represented as edges.
2. **Cross-account edges**: identified but require cross-account role
   assumption; flagged with `cross_account: true` on the edge.
3. **Implicit dependencies**: e.g., implicit SG references when the
   default SG is used. Detected via `describe-security-groups` walk,
   but may be incomplete.
4. **Dynamically-discovered resources**: e.g., Lambda ephemeral ENIs.
   Captured via CloudTrail / Config events, not by direct describe.
5. **Third-party SaaS dependencies**: out of scope — represent as opaque
   external endpoints.

## 9. Example Scope Graph (YAML)

See `assets/example-scope-graph.yaml` for a minimal end-to-end example
covering: VPC → Subnet → ALB → TG → ASG → EC2 → RDS path.