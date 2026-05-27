# Monitoring and Logging — EKS

## CloudWatch Container Insights

### 概述
CloudWatch Container Insights 为 EKS 集群提供自动化的监控、日志收集和指标可视化。

### 启用 Container Insights

#### 方法 1：使用 Quick Start（推荐）

```bash
# 使用 AWS CLI 快速启用
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

# 安装 Fluent Bit
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluent-bit-quickstart.yaml
```

#### 方法 2：使用 Helm

```bash
# 添加 Helm 仓库
helm repo add aws-amazon-cloudwatch https://aws.github.io/amazon-cloudwatch-container-insights/helm/charts
helm repo update

# 安装 Fluent Bit
helm install cloudwatch-agent \
  --namespace amazon-cloudwatch \
  --set region=us-east-1 \
  --set clusterName=my-cluster \
  --set fluentbit.enabled=true \
  --set logs.enabled=true \
  --set metrics.enabled=true \
  aws-amazon-cloudwatch/cloudwatch-agent
```

#### 方法 3：使用 AWS Distro for OpenTelemetry (ADOT)

```bash
# 安装 ADOT Collector
kubectl apply -f https://raw.githubusercontent.com/aws-observability/aws-otel-collector/main/deployment-template/eks/otel-collector-cloudwatch.yaml

# 配置 Collector
kubectl apply -f - <<EOF
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: adot-collector
  namespace: amazon-cloudwatch
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    exporters:
      cloudwatchlogs:
        log_group_name: /aws/containerinsights/my-cluster/application
        log_stream_name: "{ident}"
      awsxray:
      prometheusremotewrite:
        endpoint: https://aps-workspaces.us-east-1.amazonaws.com/workspaces/${WORKSPACE_ID}/api/v1/remote_write
        tls:
          insecure: true
    service:
      pipelines:
        traces:
          receivers: [otlp]
          exporters: [awsxray]
        metrics:
          receivers: [otlp]
          exporters: [prometheusremotewrite]
        logs:
          receivers: [otlp]
          exporters: [cloudwatchlogs]
EOF
```

### CloudWatch 指标

#### Container Insights 指标

| 指标名称 | 描述 | 维度 |
|---------|------|------|
| `pod_cpu_utilization` | Pod CPU 使用率 | PodName, Namespace |
| `pod_memory_utilization` | Pod 内存使用率 | PodName, Namespace |
| `pod_network_rx_bytes` | Pod 网络接收字节 | PodName, Namespace |
| `pod_network_tx_bytes` | Pod 网络发送字节 | PodName, Namespace |
| `node_cpu_utilization` | 节点 CPU 使用率 | NodeName |
| `node_memory_utilization` | 节点内存使用率 | NodeName |
| `node_number_of_running_pods` | 节点上运行的 Pod 数量 | NodeName |

#### 查询指标

```bash
# 使用 AWS CLI 查询指标
aws cloudwatch get-metric-statistics \
  --namespace ContainerInsights \
  --metric-name pod_cpu_utilization \
  --dimensions Name=PodName,Value=my-pod \
  --statistics Average \
  --period 300 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z

# 使用 CloudWatch Logs Insights 查询日志
aws logs start-query \
  --log-group-name /aws/containerinsights/my-cluster/application \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20'
```

### CloudWatch 仪表板

```bash
# 创建仪表板
aws cloudwatch put-dashboard \
  --dashboard-name my-eks-dashboard \
  --dashboard-body file://dashboard.json

# dashboard.json 示例
cat <<'EOF' > dashboard.json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          ["ContainerInsights", "pod_cpu_utilization", "PodName", "my-pod", "Namespace", "default"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Pod CPU Utilization"
      }
    },
    {
      "type": "metric",
      "x": 0,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          ["ContainerInsights", "pod_memory_utilization", "PodName", "my-pod", "Namespace", "default"]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Pod Memory Utilization"
      }
    }
  ]
}
EOF
```

## Prometheus + Grafana

### 安装 Prometheus Operator

```bash
# 添加 Helm 仓库
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 安装 Prometheus Operator
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set grafana.adminPassword=admin \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=gp2 \
  --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi

# 验证安装
kubectl get pods -n monitoring
kubectl get svc -n monitoring
```

### 访问 Grafana

```bash
# 端口转发
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# 访问 http://localhost:3000
# 用户名: admin
# 密码: admin（或使用设置的新密码）
```

### 创建 ServiceMonitor

```bash
# 为应用创建 ServiceMonitor
kubectl apply -f - <<EOF
apiVersion: v1
kind: Service
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  selector:
    app: my-app
  ports:
  - name: metrics
    port: 9090
    targetPort: 9090
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
EOF
```

### Grafana 仪表板

