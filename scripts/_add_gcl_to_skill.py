#!/usr/bin/env python3
"""
Helper: inject `metadata.gcl` block into a skill's SKILL.md frontmatter.

Usage:
    python3 _add_gcl_to_skill.py <skill-dir> <class> <max_iter> <pilot>

Example:
    python3 _add_gcl_to_skill.py aws-dynamodb-ops required 2 false

Reads SKILL.md, parses YAML frontmatter, inserts (or replaces) the `gcl:`
sub-block under `metadata:`, bumps `version` by 0.1.0, updates
`last_updated` to 2026-06-04, and writes back.

Idempotent: running twice does not double the gcl block.
"""
import re
import sys
from pathlib import Path

import yaml


def bump_version(v: str) -> str:
    """1.2.0 -> 1.3.0; 2.0.0 -> 2.1.0; etc."""
    parts = v.strip().strip('"').split('.')
    if len(parts) != 3:
        return v
    parts[1] = str(int(parts[1]) + 1)
    parts[2] = '0'
    return '.'.join(parts)


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(1)
    skill_dir, klass, max_iter, pilot = sys.argv[1:5]
    skill_md = Path(skill_dir) / 'SKILL.md'
    text = skill_md.read_text()
    m = re.search(r'^---\n(.*?)\n---', text, re.DOTALL | re.MULTILINE)
    if not m:
        print(f'ERROR: no frontmatter in {skill_md}', file=sys.stderr)
        sys.exit(2)
    fm_text = m.group(1)
    data = yaml.safe_load(fm_text)
    md = data.setdefault('metadata', {})
    md['version'] = bump_version(md.get('version', '1.0.0'))
    md['last_updated'] = '2026-06-04'
    gcl = md.get('gcl', {})
    gcl['enabled'] = True
    gcl['class'] = klass
    gcl['max_iter'] = int(max_iter)
    gcl['rubric_version'] = gcl.get('rubric_version', 'v1')
    gcl['rubric_ref'] = gcl.get('rubric_ref', 'references/rubric.md')
    gcl['prompts_ref'] = gcl.get('prompts_ref', 'references/prompt-templates.md')
    gcl['pilot'] = pilot.lower() in ('true', '1', 'yes')
    md['gcl'] = gcl
    new_fm = yaml.safe_dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    new_text = text[:m.start()] + '---\n' + new_fm + '---' + text[m.end():]
    skill_md.write_text(new_text)
    print(f'OK  {skill_dir}: version={md["version"]} gcl.class={klass} gcl.max_iter={max_iter} gcl.pilot={gcl["pilot"]}')


if __name__ == '__main__':
    main()
