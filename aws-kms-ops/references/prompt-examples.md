# KMS Skill — Prompt Examples

_Latest update: 2026-05-29_

Concrete user prompts that activate the `aws-kms-ops` skill.

> **双向链接**: SKILL.md → [prompt-examples.md](prompt-examples.md)
> **双向链接**: prompt-examples.md → [SKILL.md](../SKILL.md)

---

## 场景 1：创建加密密钥

### Prompt
```
帮我创建一个 KMS 密钥用于加密应用数据，添加别名 app-data-key，启用自动轮转。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Pre-flight | `aws --version`, `aws sts get-caller-identity` |
| 2. Create key | `aws kms create-key --description "Application data encryption"` |
| 3. Create alias | `aws kms create-alias --alias-name alias/app-data-key --target-key-id {{o.KeyId}}` |
| 4. Enable rotation | `aws kms enable-key-rotation --key-id {{o.KeyId}}` |
| 5. Validate | `aws kms describe-key --key-id alias/app-data-key` |

---

## 场景 2：诊断密钥无法解密问题 (RCA)

### Prompt
```
我的应用无法解密数据，报错说密钥不可用。帮我诊断一下原因。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Identify key | Ask for key ID/alias from error message |
| 2. Check state | `aws kms describe-key --key-id {{u.key_id}} --query "KeyMetadata.{State:KeyState,Enabled:Enabled}"` |
| 3. RCA decision | If State=Disabled → [AUTO_HEAL] `enable-key` |
| 4. RCA decision | If State=PendingDeletion → [AUTO_HEAL] `cancel-key-deletion` |
| 5. RCA decision | If State=Enabled → Check IAM permissions |
| 6. Report | Output RCA with decision type and SLA |

**输出格式：**
```
[发现] Key alias/app-data-key
  状态: Disabled
  影响: 解密操作失败

[RCA] 根因分析
  ├─ 直接原因: 密钥被意外禁用
  ├─ 关联下层: N/A
  └─ 判定依据: describe-key → KeyState=Disabled

[决策] 决策类型: [AUTO_HEAL]
  ├─ 操作: aws kms enable-key --key-id alias/app-data-key
  ├─ 预期效果: 密钥恢复可用状态
  └─ 失败回退: 如权限不足 → 降级为 [MANUAL]

[SLA] P0 (15分钟) — 业务中断
```

---

## 场景 3：轮转合规扫描 + 自动修复

### Prompt
```
扫描我账户里所有没开自动轮转的密钥，帮我把生产环境的对称密钥都开启轮转。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. List keys | `aws kms list-keys` |
| 2. Filter | For each key: check `KeySpec=SYMMETRIC_DEFAULT` AND `KeyRotationEnabled=false` |
| 3. Classify | Production keys (by tag/env context) → [AUTO_HEAL] |
| 4. Execute | `aws kms enable-key-rotation --key-id {{key_id}}` for production keys |
| 5. Report | List fixed keys, skipped keys (non-prod), and asymmetric keys (not supported) |

---

## 场景 4：全账户加密健康巡检 (Cross-Skill)

### Prompt
```
帮我做一次全账户加密健康巡检，看看有没有不合规的密钥配置，给出修复建议。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. KMS audit | Scan all keys: rotation status, key states, grant audit |
| 2. S3 check | `aws-s3-ops`: Check SSE-KMS encryption on buckets |
| 3. RDS check | `aws-rds-ops`: Verify storage encryption enabled |
| 4. EC2 check | `aws-ec2-ops`: Check EBS volume encryption |
| 5. Lambda check | `aws-lambda-ops`: Verify env var encryption |
| 6. Report | Compliance score + [AUTO_HEAL]/[AI_ASSIST]/[MANUAL] actions |

