# Layer 3 — 成熟度文档自动证据快照 (Spec)

> 根因 #3:成熟度文档(`docs/agentic-maturity-model.md`)的 "L4 99% / 测试全绿" 是**手工维护的叙述性真理**,
> 不是门禁的真实输出 → 文档与事实漂移无人察觉(本次就出现过错判 baseline 红)。
> Layer 3 不让机器去"算成熟度百分比"(那是主观能力评估,不可纯机器派生),
> 而是让文档的**健康声明**指向一份**机器生成、带日期、可复现**的证据文件。

## 目标 (Goals)

1. 新增 `scripts/status_snapshot.py`:一次调用,真实跑 pytest + ruff + composite_lint + self_review verify,
   输出 JSON(到 stdout) + 写 `docs/status-snapshot.md`(Markdown 证据块,含执行日期)。
2. 让成熟度文档的"健康/测试状态"声明改为**引用** `docs/status-snapshot.md`,而非手写静态数字。
3. `make ci` 增加 `snapshot` 步骤(记录证据);`make status` 供本地查看。
4. 不改动既有 `lint`/`test`/`composite-lint`/`verify` 门禁语义。

## 非目标 (Non-goals)

- 不自动计算/改写 L1–L4 成熟度百分比(主观评估,保持人工作者署名)。
- 不新增测试,不新增 lint 维度。
- 不把 snapshot 变成"阻断式门禁"(pytest/ruff 本身已是阻断门禁;snapshot 是记录器 + 引用源)。

## 设计 (Design)

### `scripts/status_snapshot.py`

CLI:`python3 scripts/status_snapshot.py [--json] [--out docs/status-snapshot.md]`

执行流程:
1. `pytest`(scripts/tests):捕获 pass/fail/error 数(用 `pytest -q` 解析末行,或 subprocess 捕获)。
2. `ruff check scripts/`:error 计数(解析 `ruff check` 末行 "N error(s)" 或退出码)。
3. `composite_lint.py lint --all`:退出码(0=pass)。
4. `self_review.py verify`:stale_p0 数(解析其输出或 import 函数)。

输出 JSON 形状:
```json
{
  "generated_at": "2026-07-27",
  "pytest": {"passed": N, "failed": M, "error": K, "ok": bool},
  "ruff": {"errors": E, "ok": bool},
  "composite_lint": {"ok": bool},
  "self_review": {"stale_p0": S, "ok": bool},
  "all_ok": bool
}
```

Markdown 证据块(`docs/status-snapshot.md`)含:生成日期 + 四项真实数字 + `all_ok` + 一句
"本文件由 `make snapshot` 生成,手工编辑会被覆盖"。

### 成熟度文档改动

在 `docs/agentic-maturity-model.md` 的状态总览(§8)/Changelog 处,把静态 "测试全绿/L4 99%" 硬断言
改为:
> 运行健康证据(机器生成,带日期):见 [`docs/status-snapshot.md`](../status-snapshot.md)。
> 能力成熟度百分比为人工评估(见各 Level 章节);健康证据仅证明门禁当前状态。

这样"能力评估(人工)"与"健康证据(机器)"分离,漂移可被独立核验。

### Makefile

```makefile
status:         ## Show live harness health snapshot
	python3 scripts/status_snapshot.py
snapshot:       ## Regenerate docs/status-snapshot.md (CI records evidence)
	python3 scripts/status_snapshot.py --out docs/status-snapshot.md
ci: lint test composite-lint verify snapshot  ## Run all CI checks locally
```

## 验收 (Acceptance)

- [ ] A1:`python3 scripts/status_snapshot.py --json` 输出合法 JSON,含四项真实数字 + `all_ok`。
- [ ] A2:`python3 scripts/status_snapshot.py --out docs/status-snapshot.md` 生成带日期的证据文件;
      重跑幂等(内容一致,仅日期可能变)。
- [ ] A3:当 pytest/ruff 实际红时,JSON `all_ok=false`(用注入法验证一次,不提交红状态)。
- [ ] A4:成熟度文档新增"证据引用"段落,指向 `docs/status-snapshot.md`,删除/弱化静态 "测试全绿" 硬断言。
- [ ] A5:`make status` / `make snapshot` 可执行;`make ci` 含 snapshot 且不破坏既有门禁。
- [ ] A6:`ruff check scripts/status_snapshot.py` 零 error;该脚本有 ≥1 单元/集成测试覆盖核心解析。

## 风险 (Risks)

- pytest 解析脆弱:用 `pytest -q` 末行 "N passed, M failed" 解析;若格式变则测试会红 → 用 `pytest` 的
  `--json-report` 不可靠(未装),改为 subprocess + 正则末行,并加测试覆盖解析函数。
- 文档改动范围:仅新增引用段 + 弱化一处硬断言,不重写百分比(避免大改动触发 GCL 多 Agent)。
- `docs/status-snapshot.md` 提交到仓库:作为证据基线,CI 每次刷新;可接受(类似 lockfile 思路)。
