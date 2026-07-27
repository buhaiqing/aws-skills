"""Shared pytest fixture: inject repo/scripts into sys.path.

Single source of truth so every test in scripts/tests can do
`from <module> import ...` without re-deriving REPO / SCRIPTS_DIR per file.
Conftest runs before any test module, making the path injection idempotent
with the legacy per-file `sys.path.insert` boilerplate (now redundant but harmless).
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
