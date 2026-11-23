# -*- coding: utf-8 -*-
"""Check whether the sensitivity table's numbers have product keys, and whether
merge threshold / drop fraction were ever swept. Also list verify_numbers claim names.

Run:  python out\_figcheck\sens_keys.py
"""
import sys, json, re, pathlib

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')

d = json.load(open(R / 'data' / 'alt_p1.json', encoding='utf-8'))
print('alt_p1.json sensitivity: %d entries' % len(d['sensitivity']))
for s in d['sensitivity']:
    print('  ', json.dumps(s, ensure_ascii=False))

print()
print('config keys in alt_p1.json (the swept values live here?):')
print('  ', json.dumps(d['config'], ensure_ascii=False))

print()
t = (R / 'code' / 'verify_numbers.py').read_text(encoding='utf-8')
names = re.findall(r'name\s*=\s*[\'"]([^\'"]+)', t)
print('verify_numbers.py claim names: %d' % len(names))
for n in names:
    print('   ', n)

print()
for kw in ('merge', 'drop', 'sens', 'hazard', 'sigma', 'sensitivity'):
    hits = [i + 1 for i, l in enumerate(t.split('\n')) if kw in l.lower()]
    print('verify_numbers.py mentions %-10s -> %d lines %s' % (kw, len(hits), hits[:8]))