```bash
# 导入官方仪表板
# EKS 集群监控: https://grafana.com/grafana/dashboards/13230/
# Node Exporter: https://grafana.com/grafana/dashboards/1860/
# Kubernetes Cluster: https://grafana.com/grafana/dashboards/7249/

# 使用 kubectl 创建 ConfigMap 存储仪表板
kubectl create configmap grafana-dashboards \
  --from-file=dashboard1.json=./dashboard1.json \
  --from-file=dashboard2.json=./dashboard2.json \
  -n monitoring

# 或使用 Grafana UI 导入
# Dashboard → Import → 输入 ID
```

### Prometheus 告警规则

```bash
# 创建 PrometheusRule
kubectl apply -f - <<EOF
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-app-alerts
  namespace: monitoring
spec:
  groups:
  - name: my-app
    rules:
    - alert: HighCPUUsage
      expr: rate(container_cpu_usage_seconds_total{pod=~"my-app-.*"}[5m]) > 0.8
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High CPU usage detected"
        description: "Pod {{ $labels.pod }} has CPU usage above 80%"
    - alert: HighMemoryUsage
      expr: container_memory_usage_bytes{pod=~"my-app-.*"} / container_spec_memory_limit_bytes{pod=~"my-app-.*"} > 0.9
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High memory usage detected"
        description: "Pod {{ $labels.pod }} has memory usage above 90%"
EOF
```

## AWS X-Ray

### 安装 X-Ray Daemon

```bash
# 使用 Helm 安装
helm repo add aws-xray https://aws.github.io/aws-xray-daemon-helm-chart
helm repo update

helm install aws-xray-daemon aws-xray/aws-xray-daemon \
  --namespace aws-xray \
  --set region=us-east-1

# 或使用 kubectl
kubectl apply -f https://raw.githubusercontent.com/aws/aws-xray-daemon/master/kubernetes/xray-daemon.yaml
```

### 应用集成

```bash
# Python 应用示例
pip install aws-xray-sdk

# app.py
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

xray_recorder.configure(
    service='my-app',
    sampling=False,
    plugins=('ECSPlugin',)
)
patch_all()

# 你的应用代码
```

```bash
# Node.js 应用示例
npm install aws-xray-sdk-core

# app.js
const AWSXRay = require('aws-xray-sdk-core');
AWSXRay.captureHTTPsGlobal(require('http'));
AWSXRay.captureHTTPsGlobal(require('https'));
AWSXRay.capturePromise();

// 你的应用代码
```

### 查看 X-Ray 跟踪

```bash
# 使用 AWS CLI 查看跟踪摘要
aws xray get-trace-summary \
  --trace-id 1-5e1b6c72d2a4b3a1c7d2e5f6a7b8c9d0

# 获取跟踪图
aws xray get-trace-graph \
  --trace-ids 1-5e1b6c72d2a4b3a1c7d2e5f6a7b8c9d0

# 使用 CloudWatch 查询 X-Ray 指标
aws cloudwatch get-metric-statistics \
  --namespace AWS/X-Ray \
  --metric-name SegmentLatency \
  --dimensions Name=Service,Value=my-app \
  --statistics Average \
  --period 300
```

## Fluent Bit 日志收集

### 安装 Fluent Bit

```bash
# 使用 Helm
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

helm install fluent-bit fluent/fluent-bit \
  --namespace logging \
  --set config.inputs='[{"name":"tail","path":"/var/log/containers/*.log","parser":"docker","tag":"kube.*","refresh_interval":"5"}]' \
  --set config.outputs='[{"name":"cloudwatch","match":"*","region":"us-east-1","log_group_name":"/aws/eks/my-cluster","log_stream_prefix":"from-fluent-bit-","auto_create_group":"true"}]' \
  --set config.filters='[{"name":"kubernetes","match":"kube.*","kube_url":"https://kubernetes.default.svc:443","kube_ca_file":"/var/run/secrets/kubernetes.io/serviceaccount/ca.crt","kube_token_file":"/var/run/secrets/kubernetes.io/serviceaccount/token"}]'
```

### 配置 Fluent Bit

