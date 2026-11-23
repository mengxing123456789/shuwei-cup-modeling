import json, os

D = r'E:\数学建模\_swc2026\SWC2026_C\data'


def peek(fn, maxdepth=2):
    p = os.path.join(D, fn)
    if not os.path.exists(p):
        print(fn, 'MISSING')
        return None
    d = json.load(open(p, encoding='utf-8'))
    print('==', fn, os.path.getsize(p), 'B')
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                print('  ', k, '{', ', '.join(list(v.keys())[:10]), '}')
            elif isinstance(v, list):
                print('  ', k, '[list n=%d]' % len(v), str(v[0])[:200] if v else '')
            else:
                print('  ', k, '=', str(v)[:160])
    return d


for f in ('best_p1a.json', 'pre_p2_ssl.json', 'best_p1b.json'):
    peek(f)
    print()

# p1a details
d = json.load(open(os.path.join(D, 'best_p1a.json'), encoding='utf-8'))
for k in ('baselines', 'candidates', 'selected', 'best', 'reference'):
    if isinstance(d, dict) and k in d:
        print('## p1a', k)
        print(json.dumps(d[k], ensure_ascii=False)[:1500])
        print()