**输出格式：**
```
╔══════════════════════════════════════════════════════════════════╗
║           加密健康巡检报告  2026-05-29 06:15 UTC               ║
╠══════════════════════════════════════════════════════════════════╣
║ KMS 密钥: 12 个                                                   ║
║   ✅ 合规: 8 个 (轮转已开启)                                      ║
║   ⚠️ 警告: 3 个 (对称密钥未开轮转) → [AUTO_HEAL] 建议开启        ║
║   ❌ 严重: 1 个 (密钥处于 PendingDeletion) → [AUTO_HEAL] 建议取消 ║
║                                                                  ║
║ S3 存储桶: 5 个                                                   ║
║   ✅ 加密: 4 个 (SSE-KMS)                                         ║
║   ❌ 未加密: 1 个 → [AI_ASSIST] 建议开启默认加密                  ║
║                                                                  ║
║ 决策分布                                                          ║
║   [AUTO_HEAL] 4 项  — 自动修复密钥状态、开启轮转                  ║
║   [AI_ASSIST] 2 项  — S3/RDS 加密配置建议                         ║
║   [MANUAL] 0 项                                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 场景 5：成本优化分析 (FinOps)

### Prompt
```
看看我的 KMS 使用情况，有没有可以优化成本的地方？
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Count keys | `aws kms list-keys \| jq '.Keys \| length'` |
| 2. Analyze usage | Check CloudTrail for `Decrypt` calls per key (90 days) |
| 3. Identify idle | Keys with zero usage → [AI_ASSIST] 建议删除 |
| 4. Calculate cost | `Keys(N) × $1.00 + Requests × $0.03/10K` |
| 5. Recommend | Delete unused keys, consolidate aliases, use data key caching |

---

## 场景 6：安全监控告警

### Prompt
```
帮我设置监控，如果有密钥被禁用或计划删除，立即通知我。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. CloudTrail rule | Create EventBridge rule for `DisableKey`, `ScheduleKeyDeletion` |
| 2. SNS topic | Configure `ops-alerts` SNS topic |
| 3. Alert config | Map events → SNS → Email/Slack |
| 4. Test | Simulate DisableKey → verify alert received |

---

## 场景 7：数据密钥加密 (Envelope Encryption)

### Prompt
```
帮我生成一个数据密钥来加密大文件，然后展示怎么用信封加密模式。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Generate DEK | `aws kms generate-data-key --key-id {{u.key_id}} --key-spec AES_256` |
| 2. Local encrypt | Use plaintext key to encrypt file locally (AES-GCM) |
| 3. Store | Save: [encrypted file] + [encrypted DEK from KMS] |
| 4. Secure cleanup | Zero out plaintext key from memory |
| 5. Decrypt flow | Show: decrypt DEK with KMS → decrypt file locally |

---

## 场景 8：跨账户密钥授权

### Prompt
```
我需要让另一个 AWS 账户能使用我的 KMS 密钥解密数据，怎么配置？
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Key policy | Add cross-account principal to key policy |
| 2. Grant | `aws kms create-grant --key-id {{u.key_id}} --grantee-principal arn:aws:iam::{{u.external_account}}:root --operations Decrypt` |
| 3. IAM policy | Guide external account to add IAM policy for KMS access |
| 4. Test | Verify cross-account decrypt works |
| 5. Document | Record grant ID for future revocation |

---

## 场景 9：密钥删除前的依赖检查

### Prompt
```
我想删除一个旧密钥，但不确定有没有服务还在用。帮我检查一下。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. CloudTrail audit | `aws cloudtrail lookup-events --lookup-attributes AttributeKey=ResourceName,AttributeValue={{u.key_id}}` (90 days) |
| 2. Service scan | Check S3 buckets, RDS instances, EBS volumes, Lambda functions |
| 3. Dependency report | List all services using the key |
| 4. Migration plan | [AI_ASSIST] 建议迁移步骤 |
| 5. Schedule deletion | After migration confirmed: `schedule-key-deletion` with 30-day window |

---

## 场景 10：批量密钥标签整理

