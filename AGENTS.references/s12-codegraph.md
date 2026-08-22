> 见 [AGENTS.md §12](../AGENTS.md) 索引

## 12. CodeGraph Integration (Code Knowledge-Graph Integration)

Local-first code knowledge graph tool ([colbymchenry/codegraph](https://github.com/colbymchenry/codegraph),
installed at `/Users/bohaiqing/.local/bin/codegraph`, Node v22.19.0). Builds a
local SQLite graph (`.codegraph/codegraph.db`) via tree-sitter, integrated
through MCP (tools `codegraph_explore` / `codegraph_node`). **Design goal:
cross-coding-agent universal** — one `codegraph serve --mcp` definition is
automatically projected to each agent's native config (OpenCode / Cursor /
Claude Code / Codex / Hermes Agent / Kiro / CodeBuddy, etc.) with no
per-agent adaptation. 100% local, no data leakage.

### Purpose

Before editing a skill's `SKILL.md` / `references/` or shared scripts
(`scripts/gcl_runner.py`, `_shared.py`, etc.), use CodeGraph to verify
**cross-skill reference consistency** and **change blast radius**, reinforcing
the Operational Guidelines rule "cross-file references must stay in sync across
three parties" (definitions / calls / docs).

This repo's 34 `aws-<svc>-ops` skills reference each other frequently (e.g.,
`aws-rds-ops`→`aws-aurora-ops`, `aws-elb-ops`↔`aws-vpc-ops`); changing one
place can affect many. `codegraph explore "aws-aurora-ops"` returned 36 symbols
across 3 files + blast radius in practice (`run_aws` has 61 callers across 15+
files).

### Commands

```bash
codegraph init .              # build graph first time (measured: 564 nodes / 1,329 edges)
codegraph sync .              # incremental sync of changes since last index (run before every code change)
codegraph explore "<symbol>"  # query blast radius / cross-file call sites
codegraph status              # query index status (Files/Nodes/Edges/DB Size)
```

### MCP Integration (cross-agent universal, done once)

**Single technique**: `codegraph serve --mcp` (stdio). One server definition is
automatically projected via `codegraph install -t all` into each agent's native
config (OpenCode / Cursor / Claude Code / Codex / Hermes / Kiro / CodeBuddy,
etc.); each agent just reads its own config — **no per-agent adapter code
needed**:

```bash
codegraph install -t all      # project codegraph MCP into all installed agents' global configs
# or specify: codegraph install -t opencode,cursor,claude,codex,hermes,codebuddy
```

- **Repo-level auto-discovery**: this repo root has `.mcp.json` (declares
  `mcpServers.codegraph`). Agents that support project-level MCP (Cursor /
  Claude Code / CodeBuddy with project-MCP) auto-detect and load it on opening
  this directory — no manual install needed.
- **CLI equivalents** (`codegraph explore` / `codegraph node` / `codegraph sync`)
  are always available even without MCP — the "sync + cross-skill check before
  editing" in AGENTS.md §12 does not depend on MCP.
- After install, **restart the relevant agent session** to take effect; uninstall
  with `codegraph uninstall -t all`.

### Rules

| Item | Requirement |
|------|-------------|
| **Before every code file change** (`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` etc. tree-sitter-supported languages, not `.md`/`.yaml` docs) | **Must run `codegraph sync .`** (incremental sync) so subsequent `explore` / `impact` are based on the latest index; if no index exists, run `codegraph init .` first |
| `.codegraph/` | Its own `.gitignore` (`*` + `!.gitignore`) already excludes the contents; committing the index is forbidden; the root `.gitignore` may add `.codegraph/` (optional, keeps `git status` silent) |
| Before editing shared scripts / delegation refs | First `codegraph sync .` then `codegraph explore "<symbol>"` to confirm call sites match the docs |
| GCL task R2 content review | Use CodeGraph to help verify cross-skill delegation references exist (e.g., dirs pointed to by `SHOULD` / `SHOULD NOT` really exist) |
| Relation to self-review | Does not replace the 2-round self-review; only adds machine verification for cross-skill references |

### Boundary of applicability (by scenario — from 2026-07-19 session retro)

