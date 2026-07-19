# F2: Cost-Tracking 扩展执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement task-by-task.

**Goal**: 为 EC2 / RDS / Lambda / S3 各补充 `references/cost-tracking.md`，对齐 ELB 模板格式

**Architecture**: 每个服务新建一个 `cost-tracking.md`，遵循 ELB 模板的 4 个标准 Section

**Tech Stack**: Bash (CLI) + Markdown

---

## Task F2.1: aws-ec2-ops/references/cost-tracking.md

**Files**: Create `aws-ec2-ops/references/cost-tracking.md`

- [ ] **Step 1**: 参照 ELB 模板格式，创建 4 个 Section：
  - **Per-Resource Cost Query**: `aws ce get-cost-and-usage` by INSTANCE_TYPE + by TAG
  - **Idle Resource Detection**: EC2 running + CPU < 5% 持续 7 天（`describe-instances` + CloudWatch）
  - **Savings Recommendations**: RI Coverage %, SP 利用率, Spot 可节省估算
  - **Anomaly Detection**: 突发大量新实例检测（instance-hours 突增 > 50%）
- [ ] **Step 2**: 所有 CLI 使用 `--output json`，附 JSON path 解析示例
- [ ] **Step 3**: `grep -c "^" aws-ec2-ops/references/cost-tracking.md` 确认 ≤ 150 行
- [ ] **Step 4**: commit `git commit -m "docs(ec2): add cost-tracking reference (FinOps F2)"`

---

## Task F2.2: aws-rds-ops/references/cost-tracking.md

**Files**: Create `aws-rds-ops/references/cost-tracking.md`

- [ ] **Step 1**: 4 个 Section：
  - **Per-Resource Cost Query**: `aws ce get-cost-and-usage` by DATABASE_ENGINE + by TAG
  - **Idle Resource Detection**: RDS `DatabaseConnections=0` 持续 7 天（CloudWatch）
  - **Savings Recommendations**: RI Coverage by engine, Multi-AZ vs Single-AZ cost delta
  - **Anomaly Detection**: 存储量突增（Storage, GB-Mo）、I/O 费用异常
- [ ] **Step 2**: commit `git commit -m "docs(rds): add cost-tracking reference (FinOps F2)"`

---

## Task F2.3: aws-lambda-ops/references/cost-tracking.md

**Files**: Create `aws-lambda-ops/references/cost-tracking.md`

- [ ] **Step 1**: 4 个 Section：
  - **Per-Resource Cost Query**: `aws ce get-cost-and-usage` by FUNCTION_NAME TAG
  - **Idle Resource Detection**: `Invocations=0` 持续 30 天（CloudWatch）
  - **Savings Recommendations**: Provisioned Concurrency 利用率, Lambda@Edge 成本
  - **Anomaly Detection**: 请求量突增 10x 检测
- [ ] **Step 2**: commit `git commit -m "docs(lambda): add cost-tracking reference (FinOps F2)"`

---

## Task F2.4: aws-s3-ops/references/cost-tracking.md

**Files**: Create `aws-s3-ops/references/cost-tracking.md`

- [ ] **Step 1**: 4 个 Section：
  - **Per-Resource Cost Query**: `aws ce get-cost-and-usage` by LINKED_ACCOUNT + StorageLENS
  - **Idle Resource Detection**: `LastModified` > 1年 + 非 IA/Glacier 层
  - **Savings Recommendations**: Intelligent-Tiering 迁移建议, S3 Select vs 全量扫描成本对比
  - **Anomaly Detection**: 存储量突增 50% 检测（通过 Storage Lens）
- [ ] **Step 2**: commit `git commit -m "docs(s3): add cost-tracking reference (FinOps F2)"`

---

## Task F2.5: ELB 模板验证（不做修改）

- [ ] **Step 1**: 读取 `aws-elb-ops/references/cost-tracking.md`，确认模板格式正确（不做修改）
- [ ] **Step 2**: 4 个新文件的 Section 结构与 ELB 模板对齐

---

## Task F2.6: README 同步检查

- [ ] **Step 1**: 运行 README sync 检查：`ls aws-ec2-ops/references/cost-tracking.md aws-rds-ops/references/cost-tracking.md aws-lambda-ops/references/cost-tracking.md aws-s3-ops/references/cost-tracking.md 2>&1`
- [ ] **Step 2**: 无需修改 README（cost-tracking.md 不是必列文件）
