# aws-skills Makefile
# Standard targets for local dev + CI parity.

.PHONY: help setup test lint verify composite-lint cross-runtime-lint clean

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

ci: lint test composite-lint verify  ## Run all CI checks locally
