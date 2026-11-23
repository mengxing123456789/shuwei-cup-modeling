# -*- coding: utf-8 -*-
"""Three claims in main.tex:365 / :150 checked against data/alt_p1.json.

(1) main.tex:365 "the hazard rate is the only parameter that matters: moving it by
    a factor of two changes F1 by 0.046"  -> which parameter actually spans 0.046?
(2) main.tex:365 "the merge threshold and the drop fraction move it by less than
    0.01"  -> is there any artefact to check this against?
(3) main.tex:150 "the record-level scores have a within-record AUC of exactly
    0.500 by construction"  -> are all record-level scores exactly 0.500?

Run:  E:\Mini\envs\mathmodel\python.exe out\_figcheck\sens_claims.py
"""
import sys, json, pathlib

sys.stdout.reconfigure(encoding='utf-8')
R = pathlib.Path(r'E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP')
d = json.load(open(R / 'data' / 'alt_p1.json', encoding='utf-8'))

print('=' * 78)
print('(1) which parameter spans F1@0.5s by 0.046 ?')
haz = [(r['value'], r['micro_f1_05']) for r in d['sensitivity'] if r['varied'] == 'hazard_lambda_s']
sig = [(r['value'], r['micro_f1_05']) for r in d['sensitivity'] if r['varied'] == 'sigma_s']
print('  hazard rows:', haz)
print('  sigma  rows:', sig)
hr = max(v for _, v in haz) - min(v for _, v in haz)
sr = max(v for _, v in sig) - min(v for _, v in sig)
print('  hazard F1@0.5s range = %.5f   (factor %.2fx across the sweep)'
      % (hr, max(k for k, _ in haz) / min(k for k, _ in haz)))
print('  sigma  F1@0.5s range = %.5f   (factor %.2fx across the sweep)'
      % (sr, max(k for k, _ in sig) / min(k for k, _ in sig)))
print('  printed claim        = 0.046')
print('  -> 0.046 matches the SIGMA range (%.5f), not the hazard range (%.5f).' % (sr, hr))
print('  -> and sigma moves F1 MORE than hazard, so "the hazard rate is the only')
print('     parameter that matters" is contradicted by this very table.')
print()
print('  factor-of-two steps inside the hazard sweep:')
for (a, fa), (b, fb) in zip(haz, haz[1:]):
    if abs(b / a - 2.0) < 1e-9:
        print('    %g -> %g  (2x): dF1 = %+.5f' % (a, b, fb - fa))
print()
print('=' * 78)
print('(2) merge threshold / drop fraction: any artefact?')
cfg = d['config']
print('  config.min_seg_s = %s   config.map_drop = %s' % (cfg['min_seg_s'], cfg['map_drop']))
found = 0
for f in sorted((R / 'data').glob('*.json')):
    txt = f.read_text(encoding='utf-8')
    n1, n2 = txt.count('min_seg_s'), txt.count('map_drop')
    if n1 or n2:
        print('  %-24s min_seg_s x%d  map_drop x%d' % (f.name, n1, n2))
        found += 1
print('  files mentioning either key: %d  (all occurrences are the single config value)' % found)
print('  -> no sweep, therefore no product key for "move it by less than 0.01".')
print()
print('=' * 78)
print('(3) within-record AUC, per method:')
wr = d['downstream_auc']['within_record']
print('  n_records=%s  n_segments=%s' % (wr.get('n_records'), wr.get('n_segments')))
for k, v in wr['mean_auc'].items():
    print('    %-26s %.7f   %s' % (k, v, 'exactly 0.500' if abs(v - 0.5) < 1e-9 else 'NOT 0.500'))
print('  main.tex:150 says "the record-level scores have a within-record AUC of')
print('  exactly 0.500 by construction" - true only for raw_record_bad_rate and')
print('  official_eligible_flag; record_posterior_bound is 0.5648.')
