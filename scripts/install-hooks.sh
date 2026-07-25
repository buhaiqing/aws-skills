#!/usr/bin/env bash
# Install pre-commit hook (idempotent).
# Run once per clone: bash scripts/install-hooks.sh
set -euo pipefail
git config core.hooksPath scripts/hooks
echo "✓ core.hooksPath → scripts/hooks"
echo "  (git commit will now invoke scripts/hooks/pre-commit automatically)"
echo "  Bypass for emergency hotfixes: git commit --no-verify (log in commit body)"
