# -*- coding: utf-8 -*-
"""Does any data/*.json carry a sweep of the merge threshold or the drop fraction?
main.tex:365 claims "the merge threshold and the drop fraction move it by less than
0.01" -- that number needs a product key.

Also: how many DISTINCT configurations does tab:p1sens contain? main.tex:173 says
"Eight configurations were re-run".

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\sens_sweep.py
"""
import sys, json, pathlib

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')

print('1) grep every data/*.json for merge-threshold / drop-fraction sweep keys')
for p in sorted((R / 'data').glob('*.json')):
    txt = p.read_text(encoding='utf-8')
    for kw in ('min_seg_s', 'map_drop', 'merge'):
        if kw in txt:
            n = txt.count(kw)
            print('   %-28s contains %-12s x%d' % (p.name, kw, n))
print('   (config-only occurrences are the chosen value, not a sweep)')

print()
print('2) distinct configurations in tab:p1sens')
d = json.load(open(R / 'data' / 'alt_p1.json', encoding='utf-8'))
base = (d['config']['hazard_lambda_s'], d['config']['sigma_s'])
print('   chosen config: hazard=%.1f sigma=%.2f' % base)
cfgs = []
for s in d['sensitivity']:
    if s['varied'] == 'hazard_lambda_s':
        cfgs.append((s['value'], base[1]))
    else:
        cfgs.append((base[0], s['value']))
print('   rows: %d' % len(cfgs))
print('   distinct configs: %d' % len(set(cfgs)))
for c in sorted(set(cfgs)):
    print('     hazard=%.1f sigma=%.2f' % c)

print()
print('3) where does the chosen cell rank on each metric in the JSON?')
rows = d['sensitivity']
for metric in ('count_mae', 'micro_f1_05', 'micro_f1_2', 'micro_f1_5'):
    vals = [(s['varied'], s['value'], s[metric]) for s in rows]
    # the chosen config appears twice (hazard=4 row and sigma=0.4 row); dedupe
    uniq = {}
    for varied, value, v in vals:
        key = (4.0, 0.4) if ((varied == 'hazard_lambda_s' and value == 4.0)
                             or (varied == 'sigma_s' and value == 0.4)) else (varied, value)
        uniq[key] = v
    chosen = uniq[(4.0, 0.4)]
    srt = sorted(uniq.items(), key=lambda kv: kv[1])
    rank_lo = [i + 1 for i, kv in enumerate(srt) if kv[0] == (4.0, 0.4)][0]
    rank_hi = len(srt) - rank_lo + 1
    best = srt[0] if metric == 'count_mae' else srt[-1]
    print('   %-12s chosen=%.5f  rank_from_low=%d/%d  best=%s %.5f'
          % (metric, chosen, rank_lo, len(srt), best[0], best[1]))
print()
print('   tab:p1sens (main.tex:179) prints Count MAE, F1@0.5s, F1@2s -- it omits')
print('   micro_f1_5, which exists in the JSON and where the chosen cell is NOT best.')