> **Key fact (measured):** CodeGraph builds a **code** symbol graph via
> tree-sitter and does **not index Markdown frontmatter**. This repo's skill
> corpus is Markdown-dominated (measured: within `aws-*` dirs, `.md` ≈ 72% /
> `.py` ≈ 9%); its `metadata:` / `delegate:` / delegation-dir references are
> **invisible to CodeGraph**.
> Therefore you must **route by file type (code vs non-code docs), not by
> specific language** — CodeGraph covers all supported languages via
> tree-sitter, not just Python; otherwise you get "didn't use it when you
> should, and used it but found nothing":

| Change type | Correct tool | Use CodeGraph? |
|------------|--------------|----------------|
| **Code files** (any tree-sitter-supported language: `.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` etc., including `_inference.py` / `_shared.py` / `gcl_runner.py` / `collectors` / `daily-health-check.py`) | `codegraph sync .` + `codegraph explore "<symbol>"` to check blast radius | ✅ **Must** — CodeGraph builds a code symbol graph via tree-sitter, covering all supported languages, not just Python |
| **Markdown skills** (`SKILL.md` / `references/*.md` / `AGENTS.md` frontmatter, delegation tables, routing tables) | `git grep` / Grep tool (verify by dir existence, string reference) | ❌ **Not needed** — CodeGraph does not index `.md`; forcing it returns "No relevant code" |

> **Improvement loop (dogfood):** This session once used Grep in place of
> CodeGraph throughout (violating §12), but the root cause was **tool
> mismatch** — a Markdown-dominated need should not have gone through CodeGraph
> in the first place. Corrected approach:
> 1. Before editing a Python script, **first `codegraph sync .` then `explore`**
>    to re-check blast radius (e.g., before editing `_inference.py`, confirm the
>    16 callers of `apply_chain_inference` are unaffected);
> 2. For editing Markdown skills, use Grep / `git grep`, do not force CodeGraph;
> 3. To make CodeGraph cover the skill corpus, it would need a Markdown
>    frontmatter extractor added (**out of scope for this §12**, a separate plan).

### Mandatory Split Gate (data-driven, must be strictly enforced — 2026-07-19 A/B comparison conclusion)

> **Decision basis (measured, not vibe):** This session ran an A/B test on two
> query types (Grep = B, current approach; CodeGraph CLI = candidate). Results:
>
> | Experiment | Query type | Grep result | CodeGraph result | Winner |
> |-----------|------------|-------------|------------------|--------|
> | E1 | Markdown delegation refs (who references aurora-ops) | **4/4 recall, 0 misses**, 0.03s | returned "36 code symbols", for the actual Markdown delegation question **0/4** | **Grep** |
> | E2 | Code symbol blast radius (make_incident) | 59 unique raw call sites, no test labels | 42 deduped callers + `⚠️ no-test` label | **CodeGraph** |
> | E3-Q1/3/5 | Non-code doc graph (Markdown skills) | correct* (regex must be right)*; Q5 missed because **my own glob was wrong** (truth=2: `aws-elb-ops/assets/example-config.yaml` + `aws-aiops-orchestrator/SKILL.md`, Grep returned 0) | structurally blind to `.md` | **Grep** (when query correct) |
> | E3-Q2/4 | Code symbol call graph (Python etc. tree-sitter languages) | 71 raw lines, needs manual dedup | 61/34 callers + test labels, instant | **CodeGraph** |
>
> **Conclusion:** Forcing a single tool ("all CodeGraph" or "all Grep") degrades
> **about half** the queries in this repo. The correct strategy is **routing by
> file type** — this is the conclusion that the §12 "Boundary of applicability"
> subsection is **validated by this experiment's data**.

