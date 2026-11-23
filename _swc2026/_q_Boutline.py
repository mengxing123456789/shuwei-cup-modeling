import json
def outline(o, pre='', depth=0, maxdepth=2):
    pad = '  ' * depth
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, dict):
                print(f'{pad}{k}: dict({len(v)}) ' + ','.join(list(v)[:8]))
                if depth < maxdepth: outline(v, pre + k + '.', depth + 1, maxdepth)
            elif isinstance(v, list):
                print(f'{pad}{k}: list({len(v)})' + (f' first={str(v[0])[:80]}' if v else ''))
            else:
                print(f'{pad}{k} = {v}')
    elif isinstance(o, list):
        print(f'{pad}list({len(o)})')
for name in ['p1', 'p2', 'p3']:
    p = rf'E:\数学建模\_swc2026\SWC2026_B\data\{name}.json'
    print('=' * 20, name, '=' * 20)
    outline(json.load(open(p, encoding='utf-8')))
