# Composite Lint + Setup-Hooks CI — Design (L4 P0 closure)

- **Date**: 2026-07-26
- **Status**: 定稿 (待实施)
- **Priority**: P0 — closes gaps L2.1 + L2.2 + L4.1 (per `maturity-2026-07-26.md`)
- **Source signal**: 诚实重审发现 L4 "100% 表面" 下 pre-commit opt-in + composite 未自动验证

## 1. 背景

诚实重审 (2026-07-26) 发现 2 个 P0 gap:

1. **L2.1 / L4.1**: pre-commit hook (`scripts/hooks/pre-commit`) **未默认安装** —
   clone 后 `git config core.hooksPath` 为空, 所有 Charter C1-C6 + TE gate 防护**零生效**
2. **L2.2**: composite skill (`aws-aiops-copilot` 等 4 个) 的 `delegate:` 块**没有
   自动化校验** — 仅人工 review, 容易漏检 "target dir missing" 或 "operation not in target.provides"

## 2. 目标

### 2.1 `scripts/composite_lint.py`

静态 lint 所有 composite/orchestrator-meta skill, 验证:

1. `delegate:` 块每个 target 目录存在
2. 每个 target 的每个 operation 在目标 skill 的 `provides:` (or `accepts:`) 中能找到
3. 输出 Markdown 报告 + JSON + 退出码 (0/1)

### 2.2 `.github/workflows/setup-hooks.yml`

GitHub Actions 在 CI 强制执行:

1. `bash scripts/install-hooks.sh` (让 CI 自己 install hooks, 但 hooks 不会在 CI 触发)
2. **核心**: 跑 `scripts/composite_lint.py` 作为 CI gate
3. 跑 `python3 -m pytest scripts/tests/` (regression)
4. 跑 `ruff check scripts/`

## 3. 契约

```python
@dataclass(frozen=True)
class DelegateRef:
    parent: str             # "aws-aiops-copilot"
    target: str             # "aws-aiops-cruise"
    operation: str          # "rca"
    line_number: int

@dataclass(frozen=True)
class CompositeIssue:
    parent: str
    target: str
    operation: str
    issue: str              # "target_dir_missing" | "operation_not_provided"
    detail: str

@dataclass(frozen=True)
class CompositeLintReport:
    parent: str
    score: float            # 1.0 = all clean
    refs: list[DelegateRef]
    issues: list[CompositeIssue]

def lint_composite(skill_md: Path, repo: Path = REPO) -> CompositeLintReport: ...
def lint_repo(repo: Path = REPO) -> dict[str, CompositeLintReport]: ...

KNOBS = {
    "composite_types": ("composite", "orchestrator-meta"),
}
```

## 4. composite frontmatter 形式 (verified)

```yaml
metadata:
  type: composite   # 或 orchestrator-meta
  provides:
  - aiops-health-check
  - aiops-rca
  delegate:
    aws-aiops-cruise:
    - health-check
    - rca
    aws-aiops-orchestrator:
    - cross-service-rca
```

注意: `delegate:` 是 dict[target_skill, list[operation]]. Operation 应是 target's
`provides:` 的子集 (或 target's `delegate.accepts:` 子集, 兼容 aiops-cruise 风格).

## 5. CLI

```bash
# lint 单个 composite
python3 scripts/composite_lint.py lint --skill aws-aiops-copilot

# lint 所有 composite
python3 scripts/composite_lint.py lint --all --out docs/superpowers/reports/composite-2026-07-26.md

# JSON 输出 (供 CI 消费)
python3 scripts/composite_lint.py lint --all --json
```

退出码:
- `0` = 所有 composite score = 1.0
- `1` = 至少 1 个 composite 有 issue

## 6. CI workflow

`.github/workflows/setup-hooks.yml`:
```yaml
name: setup-hooks + composite-lint
on: [push, pull_request]
jobs:
  composite-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r scripts/requirements.txt || true
      - run: bash scripts/install-hooks.sh
      - run: python3 scripts/composite_lint.py lint --all
      - run: python3 -m pytest -p no:rerunfailures scripts/tests/ -q
      - run: ruff check scripts/
```

## 7. 验收

1. RED → GREEN: **≥6 effective tests**:
   - lint_composite w/ all-valid → score 1.0, 0 issues
   - lint_composite w/ missing target dir → score < 1, "target_dir_missing" issue
   - lint_composite w/ operation not in provides → score < 1, "operation_not_provided"
   - lint_repo returns dict for 4 known composites
   - CLI `--all` exits 0 on clean state, 1 on dirty state
   - Edge: empty delegate block → score 1.0, 0 issues (no ref = no problem)
2. 真跑 `lint --all` → 4 composites, score 1.0/1.0/1.0/1.0, 0 issues (基于当前仓库)
3. CI workflow YAML 有效 (用 `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/setup-hooks.yml'))"`)
4. ruff clean
5. maturity model: L4 88% → **95%**
