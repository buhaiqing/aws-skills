# §23 — Edit Surgery Discipline

> 见 [AGENTS.md §23](../AGENTS.md) 索引

## §23.0 问题根因

三次事故的共同教训：

1. **Edit tool 破坏文件** — `PUT N.=M` 范围选错产生孤岛代码或语法错误
2. **写操作覆盖而非追加** — `write` 用于追加时抹掉原内容
3. **新增 schema 字段打破向后兼容** — dataclass required 字段使现有 caller 全部报错

三条规则对应三个根因。

## §23.1 文本编辑：优先用 Python 而非 Edit 工具（hard rule）

对于涉及多行、跨函数、跨 section 的修改，**永远使用 Python 脚本**而不是 Edit 工具。Edit 工具适合单行或单函数内的精确替换；多行改动用手工编辑极易产生孤岛行或语法错误。

```bash
python3 << 'PYEOF'
path = 'scripts/parallel_gcl_runner.py'
src = open(path).read()
# 做所有替换
src = src.replace('old', 'new')
open(path, 'w').write(src)
# 验证语法
import ast; ast.parse(src)
print('AST OK')
PYEOF
```

**要求**：Python 脚本输出 `AST OK` 才算完成。

**何时用 Edit 工具**：单行精确替换、注释修改、docstring 编辑。

## §23.2 写文件：永远确认是覆写还是追加（hard rule）

| 场景 | 正确方式 |
|---|---|
| 覆盖整个文件（如 recreate） | `write` — 确认文件当前内容已无用 |
| 在文件末尾追加测试函数 | Python `open(path, 'a')` 或 `bash cat >> path` |
| 替换文件中一段连续内容 | Python `src.replace(old, new)` |

**禁止**：在未确认文件当前状态时用 `write` 追加内容。

## §23.3 Schema / dataclass 新字段必须带 default（hard rule）

```python
# 正确：所有字段都有 default，caller 渐进适应
@dataclass
class GeneratorOutput:
    command: str                    # required
    args: dict                     # required
    exit_code: int                 # required
    result_excerpt: str = ""       # optional：加 default
    safety_confirm_token: str = ""  # optional：加 default
```

```python
# 错误：required 字段打断所有现有 caller
@dataclass
class GeneratorOutput:
    command: str
    args: dict
    exit_code: int
    result_excerpt: str  # 无 default → 所有 caller 必须改
```

新增 required 字段等同于破坏性 API 变更，必须走 deprecation 流程：先加 optional（带 default），跑通所有测试，再在下一个 major 版本升为 required。

## §23.4 Validation 顺序：required fields 最优先（hard rule）

`from_dict` / `validate` 方法内部的检查顺序必须严格：

```
1. required top-level fields（task_id, subtasks 等）
2. type correctness（isinstance checks）
3. non-empty / length constraints（subtasks 非空、suggestions ≤3 等）
4. cross-field constraints
```

**错误顺序**（曾导致误导性错误信息）：

```python
# subtasks 判空先于 task_id 检查 → 缺失 task_id 时报错 "subtasks 为空"
if not isinstance(data["subtasks"], list) or len(data["subtasks"]) == 0:
    raise ValueError("subtasks must be non-empty")
for f in REQUIRED_FIELDS:
    if f not in data:
        raise ValueError(f"missing {f}")  # 永远执行不到
```

**正确顺序**：

```python
for f in REQUIRED_FIELDS:
    if f not in data:
        raise ValueError(f"missing required field: {f}")
if not isinstance(data.get("subtasks"), list) or len(data["subtasks"]) == 0:
    raise ValueError("subtasks must be non-empty")
```

## §23.5 每步 edit 后立即验证语法（hard rule）

每次编辑（Edit 工具或 Python 脚本）后，在同一会话中立即运行：

```bash
python3 -c "import ast; ast.parse(open('scripts/xxx.py').read()); print('OK')"
```

语法错误不等下一个 cell 掩藏。验证通过后再继续。失败则回退（`git checkout`）并重新来过。

## §23.6 大改写前先 `git commit`

当一个文件被编辑超过 5 次或累计超过 3 个函数被修改，**先 commit 当前状态**，再继续。这让回退有干净锚点：

```bash
git add -p scripts/parallel_gcl_runner.py
git commit -m "WIP: refactoring trace schema"
```

## §23.7 测试文件变更后跑全 suite 再继续

修改测试文件后立即跑：

```bash
python3 -m pytest scripts/tests/test_xxx.py -q
```

全绿再继续。任何测试失败都立即修，不留到最后一并处理。

## §23.8 多 phase patch 合并策略（ponytail: 默认按需 consolidated patch）

**触发**：连续 N 笔 commit 改同一 changelog / TODO / maturity-model 文件 → 后续 phase 必须用 consolidated mega-patch，否则中间 commit 的 git history 制造 8-10× diff churn（详见 F-006）。

**规则**：
- 同一 sprint / phase 的 changelog / progress.md / maturity-model.md 更新**只在最后 1 笔 commit 写**，中间 commit 不碰这些 shared 文件。
- 每个 phase 单笔 patch 仍可写（archival 价值），但合并阶段必须出 `*-consolidated.patch` 作为 canonical artifact 单独 ship。
- sprint 跨度大 (>5 笔 commit) 时，**强制**在最后一个 phase commit 之前生成 consolidated patch。

**反例**（F-006 实证）：
```
AGENTS.md (8 patches: l3-p1 → p3-4)
TODO.md (10 patches: ALL of them)
docs/agentic-maturity-model.md (10 patches: ALL of them)
docs/superpowers/findings/F-005-*.md (2 patches)
scripts/golden_eval.py (2 patches: p2-2 + p2-3)
```

**教训**：F-006 在 2026-07-26 首次记录，60+ 天 open。最终处置：WONTFIX-as-DOCUMENTED（按本节规则预防）。

> **状态**：F-006 closed 2026-09-24 (per §23.8 rule codification).
