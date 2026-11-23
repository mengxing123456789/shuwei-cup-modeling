# -*- coding: utf-8 -*-
"""Q2 VOI: the three options' window counts, and the 5 strategies.

Run:  python out\_figcheck\voi_opts.py
"""
import sys, json, pathlib

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')
d = json.load(open(R / 'data' / 'alt_p2.json', encoding='utf-8'))

print('official_options:')
for o in d['official_options']:
    print('  ', json.dumps(o, ensure_ascii=False))
print()
print('voi.strategies:')
for o in d['voi']['strategies']:
    print('  ', json.dumps(o, ensure_ascii=False))
print()
print('voi.marginal_cm2 =', d['voi']['marginal_cm2'])
print('voi.threshold_cm2 =', d['voi']['threshold_cm2'])
print()
print('cross-check: alpha_1 (constant velocity) at L=30 = %.3f' % d['ablation']['alpha_1']['by_L']['30']['mean_cm'])
rows = d['mask_protocol']['rows']
print('mask_protocol.rows:')
for r in rows:
    print('  ', json.dumps(r, ensure_ascii=False))