### Prompt
```
帮我把所有没有 Environment 标签的密钥都加上标签，根据密钥别名判断环境。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. List untagged | `aws kms list-keys` + `aws kms list-resource-tags` to find keys without Environment tag |
| 2. Infer env | Parse alias (e.g., `alias/prod-*` → Production, `alias/dev-*` → Development) |
| 3. Tag keys | `aws kms tag-resource --key-id {{key_id}} --tags TagKey=Environment,TagValue={{inferred_env}}` |
| 4. Report | Summary of tagged keys by environment |

---

## 场景 11：清理孤立别名 (P3)

### Prompt
```
帮我检查一下有没有指向已删除密钥的孤立别名，清理掉。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. List aliases | `aws kms list-aliases` |
| 2. Check target | For each alias, verify `TargetKeyId` exists via `describe-key` |
| 3. Identify orphans | Aliases pointing to non-existent keys |
| 4. Delete | `aws kms delete-alias --alias-name {{orphaned_alias}}` |
| 5. Report | List of cleaned aliases |

**输出格式：**
```
[发现] 孤立别名 3 个
  ├─ alias/old-prod-key → TargetKeyId: 1234abcd (NOT_FOUND)
  ├─ alias/backup-key → TargetKeyId: 5678efgh (NOT_FOUND)
  └─ alias/test-key → TargetKeyId: 9012ijkl (NOT_FOUND)

[决策] 决策类型: [AI_ASSIST] P3
  ├─ 操作: 删除孤立别名
  ├─ 预期效果: 清理无效引用，减少混淆
  └─ 影响: 无业务影响（密钥已不存在）

[执行] 已删除 3 个孤立别名
```

---

## 场景 12：密钥文档化整理 (P3)

### Prompt
```
帮我把所有没有描述的密钥都加上描述，根据别名和标签推断用途。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Scan keys | `aws kms list-keys` + `describe-key` to find keys with empty description |
| 2. Infer purpose | Parse alias, tags, and usage patterns |
| 3. Update | Cannot update description directly; document in tags or external CMDB |
| 4. Report | List of keys needing documentation |

**决策类型**: [AI_ASSIST] P3

**输出格式：**
```
[发现] 无描述密钥 5 个
  ├─ key-1234 (alias/app-data-key)
  ├─ key-5678 (alias/backup-key)
  └─ key-9012 (无别名)

[决策] 决策类型: [AI_ASSIST] P3
  ├─ 操作: 根据别名/标签推断用途，添加到 CMDB 或标签
  ├─ 预期效果: 提升密钥可维护性
  └─ 影响: 无业务影响

[建议]
  ├─ key-1234: 推断用途 "应用数据加密" (基于 alias/app-data-key)
  ├─ key-5678: 推断用途 "备份加密" (基于 alias/backup-key)
  └─ key-9012: 需人工确认用途
```

---

## 场景 13：Grant 审计清理 (P3)

### Prompt
```
帮我检查一下哪些密钥的 grant 数量接近上限，清理不需要的 grant。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Scan grants | `aws kms list-keys` + `list-grants` for each key |
| 2. Identify high count | Keys with >400 grants (limit is 500) |
| 3. Audit | Review grant creation dates, grantees, and operations |
| 4. Clean retired | Retire grants older than 90 days with no usage |
| 5. Report | Summary of cleaned grants per key |

**决策类型**: [AI_ASSIST] P3

**输出格式：**
```
[发现] 高 Grant 数量密钥 2 个
  ├─ key-1234: 423 grants (limit: 500)
  └─ key-5678: 487 grants (limit: 500)

[决策] 决策类型: [AI_ASSIST] P3
  ├─ 操作: 审计并清理过期 grant
  ├─ 预期效果: 避免达到 500 上限导致服务中断
  └─ 影响: 无业务影响（仅清理已过期 grant）

[审计详情] key-1234
  ├─ 总计: 423 grants
  ├─ >90 天: 156 grants
  ├─ 建议: 清理 156 个过期 grant
  └─ 预计剩余: 267 grants (安全范围)

[执行] 已清理 156 个过期 grant
```

