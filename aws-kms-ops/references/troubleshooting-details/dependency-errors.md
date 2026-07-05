# KMS Dependency Errors — Detailed Recovery

## DependencyTimeoutException

CloudHSM or other dependency timeout.

```bash
# Retry with exponential backoff
# Check CloudHSM cluster status
aws cloudhsmv2 describe-clusters
aws cloudhsmv2 describe-clusters --query "Clusters[?ClusterId=='{{cluster_id}}'].State"
```

## CloudHSMClusterNotActiveException

CloudHSM cluster initializing or failed.

```bash
# Check cluster status
aws cloudhsmv2 describe-clusters --cluster-id {{cluster_id}}

# Wait for ACTIVE state or initialize
aws cloudhsmv2 initialize-cluster --cluster-id {{cluster_id}}
```

## Key Deletion Dependencies

Key has dependent resources (S3, EBS, RDS, Secrets Manager, Lambda).

```bash
# Check key usage in CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue={{key_id}} \
  --start-time "2024-01-01T00:00:00Z"

# Check service integrations
aws kms get-key-policy --key-id {{key_id}} --query "Policy" --output text | jq '.Statement[] | select(.Principal.Service)'

# Resolution: update dependents to use different key, then schedule deletion
aws kms schedule-key-deletion --key-id {{key_id}} --pending-window-in-days 30
```
