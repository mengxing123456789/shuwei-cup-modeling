# -*- coding: utf-8 -*-
"""tab:p1sens forensics: how many DISTINCT configurations the 8 rows really are,
where the chosen cell ranks on each metric (including the metric the table does
not print), and whether min_seg_s / map_drop were ever swept.

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\sens_rank.py
"""
import sys, json, pathlib

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')
d = json.load(open(R / 'data' / 'alt_p1.json', encoding='utf-8'))
rows = d['sensitivity']
cfg = d['config']

print('config chosen: hazard_lambda_s=%s  sigma_s=%s  min_seg_s=%s  map_drop=%s'
      % (cfg['hazard_lambda_s'], cfg['sigma_s'], cfg['min_seg_s'], cfg['map_drop']))
print()

# distinct configurations, keyed on the full metric tuple
seen = {}
for r in rows:
    k = (r['count_mae'], r['micro_f1_05'], r['micro_f1_2'], r['micro_f1_5'])
    seen.setdefault(k, []).append('%s=%s' % (r['varied'], r['value']))
print('rows=%d   distinct metric tuples=%d' % (len(rows), len(seen)))
for k, labels in seen.items():
    print('  %-46s  mae=%.5f  f1@.5=%.5f  f1@2=%.5f  f1@5=%.5f'
          % (' + '.join(labels), k[0], k[1], k[2], k[3]))

print()
chosen = None
for r in rows:
    if r['varied'] == 'hazard_lambda_s' and abs(r['value'] - cfg['hazard_lambda_s']) < 1e-9:
        chosen = r
print('chosen row:', json.dumps(chosen, ensure_ascii=False))
print()

# rank among distinct tuples
uniq = [list(k) for k in seen.keys()]
print('%-10s %10s %10s %10s %10s' % ('metric', 'chosen', 'rank', 'best', 'worst'))
for idx, (name, better) in enumerate([('count_mae', 'low'), ('micro_f1_05', 'high'),
                                      ('micro_f1_2', 'high'), ('micro_f1_5', 'high')]):
    vals = [u[idx] for u in uniq]
    cv = chosen[name]
    s = sorted(vals, reverse=(better == 'high'))
    rank = s.index(cv) + 1
    print('%-10s %10.5f %10s %10.5f %10.5f  (%s better)'
          % (name, cv, '%d/%d' % (rank, len(s)), s[0], s[-1], better))

print()
print('printed in tab:p1sens: Count MAE, F1@0.5s, F1@2s')
print('NOT printed anywhere:   micro_f1_5')
print()

# sweep presence
print('--- sweep presence for min_seg_s / map_drop ---')
for f in sorted((R / 'data').glob('*.json')):
    txt = f.read_text(encoding='utf-8')
    print('  %-24s min_seg_s x%d   map_drop x%d'
          % (f.name, txt.count('min_seg_s'), txt.count('map_drop')))
print()
print('A sweep would show several values of the same key; x1 = only the chosen value.')