| Query/change type | **Mandatory** tool | Forbidden | Rationale (measured) |
|-------------------|--------------------|-----------|----------------------|
| **Non-code docs** (`.md` frontmatter/delegation tables/routing tables, `references/*.md`, `AGENTS.md`, `*.yaml` config docs) | **Grep / `git grep`** | ❌ Must not use CodeGraph | CodeGraph does not index non-code docs; E1 measured 0/4 |
| **Code files** (any tree-sitter language: `.py`/`.ts`/`.go`/`.rs`/`.js`/`.java` etc.) blast radius / call sites | **`codegraph sync .` + `codegraph explore`** | ❌ Must not just use Grep | E2 measured CodeGraph adds dedup + test-coverage labels; tree-sitter covers all supported languages, not just Python |
| **Any query** | Query must be **constructed correctly** (glob/regex/args must match repo's actual layout) | ❌ Must not fudge with wrong glob/regex/args | E3-Q5: my own glob `aws-*-ops` failed to match `aws-aiops-orchestrator` (no `-ops` suffix) causing a miss, truth=2 not 0/1 — a bad query = silent wrong answer, independent of the tool |

> **Final verdict (2026-07-19 A/B comparison conclusion, 5 reviewers unanimous):**
> Forcing a single tool ("all CodeGraph" or "all Grep") degrades **about half**
> the queries in this repo. CodeGraph (tree-sitter code symbol graph) and Grep
> are **complementary**, not substitutes — the former works on **code files of
> all supported languages**, the latter on **non-code docs** (`.md`/`.yaml`
> frontmatter).
> **Winning approach = route by file type** (not by language, not either/or):
> - 🟢 Code files (any tree-sitter language) → `codegraph sync .` + `explore`
> - 🟢 Non-code docs (`.md`/`.yaml`) → Grep / `git grep`
> - 🟢 Any query → first verify the glob/regex matches the repo's actual dir layout
>
> **Execution discipline (user hard constraint):** Once this routing decision is
> made, **enforce it strictly in every subsequent action** — all non-code doc
> queries use Grep, all code blast-radius queries use CodeGraph; do not fall back
> to a single tool out of habit. Violation is treated as a quality regression.
> This gate works with §13 CADL and the Operational Guidelines
> "Fan-out Subagents": each subtask must still go through the corresponding
> routing + asset distillation.
>
> **`sync` is not enough (finer lesson, 2026-07-19 Task #10 retro):**
> when CodeGraph *is* the right tool (code files), running only `codegraph sync .`
> builds the index but yields **nothing actionable** — the high-value step is the
> **integration-point query** (`explore` / `node` / `callers`) that reveals
> the call graph, signatures, and cross-file contracts *before* editing.
> This session, a fan-out added 5 collectors + inline inference blocks; `sync` ran but
> the `callers`/`node` queries were skipped during coding and only run post-hoc
> to answer a user challenge — they immediately surfaced the `(incidents, {svc:
> signals})` collector→inference contract and the `test_all_collectors_run`
> test that exercises all collectors, which Read-alone would have taken longer.
> **Disposition:** for code changes, run `sync` *then* `explore`/`callers`/`node`
> to locate integration points and callers **before** stitching — not just baseline sync.
> Do not claim "CodeGraph integrated" if only `sync` ran; be precise about what
> was actually done (matches the honesty bar in §12's wrong-query lesson).

> **Asset landing (correct CADL placement):** The most transferable lesson from
> this experiment — "a **wrong query (bad glob/regex) is more insidious than a
> wrong tool, it answers silently wrong**" (E3-Q5) — must be written separately
> to `docs/failure-patterns.md` (pitfall assets go to failure-patterns, not
> AGENTS.md), for any future agent to retrieve and reuse.


### Pre-commit Hard Gate (硬门禁 — automation, not suggestion)

The rules above are **enforced**, not advisory. `scripts/hooks/pre-commit` runs
automatically on `git commit` (after one-time `bash scripts/install-hooks.sh`).
Five triggers, all blocking:

1. `aws-*-ops/*/SKILL.md` staged → for each changed skill, verify every name in
   `metadata.cross_skill_deps` / `metadata.delegate` keys points to an existing
   directory in this repo (`test -d`); fail commit if any miss.
2. `scripts/gcl_runner.py` or `scripts/te_gate.py` staged → run their
   `--self-test` / `--all --strict` modes respectively; fail commit on regression.
3. **Every commit** → run the complete repository unit-test suite
   `pytest -p no:rerunfailures scripts/tests/ -q`; every collected test MUST
   pass before `git commit` may proceed. A failed, errored, timed-out, skipped
   due to missing dependencies, or unexecuted required test blocks the commit;
   fix the regression or restore the required test environment first. Do not
   weaken, delete, mark `xfail`, or skip a test merely to make the gate pass.
4. Code files (`.py`/`.ts`/`.go`/`.rs`/`.js`/`.java`) staged → `codegraph sync .`
   runs as part of the hook (mandatory pre-flight per §12 above).
5. `REPO_ROOT` env var overrides auto-detection (testability only).

**Bypass**: only for emergency hotfixes, with `git commit --no-verify`; the
bypass event MUST be logged in the commit body.


