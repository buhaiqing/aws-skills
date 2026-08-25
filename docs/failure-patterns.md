# Failure Patterns — Reflexion Memory

> **Purpose**: Structured failure memory extracted from GCL traces and Self-Review records.
> Agents can optionally load this file during Pre-flight to prevent known errors.
>
> **Maintenance**: Updated automatically via Self-Review Round 3 (Lessons Learned).
> **Canonical store**: `docs/failure-patterns.jsonl` — edits should go there; this file is auto-generated.
> **Token budget**: ≤ 200 lines. When exceeded, prune low-frequency patterns (count < 3).


---

## 1. CLI Parameter Errors

> Extracted from GCL traces. High-frequency patterns first.


| skill | command | error | root_cause | fix | count | timestamp |
|-------|---------|-------|------------|-----|-------|-----------|
| aws-ec2-ops | aws ec2 terminate-instances | MissingParameter | Missing --instance-ids | --instance-ids i-xxx | 4 | 2026-07-25T00:00:00+00:00 |
| aws-ec2-ops | aws ec2 run-instances | InvalidParameterValue | SecurityGroupIds format | --security-group-ids sg-xxx | 3 | 2026-07-25T00:00:00+00:00 |
| aws-rds-ops | aws rds delete-db-instance | MissingParameter | Missing --db-instance-identifier | --db-instance-identifier mydb | 3 | 2026-07-25T00:00:00+00:00 |
| aws-s3-ops | aws s3 rb | NoSuchBucket | Bucket doesn't exist or wrong region | Verify bucket exists first | 2 | 2026-07-25T00:00:00+00:00 |
| aws-iam-ops | aws iam delete-user | NoSuchEntity | User doesn't exist | Check list-users first | 2 | 2026-07-25T00:00:00+00:00 |
| aws-lambda-ops | aws lambda delete-function | ResourceNotFoundException | Function name wrong | Verify with list-functions | 2 | 2026-07-25T00:00:00+00:00 |


## 1.5. Query / Search Silent Miss（烂查询 > 错工具）

> 来源：2026-07-19 CodeGraph A/B 对比实验 E3-Q5。最隐蔽的失败模式——**查询构造错（烂 glob/正则）比工具选错更危险，因为它静默错答、不报错**。


| 场景 | 错误模式 | 根因 | 修复 | 计数 |
|------|----------|------|------|------|
| 全局搜索"所有 composite/orchestrator 技能" | 全局搜索"所有 composite/orchestrator 技能" | glob/正则未对齐仓库实际目录布局 | 写查询前先用 `ls` / `git ls-files` 核对真实目录命名，不要凭模式推测 | — |
| 任何"按模式搜文件"的查询 | 任何"按模式搜文件"的查询 | 仓库存在例外目录（无后缀、`-meta` 等） | 优先用 `git ls-files 'aws-*/SKILL.md'` 或先枚举再过滤 | — |

> **判别口诀**：工具返回"无结果"时，先怀疑**自己的查询形状**（glob/正则/参数），再怀疑工具能力。烂查询会同时骗过 Grep 和 CodeGraph——与工具无关。\n

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


## 3. Cross-Skill Composition Failures

> Failure patterns in cross-skill orchestration chains.


| skill | command | error | root_cause | fix | count | timestamp |
|-------|---------|-------|------------|-----|-------|-----------|
| aws-elb-ops | aws elb register-targets | Target re-registration fails | Special chars in user data | Use base64 encoding | 3 | 2026-07-25T00:00:00+00:00 |
| aws-rds-ops | aws rds execute-sql | Timeout on large SQL | Large payload | Split SQL into chunks | 2 | 2026-07-25T00:00:00+00:00 |
| aws-aurora-ops | aws rds failover-db-cluster | Failover blocked | Pending modifications | Wait for modification to complete | 2 | 2026-07-25T00:00:00+00:00 |
| aws-cloudwatch-ops | aws cloudwatch get-metric-data | Alarm query empty | New alarm not yet propagated | Wait 60s after PutMetricAlarm | 2 | 2026-07-25T00:00:00+00:00 |


## 4. Runtime Execution Patterns

> Runtime failure patterns discovered during GCL execution.


| skill | command | error | root_cause | fix | count | timestamp |
|-------|---------|-------|------------|-----|-------|-----------|
| aws-ec2-ops | aws ec2 stop-instances | Instance stuck in Stopping | Dependent services not stopped | Check running processes before stop | 3 | 2026-07-25T00:00:00+00:00 |
| aws-rds-ops | aws rds create-db-instance | QuotaExceeded | Account-level instance limit | Query quota before creation | 3 | 2026-07-25T00:00:00+00:00 |
| aws-s3-ops | aws s3 rb | BucketNotEmpty | Versioned objects remain | Delete all versions first | 3 | 2026-07-25T00:00:00+00:00 |
| aws-elb-ops | aws elb deregister-targets | TargetsStillInService | Deregistration delay | Wait for DRAINING state | 3 | 2026-07-25T00:00:00+00:00 |


## 5. Token Efficiency Violations

> Common violations of Token Efficiency rules.


| TE Rule | Common Violation | Fix | Frequency |
|---------|------------------|-----|-----------|
| TE-6 | Same script in SKILL.md and references/ | Delete from references, keep SKILL.md copy | 4x |
| TE-4 | JSON paths scattered across file | Declare at file top in one block | 3x |
| TE-1 | Hardcoded region/zone lists in references/ | Use `aws ec2 describe-regions` query | 2x |
| TE-3 | Error table with > 3 columns | Merge columns, 1 error code per row | 2x |


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
# 2. Check if pattern already exists (dedup by error_signature)
# 3. If new: append to failure-patterns.jsonl with count=1
# 4. If existing: count is incremented automatically
# 5. Run: python3 scripts/_render_failure_patterns.py
# 6. If total lines > 200: prune patterns with count < 3
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
