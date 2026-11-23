import json, os
D = r'E:\数学建模\_swc2026\SWC2026_C\data'

p = json.load(open(os.path.join(D, 'best_p3_sens.json'), encoding='utf-8'))
print('=== best_p3_sens ===')
print('_meta:', json.dumps(p['_meta'], ensure_ascii=False, indent=1)[:1800])
print('\nbaseline_summary:', json.dumps(p['baseline_summary'], ensure_ascii=False)[:600])
print('\nselected:', p['selected'])
print('selected_summary:', json.dumps(p['selected_summary'], ensure_ascii=False)[:600])
print('paired_vs_default:', json.dumps(p['paired_vs_default'], ensure_ascii=False)[:900])

print('\n=== sensitivity table (tag, S2, S3) ===')
rows = []
for s in p['sensitivity']:
    rows.append((s['tag'], s['summary']['S2']['mean'], s['summary']['S3']['mean']))
for tag, a, b in sorted(rows, key=lambda x: -(x[1] + x[2])):
    print(f'  {tag:28s} S2={a:.4f} S3={b:.4f} sum={a+b:.4f}')

print('\n=== p3_adaptive ===')
a = json.load(open(os.path.join(D, 'p3_adaptive.json'), encoding='utf-8'))
print('keys:', list(a.keys()))
print(json.dumps(a.get('_meta', {}), ensure_ascii=False, indent=1)[:1200])
for k, v in a.items():
    if k == '_meta':
        continue
    if isinstance(v, dict):
        print(f'\n-- {k} --')
        print(json.dumps(v, ensure_ascii=False, indent=1)[:1200])
    elif isinstance(v, list):
        print(f'\n-- {k}: list n={len(v)} --')
        print(json.dumps(v[:3], ensure_ascii=False, indent=1)[:900])