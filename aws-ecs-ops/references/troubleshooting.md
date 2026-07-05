# ECS Troubleshooting

## Error Table

| Error | Resolution |
|-------|-----------|
| `ClusterNotFoundException` | Verify cluster name/ARN; list existing clusters |
| `ServiceNotFoundException` | Verify service name; list services in cluster |
| `TaskDefinitionNotFoundException` | Register task definition first |
| `InvalidParameterException` | Check required params (CPU, memory valid combos) |
| `PlatformTaskDefinitionIncompatibilityError` | Fargate task def must have `awsvpc` network and compatible CPU/memory |
| `AccessDeniedException` | Check IAM execution role permissions |
| `CannotCreateContainerError` | Check container image exists in ECR/public registry |
| `REsourceInitializationError` | Check VPC/subnet has route to pull image (NAT gateway for private) |
| `ThrottlingException` | Backoff and retry; reduce API call rate |
| `ServiceNotActiveException` | Service must be ACTIVE to update/delete |
| `UnableToAssumeRoleError` | Verify task execution role ARN is valid |

## Polling Limits
- Service stable: wait up to 10 min
- Task running: wait up to 5 min
- Cluster drain: wait up to 30 min for EC2 instances

## Health Check
```bash
aws ecs describe-services --cluster "{{user.cluster_name}}" --services "{{user.service_name}}" \
  --query "services[0].{status:status,desired:desiredCount,running:runningCount,pending:pendingCount,deployments:deployments[].{status:status,running:runningCount}}"
```

## Common Issues

### Task stuck in PENDING
- Fargate: subnet missing NAT gateway or VPC endpoints (ECR, CloudWatch, S3)
- EC2: insufficient cluster resources (CPU/memory/ports)

### Service deployment failing
- Check deployment circuit breaker: `deployments[0].rolloutState == "FAILED"`
- Verify task definition revision exists
- Check load balancer target group health checks