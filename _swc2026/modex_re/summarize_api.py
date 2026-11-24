# -*- coding: utf-8 -*-
"""Summarize introspect JSON into readable text."""
import json, sys

path, out = sys.argv[1], sys.argv[2]
mods = json.load(open(path, encoding='utf-8'))
with open(out, 'w', encoding='utf-8', newline='\n') as f:
    for m in mods:
        f.write(f"===== MODULE {m['module']} ok={m.get('ok')} =====\n")
        if m.get('doc'):
            f.write(f"DOC: {m['doc']}\n")
        if not m.get('ok'):
            f.write((m.get('error') or '') + "\n")
            continue
        consts = [a for a in m['attrs'] if 'value' in a]
        funcs = [a for a in m['attrs'] if 'sig' in a]
        f.write(f"-- CONSTANTS ({len(consts)}) --\n")
        for a in consts:
            f.write(f"{a['name']} [{a['type']}] = {a['value']}\n")
        f.write(f"-- CALLABLES ({len(funcs)}) --\n")
        for a in funcs:
            doc = (a.get('doc') or '').replace('\n', ' | ')
            f.write(f"{a['name']}{a.get('sig','')} :: {doc[:400]}\n")
        f.write("\n")
print("written", out)
