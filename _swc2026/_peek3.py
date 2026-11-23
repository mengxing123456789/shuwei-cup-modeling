import json, os
D = r'E:\数学建模\_swc2026\SWC2026_C\data'
d = json.load(open(os.path.join(D, 'best_p1a.json'), encoding='utf-8'))
M = d['methods']
print('%-8s %s' % ('rec', ' '.join('%-22s' % k for k in M)))
for rec in M['ward_base']['records']:
    row = []
    for k in M:
        r = M[k]['records'][rec]
        row.append('%5.3f ari k%-2d n%d' % (r['ari'], r.get('n_seg', -1), r.get('b_count_err', -1)))
    print('%-8s %s' % (rec, ' '.join(row)))
print()
for k in M:
    print('%-14s mean_ari=%.4f  std=%.4f  mean_f1=%.4f' % (
        k, M[k]['mean']['ari'] if isinstance(M[k]['mean'], dict) else M[k]['mean'],
        0, 0))
print()
print('mean blocks:')
for k in ('ward_base', 'ward_k25', 'ward_ms'):
    print(k, json.dumps(M[k]['mean'], ensure_ascii=False)[:300])
print()
# n_seg chosen per record for ward_k25
print('ward_k25 n_seg per record:', {r: M['ward_k25']['records'][r]['n_seg'] for r in M['ward_k25']['records']})
print('ward_base n_seg per record:', {r: M['ward_base']['records'][r]['n_seg'] for r in M['ward_base']['records']})