import json, os

D = r'E:\数学建模\_swc2026\SWC2026_C\data'
d = json.load(open(os.path.join(D, 'best_p1a.json'), encoding='utf-8'))
print('meta:', json.dumps(d['_meta'], ensure_ascii=False)[:1400])
print()
print('deltas vs baseline:')
for k, v in d['delta_ari_vs_baseline'].items():
    print('   %-14s %s' % (k, v))
print()
for name, m in d['methods'].items():
    if isinstance(m, dict):
        small = {k: (round(v, 4) if isinstance(v, float) else v)
                 for k, v in m.items() if k in
                 ('ari', 'f1', 'k', 'n_states', 'silhouette', 'db', 'best_ari', 'best_f1', 'seconds',
                  'median_ari', 'ari_mean', 'note', 'status', 'error')}
        print('%-14s %s' % (name, json.dumps(small, ensure_ascii=False)[:600]))
        rest = [k for k in m if k not in small]
        if rest:
            print('      other keys:', rest)
    else:
        print(name, m)
print()
b = json.load(open(os.path.join(D, 'best_p1b.json'), encoding='utf-8'))
print('p1b meta:', json.dumps(b['_meta'], ensure_ascii=False)[:700])
print()
for name, a in b.get('arms', {}).items():
    if isinstance(a, dict):
        keys = list(a.keys())
        print('== arm', name, 'keys', keys[:12])
        for k in ('test', 'best', 'result', 'metrics', 'final'):
            if k in a:
                print('  ', k, json.dumps(a[k], ensure_ascii=False)[:700])
print()
print('paired:', json.dumps(b.get('paired_bootstrap', {}), ensure_ascii=False)[:900])