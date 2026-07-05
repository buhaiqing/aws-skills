# boto3 SDK Usage — ECS

```python
import boto3
ecs = boto3.client('ecs', region_name='{{env.AWS_DEFAULT_REGION}}')

# Create cluster
resp = ecs.create_cluster(clusterName='{{user.cluster_name}}')
cluster_arn = resp['cluster']['clusterArn']

# List clusters
clusters = ecs.list_clusters()['clusterArns']

# Describe cluster
desc = ecs.describe_clusters(clusters=['{{user.cluster_name}}'])
cluster = desc['clusters'][0]  # .status, .runningCount

# Register task definition
resp = ecs.register_task_definition(
    family='{{user.task_family}}',
    networkMode='awsvpc',
    requiresCompatibilities=['FARGATE'],
    cpu='256',
    memory='512',
    containerDefinitions=[{
        'name': 'app',
        'image': '{{user.container_image}}',
        'portMappings': [{'containerPort': 80, 'protocol': 'tcp'}]
    }]
)
task_def_arn = resp['taskDefinition']['taskDefinitionArn']

# List task definitions
defs = ecs.list_task_definitions()['taskDefinitionArns']

# Deregister task definition
ecs.deregister_task_definition(taskDefinition='{{user.task_definition}}')

# Create service
resp = ecs.create_service(
    cluster='{{user.cluster_name}}',
    serviceName='{{user.service_name}}',
    taskDefinition='{{user.task_definition}}',
    desiredCount=1,
    launchType='FARGATE',
    networkConfiguration={
        'awsvpcConfiguration': {
            'subnets': ['{{user.subnets}}'],
            'securityGroups': ['{{user.security_groups}}']
        }
    }
)
service_arn = resp['service']['serviceArn']

# Update service (scale)
ecs.update_service(
    cluster='{{user.cluster_name}}',
    service='{{user.service_name}}',
    desiredCount=0  # scale to zero
)

# Describe services
desc = ecs.describe_services(cluster='{{user.cluster_name}}', services=['{{user.service_name}}'])
svc = desc['services'][0]  # .status, .desiredCount, .runningCount

# Wait for stable
waiter = ecs.get_waiter('services_stable')
waiter.wait(cluster='{{user.cluster_name}}', services=['{{user.service_name}}'])

# Delete service
ecs.delete_service(cluster='{{user.cluster_name}}', service='{{user.service_name}}', force=True)

# Stop task
ecs.stop_task(cluster='{{user.cluster_name}}', task='{{user.task_arn}}')

# List tasks
tasks = ecs.list_tasks(cluster='{{user.cluster_name}}')['taskArns']

# Describe tasks
desc = ecs.describe_tasks(cluster='{{user.cluster_name}}', tasks=['{{user.task_arn}}'])
task = desc['tasks'][0]  # .lastStatus, .containerInstanceArn

# Delete cluster
ecs.delete_cluster(cluster='{{user.cluster_name}}')
```