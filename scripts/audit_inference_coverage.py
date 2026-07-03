#!/usr/bin/env python3
"""Audit inference rule coverage between docs and code."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def extract_rules_from_docs(docs_path: Path) -> set[str]:
    """Extract rule IDs from inference-rules.md.
    
    Pattern: **RULE-ID**: at start of heading or in bold
    """
    rules = set()
    content = docs_path.read_text()
    
    # Match patterns like:
    # ### R53-ALB-01: ...
    # **ALB-EC2-01**: ...
    # **EC2-MEM-01**: ...
    # CF-EDGE-01 / CF-ORIGIN-01 (composite)
    patterns = [
        r'^###\s+([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)\s*:',  # ### RULE-ID:
        r'^\*\*([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)\*\*\s*:',  # **RULE-ID**:
        r'\*\*([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)\*\*\s*/\s*\*\*([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)\*\*',  # **RULE1** / **RULE2**
        r'\*\*([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)\*\*\s*/\s*([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)',  # **RULE1** / RULE2
        r'([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)\s*/\s*([A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+)',  # RULE1 / RULE2 (in headings)
    ]
    
    for line in content.split('\n'):
        # Skip comment lines
        if line.startswith('>'):
            continue
            
        for pattern in patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                if isinstance(match, tuple):
                    for rule_id in match:
                        if re.match(r'^[A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+$', rule_id):
                            rules.add(rule_id)
                else:
                    if re.match(r'^[A-Z][A-Z0-9]+-[A-Z0-9]+-[0-9]+$', match):
                        rules.add(match)
    
    return rules


def extract_rules_from_code(code_path: Path) -> set[str]:
    """Extract rule IDs from _inference.py.
    
    Pattern: rule = "RULE-ID"
    """
    rules = set()
    content = code_path.read_text()
    
    # Match pattern: rule = "RULE-ID"
    pattern = r'rule\s*=\s*"([A-Z0-9_-]+)"'
    matches = re.findall(pattern, content)
    
    for match in matches:
        rules.add(match)
    
    return rules


def main() -> int:
    """Main audit function."""
    # Find project root (worktree root)
    project_root = Path(__file__).parent.parent
    
    # File paths
    docs_path = project_root / "aws-aiops-cruise" / "references" / "inference-rules.md"
    code_path = project_root / "aws-aiops-cruise" / "runbooks" / "scripts" / "_inference.py"
    
    # Check files exist
    if not docs_path.exists():
        print(f"Error: Docs file not found: {docs_path}", file=sys.stderr)
        return 1
    if not code_path.exists():
        print(f"Error: Code file not found: {code_path}", file=sys.stderr)
        return 1
    
    # Extract rules
    docs_rules = extract_rules_from_docs(docs_path)
    code_rules = extract_rules_from_code(code_path)
    
    # Compare
    implemented = docs_rules & code_rules  # Rules in both
    unimplemented = docs_rules - code_rules  # Rules in docs but not in code
    orphan = code_rules - docs_rules  # Rules in code but not in docs
    
    # Output
    print("=== Inference Coverage Audit ===\n")
    print(f"Rules in docs: {len(docs_rules)}")
    print(f"Rules in code: {len(code_rules)}\n")
    
    print(f"✅ Implemented ({len(implemented)}):")
    if implemented:
        print(f"  {', '.join(sorted(implemented))}")
    else:
        print("  (none)")
    
    print(f"\n❌ Unimplemented ({len(unimplemented)}):")
    if unimplemented:
        print(f"  {', '.join(sorted(unimplemented))}")
    else:
        print("  (none)")
    
    print(f"\n⚠️  Orphan code ({len(orphan)}):")
    if orphan:
        print(f"  {', '.join(sorted(orphan))}")
    else:
        print("  (none)")
    
    # Result
    if unimplemented or orphan:
        print(f"\nResult: FAIL — {len(unimplemented)} rules unimplemented, {len(orphan)} orphan code")
        return 1
    else:
        print("\nResult: PASS — All rules implemented")
        return 0


if __name__ == "__main__":
    sys.exit(main())
