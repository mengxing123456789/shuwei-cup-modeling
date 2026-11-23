import json, os
import numpy as np
D = r'E:\数学建模\_swc2026\SWC2026_C\data'

d = json.load(open(os.path.join(D, 'pre_p2_results.json'), encoding='utf-8'))
runs = d['runs']
print('n runs =', len(runs))
print('%-4s %-4s %-10s %3s %5s %8s %8s %8s %6s %6s' % (
    'arm', 'ssl', 'seed', 'L', 'L_s', 'rmse_cm', 'end_cm', 'med_cm', 'cov80', 'pitmax'))
for r in sorted(runs, key=lambda x: (x['L'], x['arm'], str(x['ssl_task']), x['seed'])):
    print('%-4s %-4s %-10s %3d %5.1f %8.4f %8.4f %8.4f %6.3f %6.3f' % (
        r['arm'], str(r['ssl_task']), r['seed'], r['L'], r['L_s'],
        r['rmse_cm'], r['endpoint_rmse_cm'], r['median_cm'],
        r['cov80_endpoint'], r['pit_maxdev']))

print('\n--- grouped by (L, arm, ssl) mean ---')
from collections import defaultdict
g = defaultdict(list)
for r in runs:
    g[(r['L'], r['arm'], str(r['ssl_task']))].append(r)
for k in sorted(g):
    rs = g[k]
    print('L=%3d %-4s ssl=%-4s n=%d  rmse=%.4f end=%.4f med=%.4f' % (
        k[0], k[1], k[2], len(rs),
        np.mean([x['rmse_cm'] for x in rs]),
        np.mean([x['endpoint_rmse_cm'] for x in rs]),
        np.mean([x['median_cm'] for x in rs])))

print('\n--- P2 quantile (best_p2q) summary ---')
q = json.load(open(os.path.join(D, 'best_p2q.json'), encoding='utf-8'))
for row in q['rows']:
    last = row['horizons'][-1]
    print('L=%3d (%.1f s) params=%d best_ep=%d val_med_ae=%.4f  '
          'last-step rmse=%.4f med=%.4f within2cm=%.3f cov90=%.3f cov50=%.3f w90=%.2fcm' % (
              row['L_frames'], row['L_s'], row['params'], row['best_val_epoch'],
              row['val_median_ae_m'], last['rmse_m'], last['median_err_m'],
              last['within_2cm'], last['coverage90_mean'], last['coverage50_mean'],
              last['width90_mean_cm']))

print('\n--- P3 sensitivity (best_p3_sens) ---')
p = json.load(open(os.path.join(D, 'best_p3_sens.json'), encoding='utf-8'))
print('keys:', list(p.keys()))
print(json.dumps({k: v for k, v in p.items() if not isinstance(v, (list, dict))},
                 ensure_ascii=False)[:800])
for k, v in p.items():
    if isinstance(v, list):
        print(f'{k}: list n={len(v)}; first={json.dumps(v[0], ensure_ascii=False)[:300]}')
    elif isinstance(v, dict):
        print(f'{k}: dict keys={list(v.keys())[:12]}')