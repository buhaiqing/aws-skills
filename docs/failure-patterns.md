# Failure Patterns — Reflexion Memory

> **Purpose**: Structured failure memory extracted from GCL traces and Self-Review records.
> Agents can optionally load this file during Pre-flight to prevent known errors.
>
> **Maintenance**: Updated automatically via Self-Review Round 3 (Lessons Learned).
> **Token budget**: ≤ 200 lines. When exceeded, prune low-frequency patterns (count < 3).

---

## 1. CLI Parameter Errors

> Extracted from GCL traces. High-frequency patterns first.

| Skill | Command | Error Pattern | Root Cause | Fix | Count |
|-------|---------|---------------|------------|-----|-------|
| `ec2-ops` | `terminate-instances` | `MissingParameter` | Missing `--instance-ids` | `--instance-ids i-xxx` | 4 |
| `ec2-ops` | `run-instances` | `InvalidParameterValue` | SecurityGroupIds format | `--security-group-ids sg-xxx` | 3 |
| `rds-ops` | `delete-db-instance` | `MissingParameter` | Missing `--db-instance-identifier` | `--db-instance-identifier mydb` | 3 |
| `s3-ops` | `delete-bucket` | `NoSuchBucket` | Bucket doesn't exist or wrong region | Verify bucket exists first | 2 |
| `iam-ops` | `delete-user` | `NoSuchEntity` | User doesn't exist | Check `list-users` first | 2 |
| `lambda-ops` | `delete-function` | `ResourceNotFoundException` | Function name wrong | Verify with `list-functions` | 2 |

---

## 1.5. Query / Search Silent Miss（烂查询 > 错工具）

> 来源：2026-07-19 CodeGraph A/B 对比实验 E3-Q5。最隐蔽的失败模式——**查询构造错（烂 glob/正则）比工具选错更危险，因为它静默错答、不报错**。

| 场景 | 错误模式 | 根因 | 修复 | 计数 |
|------|----------|------|------|------|
| 全局搜索"所有 composite/orchestrator 技能" | glob `aws-*-ops` 漏匹配 `aws-aiops-orchestrator`（该目录**无 `-ops` 后缀） | glob/正则未对齐仓库实际目录布局 | 写查询前先用 `ls` / `git ls-files` 核对真实目录命名，不要凭模式推测 | 1（实测真值=2，Grep 返回 0） |
| 任何"按模式搜文件"的查询 | 用 `aws-*-ops` 这类带后缀的 glob 当全集 | 仓库存在例外目录（无后缀、`-meta` 等） | 优先用 `git ls-files 'aws-*/SKILL.md'` 或先枚举再过滤 | — |

> **判别口诀**：工具返回"无结果"时，先怀疑**自己的查询形状**（glob/正则/参数），再怀疑工具能力。烂查询会同时骗过 Grep 和 CodeGraph——与工具无关。

---

## 2. Skill Generation Issues

> Common structural errors from the skill generator.

| Issue Type | Frequency | Fix Pattern | First Seen |
|------------|-----------|-------------|------------|
| Missing YAML frontmatter | 10x | Always start with `---` block containing name, description, license, compatibility, metadata | 2026-06 |
| TE-6 violation (cross-file duplication) | 7x | Delete duplicate from references/, keep SKILL.md as authoritative | 2026-06 |
| Missing SHOULD/SHOULD NOT section | 5x | Add trigger conditions chapter with delegation rules | 2026-06 |
| Broken relative links | 4x | Use `../` prefix for advanced/ → references/ links | 2026-06 |
| Missing Well-Architected table | 3x | Add five-pillar table (Security, Stability, Cost, Efficiency, Performance) | 2026-06 |
| TE-1 violation (hardcoded versions) | 2x | Replace with `aws` query command for dynamic version fetching | 2026-06 |

---

## 3. Cross-Skill Composition Failures

> Failure patterns in cross-skill orchestration chains.

| Source Skill | Target Skill | Failure Pattern | Resolution | Count |
|--------------|--------------|-----------------|------------|-------|
| `elb-ops` | `ec2-ops` | Target re-registration fails with special chars in user data | Use base64 encoding | 3 |
| `rds-ops` | `ec2-ops` | Timeout on large SQL file via SSM | Split SQL into chunks < 10KB | 2 |
| `aurora-ops` | `rds-ops` | Failover blocked by pending changes | Wait for modification to complete first | 2 |
| `cloudwatch-ops` | `ec2-ops` | Alarm query returns empty for new alarm | Wait 60s after PutMetricAlarm before querying | 2 |

---

## 4. Runtime Execution Patterns

> Runtime failure patterns discovered during GCL execution.

| Skill | Operation | Failure Pattern | Root Cause | Prevention |
|-------|-----------|-----------------|------------|------------|
| `ec2-ops` | `stop-instances` | Instance stuck in Stopping state | Dependent services not stopped | Check running processes before stop |
| `rds-ops` | `create-db-instance` | Quota exceeded error | Account-level instance limit | Query quota before creation |
| `s3-ops` | `delete-bucket` | Bucket not empty (versioning enabled) | Versioned objects remain | Delete all versions first |
| `elb-ops` | `deregister-targets` | Targets still in service | Deregistration delay | Wait for DRAINING state |

---

## 5. Token Efficiency Violations

> Common violations of Token Efficiency rules.

| TE Rule | Common Violation | Fix | Frequency |
|---------|------------------|-----|-----------|
| TE-1 | Hardcoded region/zone lists in references/ | Use `aws ec2 describe-regions` query | 2x |
| TE-3 | Error table with > 3 columns | Merge columns, 1 error code per row | 2x |
| TE-4 | JSON paths scattered across file | Declare at file top in one block | 3x |
| TE-6 | Same script in SKILL.md and references/ | Delete from references, keep SKILL.md copy | 4x |

---

## Usage Guidelines

### For Agents (Pre-flight)

```
# Optional: Load failure patterns before executing a skill
# 1. Read this file (lazy-load, ~150 lines)
# 2. Filter patterns by current skill name
# 3. Inject relevant patterns into Generator context as prevention hints
```

### For Self-Review (Round 3: Lessons Learned)

```
# After completing R1 + R2:
# 1. Extract new failure patterns from this session
# 2. Check if pattern already exists (dedup by skill + command + error)
# 3. If new: append to appropriate section with count=1
# 4. If existing: increment count
# 5. If total lines > 200: prune patterns with count < 3
```

### For GCL Traces

```
# When a GCL iteration fails, record the failure pattern:
{
  "failure_pattern": {
    "category": "cli_parameter" | "skill_generation" | "cross_skill" | "runtime" | "token_efficiency",
    "skill": "aws-xxx-ops",
    "command": "aws xxx ...",
    "error": "MissingParameter: ...",
    "fix": "Added correct parameter format",
    "reusable": true | false
  }
}
```
