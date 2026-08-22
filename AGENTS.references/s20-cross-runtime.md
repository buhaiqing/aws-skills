> 见 [AGENTS.md §20](../AGENTS.md) 索引

## 20. Cross-Runtime Portability Protocol (L4 #11)

§15-§19 ship L4 protocols in one agent runtime (Codex CLI). §20 broadens
the contract: a skill authored here must be **portable** across the major
agent runtimes (Codex CLI, Claude Code, Cursor).

> **Hard rule**: every PR that adds a new skill or updates an existing
> skill's runtime integration must pass
> `python3 scripts/cross_runtime_lint.py lint --skill <name>` with
> score >= 0.85. CI runs `lint --all` against the whole repo.

### Why static lint, not "run on all 3 runtimes"?

Each agent runtime requires its own sandbox (Codex CLI shell, Claude Code
license, Cursor subscription). Running the same prompt through 3 runtimes
inside one CI job is expensive + flaky. **Static lint catches 80% of
portability issues** without that overhead. Phase P3.3 (auto skill
generation) may revisit this with a smaller smoke-test matrix.

### Detection patterns (12 known)

| Pattern | Runtime | Severity |
|---|---|---|
| `~/.codex/` hardcode | Codex CLI | high |
| `~/.claude/` hardcode | Claude Code | high |
| `~/.cursor/` hardcode | Cursor | high |
| `/Users/<name>/` in skill content | host path | critical |
| `/home/<name>/` in skill content | host path | critical |
| `python3.X.Y` exact pin | py-version | medium |
| `<N.N.N>` exact version | version-pin | medium |
| `/usr/local/bin/X` absolute | usr-local | medium |
| `/usr/bin/X` absolute | usr-bin | low |
| `wheel install` instructions | wheel-install | low |
| `sudo apt` instructions | sudo-apt | high |
| `` `brew install` `` | brew | low |

### Scoring

```python
score = max(0.0, 1.0 - (sum_weighted_hits / 10.0))
```

- `score == 1.0` — no detected coupling (clean)
- `score >= 0.85` — at most minor hits (CI pass)
- `score 0.6–0.85` — review recommended
- `score < 0.6` — must fix before merge

The `/ 10.0` divisor makes hit counts additive but bounded:
1 critical hit + 2 medium hits = (1.5 + 0.4 + 0.4) / 10 = 0.23 → score 0.77.

### CLI reference

```bash
# Single skill
python3 scripts/cross_runtime_lint.py lint --skill aws-ec2-ops --repo .

# Whole repo (CI / nightly)
python3 scripts/cross_runtime_lint.py lint --all \\
    --out docs/runtime/cross-runtime-2026-07-25.md

# JSON for CI consumption
python3 scripts/cross_runtime_lint.py lint --skill aws-ec2-ops --json
```

### Portable-fix hints (auto-generated)

Each runtime triggers a specific fix:

| Runtime hit | Suggested fix |
|---|---|
| `codex` | move `~/.codex/config.toml` reference to AGENTS.md §15 integration table; symlink for portability |
| `claude` | same, for `~/.claude/settings.json` |
| `host-path` | replace `/Users/<name>/` with `$HOME/` or `python3 scripts/...` |
| `py-version` | remove `python3.X.Y` pin; rely on shebang `#!/usr/bin/env python3` |
| `version-pin` | use `>=N.N` instead of exact `N.N.N` |

### CI integration

```yaml
# .github/workflows/portability.yml
- name: Cross-runtime portability
  run: |
    python3 scripts/cross_runtime_lint.py lint --all \\
      --out docs/runtime/cross-runtime.md
    SCORE=$(python3 -c "
import json,sys
from cross_runtime_lint import lint_repo
from pathlib import Path
r = lint_repo(Path('.'))
print(min((x.score for x in r.values()), default=1.0))
")
    if (( $(echo "$SCORE < 0.85" | bc -l) )); then
      echo "FATAL: portability score $SCORE < 0.85"
      exit 1
    fi
```

Spec: [`docs/superpowers/specs/2026-07-25-cross-runtime-lint-design.md`](docs/superpowers/specs/2026-07-25-cross-runtime-lint-design.md).
Plan: [`docs/superpowers/plans/2026-07-25-cross-runtime-lint.md`](docs/superpowers/plans/2026-07-25-cross-runtime-lint.md).

