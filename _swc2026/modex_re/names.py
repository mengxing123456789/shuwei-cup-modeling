# -*- coding: utf-8 -*-
"""Extract Cython-qualified names from strings dump."""
import json, sys, re
rows = json.load(open(sys.argv[1], encoding='utf-8'))
mod = sys.argv[2] if len(sys.argv) > 2 else 'workflow_engine'
names = set()
for r in rows:
    s = r['s']
    if s.startswith(mod + '.'):
        # strip lambda/scope noise from the end
        names.add(s)
out = sorted(names)
with open(sys.argv[3], 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(out))
print(len(out), 'names')