```bash
# 创建自定义配置
kubectl create configmap fluent-bit-config \
  --from-file=fluent-bit.conf=./fluent-bit.conf \
  --from-file=parsers.conf=./parsers.conf \
  -n logging

# fluent-bit.conf 示例
cat <<'EOF' > fluent-bit.conf
[SERVICE]
    Flush        1
    Log_Level    info
    Daemon       off
    Parsers_File parsers.conf

[INPUT]
    Name              tail
    Path              /var/log/containers/*.log
    Parser            docker
    Tag               kube.*
    Refresh_Interval  5
    Mem_Buf_Limit     5MB
    Skip_Long_Lines   On

[FILTER]
    Name                kubernetes
    Match               kube.*
    Kube_URL            https://kubernetes.default.svc:443
    Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
    Kube_Tag_Prefix     kube.var.log.containers.
    Merge_Log           On
    Keep_Log            Off
    K8S-Logging.Parser  On
    K8S-Logging.Exclude On

[OUTPUT]
    Name                cloudwatch
    Match               *
    region              us-east-1
    log_group_name      /aws/eks/my-cluster/application
    log_stream_prefix   from-fluent-bit-
    auto_create_group   true
EOF

# parsers.conf 示例
cat <<'EOF' > parsers.conf
[PARSER]
    Name        docker
    Format      json
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L
    Time_Keep   On

[PARSER]
    Name        syslog
    Format      regex
    Regex       ^\<(?<pri>[0-9]+)\>(?<time>[^ ]* {1,2}[^ ]* [^ ]*) (?<host>[^ ]*) (?<ident>[a-zA-Z0-9_\/\.\-]*)(?:\[(?<pid>[0-9]+)\])?(?:[^\:]*\:)? *(?<message>.*)$
    Time_Key    time
    Time_Format %b %d %H:%M:%S
EOF
```

### 查看日志

```bash
# 使用 AWS CLI
aws logs tail /aws/eks/my-cluster/application --follow

# 使用 CloudWatch Logs Insights
aws logs start-query \
  --log-group-name /aws/eks/my-cluster/application \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, kubernetes.pod_name, kubernetes.namespace_name, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 50'

# 使用 kubectl（短期日志）
kubectl logs -f <pod-name> -n <namespace>
kubectl logs -f <pod-name> -n <namespace> --all-containers
kubectl logs -f <pod-name> -n <namespace> --previous
```

## 告警和通知

### CloudWatch Alarms

```bash
# 创建告警
aws cloudwatch put-metric-alarm \
  --alarm-name HighCPUUsage \
  --alarm-description "Alert when CPU usage exceeds 80%" \
  --metric-name pod_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=PodName,Value=my-pod,Name=Namespace,Value=default \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:my-alert-topic

# 查看告警状态
aws cloudwatch describe-alarms --alarm-names HighCPUUsage
```

### SNS 通知

```bash
# 创建 SNS Topic
aws sns create-topic --name my-alert-topic

# 订阅邮箱
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:my-alert-topic \
  --protocol email \
  --notification-endpoint admin@example.com

# 订阅 Lambda 函数
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:my-alert-topic \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:123456789012:function:alert-handler
```

### Prometheus Alertmanager

```bash
# 配置 Alertmanager
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: alertmanager-config
  namespace: monitoring
data:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
    route:
      group_by: ['alertname']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 1h
      receiver: 'web.hook'
    receivers:
    - name: 'web.hook'
      webhook_configs:
      - url: 'http://alertmanager-webhook:5001/'
EOF
```

## 最佳实践

### 日志管理

1. **结构化日志**
   - 使用 JSON 格式
   - 包含时间戳、级别、消息
   - 添加元数据（request_id, user_id 等）

2. **日志级别**
   - 开发环境: DEBUG
   - 测试环境: INFO
   - 生产环境: WARN

3. **日志保留**
   - 应用日志: 7-30 天
   - 审计日志: 1 年
   - 安全日志: 7 年

### 监控指标

1. **关键指标**
   - CPU、内存使用率
   - 请求延迟、吞吐量
   - 错误率
   - Pod 状态、节点状态

2. **告警阈值**
   - CPU > 80%
   - 内存 > 90%
   - 错误率 > 1%
   - 响应时间 > 1s

3. **Dashboard**
   - 集群级别
   - 应用级别
   - 服务级别

### 性能优化

1. **采样率**
   - 开发环境: 100%
   - 测试环境: 50%
   - 生产环境: 10%

2. **数据保留**
   - 指标: 15 天
   - 日志: 30 天
   - 跟踪: 7 天

3. **成本控制**
   - 使用低成本存储
   - 定期清理旧数据
   - 优化查询

## 故障排查

### 日志不显示

```bash
# 检查 Fluent Bit 状态
kubectl logs -n logging deployment/fluent-bit

# 检查 Pod 日志
kubectl describe pod <pod-name>

# 检查 CloudWatch 日志组
aws logs describe-log-groups \
  --log-group-name-prefix /aws/eks/my-cluster
```

### 指标不显示

```bash
# 检查 Prometheus 状态
kubectl logs -n monitoring prometheus-kube-prometheus-prometheus-0

# 检查 ServiceMonitor
kubectl get servicemonitor -n monitoring

# 检查指标
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
# 访问 http://localhost:9090/targets
```

### 跟踪不显示

```bash
# 检查 X-Ray Daemon
kubectl logs -n aws-xray daemonset/aws-xray-daemon

# 检查应用配置
# 确保应用已正确集成 X-Ray SDK
```

## 参考文档

- [CloudWatch Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [AWS X-Ray](https://docs.aws.amazon.com/xray/)
- [Fluent Bit](https://docs.fluentbit.io/manual/)