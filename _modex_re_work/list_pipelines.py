# -*- coding: utf-8 -*-
import json, collections, io
p = r'E:\数学建模\.agents\skills\paper-kit\pipelines.json'
d = json.load(open(p, encoding='utf-8'))
out = io.StringIO()
out.write(f'templates={len(d)}\n')
rows = []
for key, it in d.items():
    if not isinstance(it, dict):
        out.write(f'!! {key} -> {type(it)}\n')
        continue
    out.write(f'\n## {key}\t{it.get("name")}\tpipeline_skill={it.get("pipeline_skill")}\n')
    for s in it.get('steps', []):
        out.write(f'  {s.get("skill_name")}\t{s.get("display_name")}\tcheckpoint={s.get("has_checkpoint")}/{s.get("checkpoint_type")}\n')
        rows.append((s.get('skill_name'), s.get('display_name')))
u = collections.OrderedDict()
for sk, dn in rows:
    u.setdefault((sk, dn), 0)
    u[(sk, dn)] += 1
out.write('\n\n==== UNIQUE SKILLS ====\n')
for (sk, dn), n in sorted(u.items(), key=lambda x: (str(x[0][0]))):
    out.write(f'{sk}\t{dn}\t{n}\n')
open(r'E:\数学建模\_modex_re_work\pipelines_dump.txt', 'w', encoding='utf-8').write(out.getvalue())
print('ok', len(d), len(u))
