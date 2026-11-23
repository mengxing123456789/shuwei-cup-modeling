import json
d = json.load(open(r'E:\数学建模\_swc2026\SWC2026_B\data\p2.json', encoding='utf-8'))
def show(o, name, depth=0):
    pad='  '*depth
    if isinstance(o, dict):
        for k,v in o.items():
            if isinstance(v,(dict,)):
                print(f'{pad}{k}:'); show(v,name,depth+1)
            elif isinstance(v,list) and v and isinstance(v[0],dict):
                print(f'{pad}{k}: list({len(v)})')
                show(v[0],name,depth+1)
            else:
                s=str(v)
                print(f'{pad}{k} = {s[:150]}')
print('#### p2_1 ####'); show(d['p2_1'],'')
print('#### p2_2 ####'); show(d.get('p2_2',{}),'')
for k in d:
    if k not in ('_meta','p2_1','p2_2'):
        print('#### ',k,' ####')
        print(json.dumps(d[k],ensure_ascii=False)[:1500])
