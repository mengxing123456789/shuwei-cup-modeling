import json, os
D = r'E:\数学建模\_swc2026\SWC2026_C\data'


def peek(name, depth=2, width=1400):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        print(f'--- {name}: MISSING ---')
        return
    d = json.load(open(p, encoding='utf-8'))
    print(f'=== {name} ({os.path.getsize(p)} B) ===')
    print('top keys:', list(d.keys())[:20])


def dump(obj, indent=0, maxlen=1200):
    s = json.dumps(obj, ensure_ascii=False, indent=1)
    print(s[:maxlen])


peek('pre_p2_results.json')
d = json.load(open(os.path.join(D, 'pre_p2_results.json'), encoding='utf-8'))
print(json.dumps(d, ensure_ascii=False, indent=1)[:3000])
print('\n\n')
peek('best_p2q.json')
d2 = json.load(open(os.path.join(D, 'best_p2q.json'), encoding='utf-8'))
print('keys:', list(d2.keys())[:20])
for k in d2:
    if isinstance(d2[k], (int, float, str)):
        print(f'  {k} = {d2[k]}')
print(json.dumps({k: d2[k] for k in list(d2)[:6]}, ensure_ascii=False, indent=1)[:2000])