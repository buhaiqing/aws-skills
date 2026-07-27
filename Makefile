# aws-skills Makefile
# Standard targets for local dev + CI parity.

.PHONY: help setup test lint verify composite-lint cross-runtime-lint status snapshot clean

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup:          ## Install pre-commit hook + Python dev deps
	@bash scripts/install-hooks.sh
	@pip install pytest ruff pyyaml 2>&1 | tail -3 || true

test:           ## Run full pytest suite
	python3 -m pytest -p no:rerunfailures scripts/tests/ -q

lint:           ## Run ruff on all scripts + tests
	ruff check scripts/

composite-lint: ## Lint all composite/orchestrator-meta skills
	python3 scripts/composite_lint.py lint --all

cross-runtime-lint: ## Lint cross-runtime portability for all skills
	python3 scripts/cross_runtime_lint.py lint --all

verify:         ## §21 Self-Reflection verify (no stale P0)
	python3 scripts/self_review.py verify

status:         ## Show live harness health snapshot (JSON + Markdown to stdout)
	python3 scripts/status_snapshot.py

snapshot:       ## Regenerate docs/status-snapshot.md (machine evidence for maturity doc)
	python3 scripts/status_snapshot.py --out docs/status-snapshot.md

# snapshot runs first as a recorder so docs/status-snapshot.md is always fresh,
# even on a red tree; the "-" prefix keeps it non-blocking so lint/test remain
# the authoritative CI failure signal.
ci: snapshot lint test composite-lint verify  ## Run all CI checks locally
