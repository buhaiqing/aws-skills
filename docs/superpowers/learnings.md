# Cross-Session Learnings

> Append-only log of lessons learned during implementation work. Each entry
> is keyed by date + topic and pinned to a specific commit / spec.

## 2026-07-28 — TE Gate C6 Debt Pilot

**Files**: `docs/superpowers/specs/2026-07-28-te-gate-c6-debt-design.md`,
`docs/superpowers/plans/2026-07-28-te-gate-c6-debt-pilot.md`,
`scripts/tests/test_te_gate.py` (new), `scripts/te_gate.py` (regex fix + G1 off-by-one),
`aws-cloudwatch-ops/SKILL.md` (135→118), `aws-ram-ops/SKILL.md` (666→119),
`aws-ram-ops/references/operations.md` (new, 425 lines).

### Lesson 1 — G3 body-dupe check must skip the entire header block, not just the header line

**Symptom**: `te_gate.py` was reporting `JSON path re-declared in body (TE-4)`
on the **header's own line** when the header used multi-path content like
`.A | .B → .C`. The header-block splitter stopped at the next `##` heading
but the body-dupe check only skipped up to the header_idx, so a token
extracted from the LHS of the header was matching the RHS of the same line.

**Root cause**: The block boundary was used to extract declarations but
not to bound the body-dupe scan. Sub-line in the block is a header, not
a body re-declaration.

**Fix**: Track `block_end_idx` (next `##` after the header) and skip
`i <= block_end_idx` in the body loop.

**Why this matters for P0-B**: 30+ of 37 skills have multi-path header
content (`# Label: .path.{key1,key2}` style, or `key1 → .a; key2 → .b`).
Without this fix, fixing G3 by reformatting the header is necessary but
the regex still misfires. P0-B will hit this if anyone copy-pastes the
cloudwatch header.

### Lesson 2 — G1 line count has an off-by-one when the file ends with `\n`

**Symptom**: `check_g1` reports N+1 lines when the file is exactly N lines
ending in `\n`. The function used `text.count("\n") + 1` which double-counts.

**Fix**: Use `len(text.splitlines())` (correct regardless of trailing newline).

**Why this matters for P0-B**: Without the fix, every skill that's
**exactly** 120 lines reports 121 and fails G1 spuriously. Catching this
now means P0-B trusts the `≤ 120` cap.

### Lesson 3 — Frontmatter YAML `cross_skill_deps` and `environment` can be inline arrays

**Symptom**: Multi-line YAML lists eat 6+ lines per skill in frontmatter.

**Fix**: `[aws-iam-ops, aws-vpc-ops, ...]` and
`[AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, ...]` syntax is valid YAML,
parses identically, and saves 4-5 lines per frontmatter.

**Why this matters for P0-B**: 35 skills × 5 lines saved = 175 lines total
recoverable. Doesn't violate any Charter rule (only the semantics matter,
not the YAML shape).

### Lesson 4 — SKILL.md must keep `### SHOULD Use When` / `### SHOULD NOT Use When` literal sub-headers

**Symptom**: Compressing Trigger & Scope into a single paragraph (SHOULD: …
SHOULD NOT: …) saved lines but broke Charter C2's literal check.

**Fix**: Keep the sub-headers even when the content is compressed. The
sub-headers are 4 lines but they preserve the Charter invariant. P0-B
should not strip them.

### Lesson 5 — Cross-file anchor links need a "anchor actually exists in the target" check

**Symptom**: Adding `[references/operations.md#config-placeholders]` in
SKILL.md created a broken link because the section was in SKILL.md, not
in operations.md. C2 (link integrity) only caught the "file exists" part,
not the "anchor exists" part.

**Fix for P0-B**: Build a real link-integrity check that (a) resolves
the file, (b) parses its headings, (c) matches the GitHub-style anchor.
This is a 30-line script, not 200.

### Lesson 6 — TDD step size: replace one block per commit, not all at once

**Symptom**: The first attempt at Pilot B used a 169-line `assert old in text`
script that failed on the AIOps block because my assumption about the
exact whitespace was off by one newline. Hard to bisect.

**Fix**: TDD discipline — replace one section, run `te_gate`, log RED,
move on. Step 1-6 each touched 30-60 lines and were independently
verifiable. The total rewrite was decomposed into 6 atomic steps.

