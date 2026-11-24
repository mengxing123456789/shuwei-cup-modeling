# -*- coding: utf-8 -*-
import json, sys, os
path = sys.argv[1]
outdir = sys.argv[2]
mods = json.load(open(path, encoding='utf-8'))
for m in mods:
    name = m['module'].split('.')[-1]
    with open(os.path.join(outdir, f'api_{name}.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(f"MODULE {m['module']} ok={m.get('ok')}\nDOC: {m.get('doc')}\n\nCONSTANTS:\n")
        for a in m.get('attrs', []):
            if 'value' in a:
                f.write(f"{a['name']} [{a['type']}] = {a['value']}\n")
        f.write("\nCALLABLES:\n")
        for a in m.get('attrs', []):
            if 'sig' in a:
                doc = (a.get('doc') or '').replace('\n', ' | ')
                f.write(f"{a['name']}{a.get('sig','')} :: {doc[:600]}\n")
print('done')