---

## 场景 14：季度密钥健康巡检 (P3)

### Prompt
```
帮我做一次季度密钥健康巡检，包括标签、描述、轮转状态、使用情况。
```

### Agent 执行流程
| 步骤 | 操作 |
|------|------|
| 1. Full scan | All keys: state, rotation, tags, description, usage |
| 2. Classify issues | P0 (critical), P2 (important), P3 (maintenance) |
| 3. Generate report | Compliance score + action items by priority |
| 4. Recommendations | [AUTO_HEAL] / [AI_ASSIST] / [MANUAL] actions |

**输出格式：**
```
╔══════════════════════════════════════════════════════════════════╗
║           季度密钥健康巡检报告  2026-Q2                          ║
╠══════════════════════════════════════════════════════════════════╣
║ 总览: 15 个密钥                                                   ║
║   ✅ 健康: 9 个                                                    ║
║   ⚠️ P2 问题: 3 个                                                 ║
║   📋 P3 待优化: 3 个                                               ║
║                                                                  ║
║ P2 问题 (需 48h 内处理):                                          ║
║   ├─ key-1234: 轮转未开启 → [AUTO_HEAL]                           ║
║   ├─ key-5678: 90天未使用 → [AI_ASSIST] 建议删除                  ║
║   └─ key-9012: 状态 Disabled → [AUTO_HEAL]                        ║
║                                                                  ║
║ P3 优化项 (计划性维护) [AI_ASSIST] P3:                           ║
║   ├─ 5 个密钥缺少 Environment 标签 → [AI_ASSIST] P3              ║
║   ├─ 2 个密钥无描述 → [AI_ASSIST] P3                              ║
║   └─ 1 个孤立别名待清理 → [AI_ASSIST] P3                          ║
║                                                                  ║
║ 合规评分: 78/100                                                  ║
║   ├─ 轮转合规: 80% (12/15)                                        ║
║   ├─ 标签完整: 67% (10/15)                                        ║
║   └─ 文档完整: 87% (13/15)                                        ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 触发词总结

| 触发词 | 场景 | 决策类型 |
|--------|------|----------|
| "创建 KMS 密钥" | 场景 1 | 标准操作 |
| "密钥无法解密" / "诊断密钥问题" | 场景 2 | RCA + [AUTO_HEAL]/[MANUAL] |
| "扫描轮转合规" / "开启自动轮转" | 场景 3 | [AUTO_HEAL] |
| "加密健康巡检" / "全账户加密审计" | 场景 4 | Cross-skill + 多层决策 |
| "KMS 成本优化" / "看看 KMS 花了多少钱" | 场景 5 | FinOps + [AI_ASSIST] |
| "监控密钥安全" / "密钥告警" | 场景 6 | 安全监控 |
| "数据密钥" / "信封加密" | 场景 7 | 技术实施 |
| "跨账户密钥" / "授权其他账户" | 场景 8 | 跨账户配置 |
| "删除密钥" / "密钥依赖检查" | 场景 9 | 安全删除流程 |
| "整理密钥标签" / "批量加标签" | 场景 10 | [AI_ASSIST] P3 |
| "孤立别名" / "清理别名" | 场景 11 | [AI_ASSIST] P3 |
| "密钥描述" / "文档化" | 场景 12 | [AI_ASSIST] P3 |
| "grant 审计" / "grant 清理" | 场景 13 | [AI_ASSIST] P3 |
| "季度巡检" / "健康巡检" | 场景 14 | 综合巡检 P0-P3 |

---

## 设计原则

1. **每个 Prompt 对应一个具体的 Operation** — Agent 可准确匹配 SKILL.md 执行流
2. **日常语言 → Agent 解析** — 用户无需知道 KMS 术语
3. **AIOps 场景覆盖** — RCA、Auto-Heal、Cross-Skill 编排
4. **FinOps 场景覆盖** — 成本分析、优化建议