**Why this matters for P0-B**: A 35-skill batch rewrite is doomed if
each skill is one big script. The template should be per-skill step
list: frontmatter compress → JSON paths → trigger & scope → variable
convention → config placeholders → operations extract → safety gates
compress → AIOps compress → TE → quality gate → ref files.

## 2026-07-27 — P0 Trust Boundaries (see plan: `2026-07-27-p0-trust-boundaries.md`)

(Placeholder — lessons from the P0 work should be back-filled here.)

- Lesson 7 — aws-sns-ops: GCL、AIOps 与变量约定可压缩为单段可执行约束；保留确认 token、trace 与输出契约即可通过 C6。
- Lesson 8 — Pilot E 收尾：最终 gate 快照必须同时覆盖行为测试、静态质量、链接完整性与目标技能 TE gate；单独通过行数不足以证明可交付。
- Lesson 9 — SQS/CloudFront 的 JSON path gate 要求路径行以可解析标签开头（如 `CreateQueue: .QueueUrl`）；注释式说明不是机器可验证资产。
- Lesson 10 — EBS 这类长技能应把操作契约留在 SKILL.md、把 CLI/SDK 细节留在 references；压缩到门槛边界时仍可保留全生命周期安全门。
- Lesson 11 — Secrets Manager 的 C6 压缩必须把 SecretString/SecretBinary 永久不可出现在 trace 的规则保留在主技能契约中，不能只放进 references。
- Lesson 12 — Aurora 的 AIOps runbook 表可由统一 delegate contract + references 链接替代，但必须保留 MANUAL/AI_ASSIST/AUTO_HEAL 与破坏性 token 语义。
- Lesson 13 — EKS 的版本静态表违反 TE-1；主技能只保留“一次升级一个 minor 版本”的安全规则，实时支持版本从 API 查询。
- Lesson 14 — Auto Scaling 压缩时必须保留 A16：force delete 前 DesiredCapacity>0 必须先 scale-to-zero，不能被通用删除确认替代。
- Lesson 15 — SSM `send-command` 虽非资源删除，但属于高爆炸半径远程执行；C6 压缩后仍必须使用目标绑定确认并脱敏 stdout/stderr。
- Lesson 16 — ElastiCache 删除契约应默认 final snapshot，并把 `--apply-immediately` 可能触发 failover 作为独立确认场景。
- Lesson 17 — API Gateway 的生产部署替换也是高影响写操作；即使不是删除，也应由 decision tier/token 控制并遮蔽 API keys、auth headers 与 request body。
- Lesson 18 — Lambda 删除前必须显式枚举 event source mappings；存在触发器时升级为 `DELETE_FUNCTION_WITH_TRIGGERS`，普通删除确认不能覆盖隐藏触发器。
- Lesson 19 — OpenSearch 的 AUTO_HEAL 只能执行非破坏性修复；domain、snapshot、VPC endpoint、pipeline 删除和 engine upgrade 均需资源绑定 token。
- Lesson 20 — ELB target deregistration 的确认强度必须随比例升级（<50%、≥50%、100%），这是比统一确认更有效的流量风险表达。
- Lesson 21 — Security Hub AUTO_HEAL 只能更新获批的 finding workflow；不得借自动修复关闭 controls、product import 或 Hub 本身。
- Lesson 22 — EventBridge 删除遵循引用图顺序：targets→rule、rules→bus、API destinations→connection；确认 token 不能替代依赖检查。
- Lesson 23 — S3 C6 契约必须同时保留版本桶 A2、批量删除 A6、敏感文件 A9、公开访问 A15 和 recursive count/bytes 确认，任何单一“删除确认”都不充分。
- Lesson 24 — EFS 删除必须先证明 mount targets、access points 和 consumers 已清理；单一 file-system confirmation 不足以表达依赖风险。
- Lesson 25 — Route53 failover 不能由单一 ELB/health signal 触发；必须多信号验证、记录精确 record diff，并通过决策层授权。
- Lesson 26 — ECR 镜像批量删除要绑定显式 digest/tag 集合与数量，不能用 wildcard/空列表；repository policy 的 public/cross-account widening 需单独确认。
- Lesson 27 — 批量清零 C6 债务时，应按安全域分批并让每批独立 gate；“一次性完成”不等于“一次不可审计的大改”。
- Lesson 28 — 高风险主契约压缩必须保留服务特有硬门：RDS A5、VPC A13、KMS A4、EC2 A1、DynamoDB trigger/TTL、CloudTrail audit restore-only AUTO_HEAL。
