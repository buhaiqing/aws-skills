# AWS CLI Usage — ECS

> **Pre-condition**: `aws sts get-caller-identity` before any command.

## Common JSON Paths
- Cluster: `.clusters[0].{clusterArn,status,runningCount,pendingCount}`
- Service: `.services[0].{serviceArn,status,desiredCount,runningCount}`
- Task: `.tasks[0].{taskArn,lastStatus,desiredStatus,containerInstanceArn}`
- Task Definition: `.taskDefinition.{taskDefinitionArn,revision,status}`

## Commands

```bash
# List/describe
aws ecs list-clusters --output json
aws ecs describe-clusters --clusters "{{user.cluster_name}}" --output json
aws ecs list-services --cluster "{{user.cluster_name}}" --output json
aws ecs describe-services --cluster "{{user.cluster_name}}" --services "{{user.service_name}}" --output json
aws ecs list-task-definitions --output json
aws ecs describe-task-definition --task-definition "{{user.task_definition}}" --output json
aws ecs list-tasks --cluster "{{user.cluster_name}}" --output json
aws ecs describe-tasks --cluster "{{user.cluster_name}}" --tasks "{{user.task_arn}}" --output json

# Cluster
aws ecs create-cluster --cluster-name "{{user.cluster_name}}" --tags Key=ManagedBy,Value=aiops --output json
aws ecs delete-cluster --cluster "{{user.cluster_name}}" --output json

# Service
aws ecs create-service --cluster "{{user.cluster_name}}" --service-name "{{user.service_name}}" --task-definition "{{user.task_definition}}" --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[{{user.subnets}}],securityGroups=[{{user.security_groups}}]}" --output json
aws ecs update-service --cluster "{{user.cluster_name}}" --service "{{user.service_name}}" --desired-count {{user.desired_count}} --output json
aws ecs delete-service --cluster "{{user.cluster_name}}" --service "{{user.service_name}}" --force --output json
aws ecs wait services-stable --cluster "{{user.cluster_name}}" --services "{{user.service_name}}"

# Task Definition
aws ecs register-task-definition --family "{{user.task_family}}" --container-definitions '{{user.container_defs}}' --output json
aws ecs deregister-task-definition --task-definition "{{user.task_definition}}" --output json

# Task
aws ecs run-task --cluster "{{user.cluster_name}}" --task-definition "{{user.task_definition}}" --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[{{user.subnets}}]}" --output json
aws ecs stop-task --cluster "{{user.cluster_name}}" --task "{{user.task_arn}}" --reason "Manual stop" --output json
```