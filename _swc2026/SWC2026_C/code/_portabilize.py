# -*- coding: utf-8 -*-
"""Replace absolute project paths in code/*.py with paths derived from __file__."""
import os
import re
from pathlib import Path

CODE = Path(__file__).resolve().parent
PROJ_EXPR = 'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))'
ROOT_EXPR = 'os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))'

pairs = [
    (r'os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")', f'os.path.join({PROJ_EXPR}, "data")'),
    (r'os.path.dirname(os.path.abspath(__file__))', 'os.path.dirname(os.path.abspath(__file__))'),
    (r'os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")', f'os.path.join({PROJ_EXPR}, "models")'),
    (r'os.path.dirname(os.path.dirname(os.path.abspath(__file__)))', PROJ_EXPR),
    (r'os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))', ROOT_EXPR),
]

changed = []
for p in sorted(CODE.glob("*.py")):
    s = p.read_text(encoding="utf-8", errors="ignore")
    if ".\\_swc2026" not in s:
        continue
    orig = s
    for a, b in pairs:
        s = s.replace(a, b)
    if s == orig:
        continue
    if "import os" not in s.split("\n\n")[0] and not re.search(r'^import os\b', s, re.M):
        # insert after the first coding/comment block, before other imports
        lines = s.splitlines()
        idx = 0
        for i, line in enumerate(lines[:12]):
            if line.startswith("import ") or line.startswith("from "):
                idx = i
                break
        lines.insert(idx, "import os")
        s = "\n".join(lines)
    p.write_text(s, encoding="utf-8")
    changed.append(p.name)

print("changed", len(changed))
print("\n".join(changed))