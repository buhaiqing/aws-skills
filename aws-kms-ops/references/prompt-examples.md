# KMS Skill — Prompt Examples

_Latest update: 2026-07-31_

典型用户 Prompt → Agent 执行流。详细 CLI 见 [aws-cli-usage.md](aws-cli-usage.md)。

> **链接**：[SKILL.md](../SKILL.md) · [prompt-templates.md](prompt-templates.md)

## 场景 1：创建加密密钥
**Prompt**: `创建 KMS 密钥加密应用数据，别名 app-data-key，启用自动轮转。`
| 步骤 | 操作 |
| 1 | `sts get-caller-identity` → `create-key` → `create-alias` → `enable-key-rotation` → `describe-key` 验证 |

## 场景 2：诊断密钥无法解密 (RCA)
**Prompt**: `应用无法解密，报错密钥不可用，帮我诊断。`
| 步骤 | 操作 |
| 1 | `describe-key` 查 State/Enabled |
| 2 | Disabled → `[AUTO_HEAL] enable-key`；PendingDeletion → `cancel-key-deletion`；Enabled → 查 IAM |

## 场景 3：轮转合规扫描 + 自动修复
**Prompt**: `扫描未开自动轮转的对称密钥，生产环境全部开启轮转。`
| 步骤 | 操作 |
| 1 | `list-keys` → 过滤 `SYMMETRIC_DEFAULT` 且未轮转 → 生产标签 → `[AUTO_HEAL] enable-key-rotation` |

## 场景 4：全账户加密健康巡检 (Cross-Skill)
**Prompt**: `全账户加密健康巡检，不合规密钥给修复建议。`
| 步骤 | 操作 |
| 1 | KMS 轮转/状态/grant 审计 |
| 2 | `aws-s3-ops` SSE-KMS · `aws-rds-ops` 存储加密 · `aws-ec2-ops` EBS · `aws-lambda-ops` 环境变量加密 |
| 3 | 合规分 + `[AUTO_HEAL]`/`[AI_ASSIST]`/`[MANUAL]` 动作 |

## 场景 5：成本优化 (FinOps)
**Prompt**: `KMS 使用情况与成本优化建议。`
| 步骤 | 操作 |
| 1 | `list-keys` 计数 → CloudTrail `Decrypt` 用量(90d) → 闲置密钥 `[AI_ASSIST]` → 成本估算 |

## 场景 6：安全监控告警
**Prompt**: `密钥被禁用或计划删除时立即通知。`
| 步骤 | 操作 |
| 1 | EventBridge `DisableKey`/`ScheduleKeyDeletion` → SNS → 验证告警 |

## 场景 7：数据密钥 / 信封加密
**Prompt**: `生成数据密钥加密大文件，演示信封加密。`
| 步骤 | 操作 |
| 1 | `generate-data-key` → 本地 AES 加密 → 存密文+加密 DEK → 内存清零 Plaintext |

## 场景 8：跨账户密钥授权
**Prompt**: `另一 AWS 账户用我的 KMS 密钥解密，怎么配？`
| 步骤 | 操作 |
| 1 | key policy 加跨账户 principal → `create-grant` Decrypt → 外部 IAM 策略 → 验证 |

## 场景 9：密钥删除前依赖检查
**Prompt**: `删旧密钥前检查是否仍有服务在用。`
| 步骤 | 操作 |
| 1 | CloudTrail(90d) + S3/RDS/EBS/Lambda 扫描 → 依赖报告 → 迁移后 `schedule-key-deletion`（需 `PERMANENTLY DELETE <key-id>`） |

## 场景 10：批量密钥标签整理
**Prompt**: `无 Environment 标签的密钥按别名推断环境并打标。`
| 步骤 | 操作 |
| 1 | `list-keys` + `list-resource-tags` → 别名推断 → `tag-resource` |

## 场景 11：清理孤立别名 (P3)
**Prompt**: `检查并清理指向已删密钥的孤立别名。`
| 步骤 | 操作 |
| 1 | `list-aliases` → `describe-key` 验证 Target → `delete-alias` 孤立项 |

## 场景 12：密钥文档化 (P3)
**Prompt**: `无描述密钥按别名/标签推断用途并文档化。`
| 步骤 | 操作 |
| 1 | `list-keys` + `describe-key` 找空描述 → 推断用途 → 标签/CMDB 记录 |

## 场景 13：Grant 审计清理 (P3)
**Prompt**: `哪些密钥 grant 接近 500 上限，清理过期 grant。`
| 步骤 | 操作 |
| 1 | `list-grants` 计数 → >400 审计 → `retire-grant` 过期项（需 `confirm=RETIRE_GRANT <grant-id>`） |

## 场景 14：季度密钥健康巡检 (P3)
**Prompt**: `季度巡检：标签、描述、轮转、使用情况。`
| 步骤 | 操作 |
| 1 | 全量 scan → P0/P2/P3 分类 → 合规分 + 按优先级建议 |

## Quick Reference

| 触发词 | 场景 | 决策 |
|--------|------|------|
| 创建 KMS 密钥 | 1 | 标准 |
| 无法解密 / 诊断 | 2 | RCA + AUTO_HEAL |
| 轮转合规 / 开启轮转 | 3 | AUTO_HEAL |
| 加密健康巡检 | 4 | Cross-skill |
| KMS 成本 | 5 | FinOps |
| 密钥告警 | 6 | 监控 |
| 数据密钥 / 信封加密 | 7 | 技术 |
| 跨账户密钥 | 8 | 跨账户 |
| 删除密钥 / 依赖检查 | 9 | 安全删除 |
| 批量标签 | 10 | AI_ASSIST P3 |
| 孤立别名 | 11 | AI_ASSIST P3 |
| 密钥文档化 | 12 | AI_ASSIST P3 |
| grant 审计 | 13 | AI_ASSIST P3 |
| 季度巡检 | 14 | 综合 P0–P3 |
