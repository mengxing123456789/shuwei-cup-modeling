import json, os

D = r'E:\数学建模\_swc2026\SWC2026_C\data'
d = json.load(open(os.path.join(D, 'p3_scheduling.json'), encoding='utf-8'))
print('top keys', list(d.keys()))
s = d.get('summary')
print('summary type', type(s).__name__, 'n', len(s) if hasattr(s, '__len__') else '')
if isinstance(s, list):
    cols = sorted(set().union(*[set(e.keys()) for e in s]))
    print('summary entry keys:', cols)
    print()
    for case in ('S1', 'S2', 'S3'):
        rows = [e for e in s if e.get('case') == case]
        print('==', case, 'n=', len(rows))
        for e in rows:
            print('   %-22s eta=%.4f rev=%.2f cost=%.2f' % (
                e.get('policy'), e.get('weighted_on_time_rate', float('nan')),
                e.get('reviews', 0) or 0, e.get('cost', 0) or 0))
# constraint block
for k in ('constraint_nominal', 'constraints', 'thresholds'):
    if k in d:
        print()
        print('##', k)
        print(json.dumps(d[k], ensure_ascii=False)[:1200])