# Harness Lint Gate (Layer 1 + Layer 2) — Spec

> 解决实测发现的回归:ruff 5 error + 1 红测试 长时间未被 pre-commit / CI 兜住。
> 根因:门禁存在但不覆盖 `scripts/*.py` 的 lint,且测试 import 路径靠每文件手写 `sys.path`,
> 任一测试偏离约定即"本地绿、CI 红"。本 spec 把现有门禁变为**强制**(commit-time 阻断),
> 并消除 import 路径的脆弱性。

## 问题陈述 (Problem)

现状(pre-commit hook `scripts/hooks/pre-commit`):
- 触发 1: `aws-*-ops/SKILL.md` → cross_skill_deps 校验 + `te_gate --strict`
- 触发 2/3: `scripts/gcl_runner.py` / `scripts/te_gate.py` → self-test / `--all --strict`
- 触发 4: `*.py` 等 → `codegraph sync .`(仅 `|| true`,不阻断)

缺口:`scripts/*.py` 的 **ruff lint 不在 pre-commit 任何触发里**。只有 `make lint` / CI 跑 ruff,
而二者都不在 commit 路径上 → ruff error 可静默进入历史。这正是本次 5 个 ruff error 漏网的原因。

测试侧:`scripts/tests/*.py` 各自重复 `REPO = Path(__file__).resolve().parents[2];
SCRIPTS_DIR = REPO / "scripts"; sys.path.insert(0, str(SCRIPTS_DIR))`。无共享 `conftest.py`,
无统一契约 → 单文件用 `import scripts.xxx`(包式)即失败,且该失败只在 pytest 从仓库根运行时暴露。

## 目标 (Goals)

1. **Layer 1**:`scripts/*.py` 的 ruff error 在 `git commit` 时被 pre-commit 硬门禁阻断(零 error 才放行)。
2. **Layer 2**:新增 `scripts/tests/conftest.py` 统一注入 `scripts/` 到 `sys.path`,
   消除每文件手写路径;测试可稳定 `from <module> import ...`。
3. 不破坏现有 hook 触发(1–4)与既有 hook 测试(`test_precommit_hook.py`)。
4. 新增 hook 行为须有测试覆盖(红/绿两条)。

## 非目标 (Non-goals)

- 不动 Layer 3(成熟度文档自动快照)——本次仅 Layer 1+2。
- 不重排各测试文件的既有 import 写法(只新增 conftest 提供兜底;既有 `sys.path.insert` 保留以向后兼容,
  避免大范围改动触发 GCL 多 Agent)。
- 不引入新 lint 工具/新规则维度。

## 设计 (Design)

### Layer 1 — pre-commit 增加 ruff 触发

在 hook 的遍历循环**之前**(即不限于 staged `scripts/*.py`,改为对所有 `scripts/**/*.py`
做一次性全量 ruff 检查,因为单文件 lint 易漏跨文件 import 问题且成本极低),新增:

```bash
# L1+L2 gate: ruff on all scripts (fail-closed, mirrors Makefile `lint`)
if command -v ruff >/dev/null 2>&1; then
    if ! ruff check "$SCRIPTS_DIR" >/dev/null 2>&1; then
        FAIL_REASONS+=("ruff check scripts/ failed — run: ruff check --fix scripts/")
        FAIL=1
    fi
else
    FAIL_REASONS+=("ruff not installed — cannot run lint gate (install: pip install ruff)")
    FAIL=1
fi
```

要点:
- 放在 staged-file 循环**外**,对 `scripts/` 全量检查(一次调用),避免只对改动文件 lint 而漏掉上下文。
- `ruff` 缺失时**失败**(fail-closed),而非静默跳过——否则无 ruff 环境会绕过门禁。
- 其余触发 1–4 不变。

### Layer 2 — conftest.py

新增 `scripts/tests/conftest.py`:
```python
from __future__ import annotations
import sys
from pathlib import Path

# 单一信源:把 repo/scripts 注入 sys.path,使测试可直接 `from <module> import ...`
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
```

效果:各测试文件既有的 `sys.path.insert` 变成冗余但无害(conftest 先执行,路径已在);
未来新增测试无需再手写。单一 `parents[2]` 假设收敛到一处。

## 验收标准 (Acceptance)

- [ ] A1:在 `scripts/` 注入一个 ruff error(临时)后 `bash scripts/hooks/pre-commit`(staged 任意 py)> 退出码 1 且理由含 "ruff check scripts/ failed"。
- [ ] A2:干净 `scripts/` + `git commit` → 门禁对该文件放行(其余触发仍生效)。
- [ ] A3:`python3 -m pytest scripts/tests/ -q` → 全绿(111+ passed),且新增 conftest 不引入 import 警告。
- [ ] A4:既有 `test_precommit_hook.py` 仍全绿(REPO_ROOT 机制不受影响)。
- [ ] A5:`make ci`(lint + test + composite-lint + verify)全绿。
- [ ] A6:ruff 自身对 `scripts/tests/conftest.py` 零 error。

## 风险 (Risks)

- **ruff 未在 CI 镜像**:`setup-hooks.yml` 已 `pip install ruff`,本地 `make setup` 也装;fail-closed 设计下缺失即阻断,促使安装,符合预期。
- **全量 ruff 慢**:`scripts/` ~27 文件,ruff 亚秒级,可忽略。
- **conftest 与既有 `sys.path.insert` 重复**:无害(幂等 insert),不删既有以控制改动面。
