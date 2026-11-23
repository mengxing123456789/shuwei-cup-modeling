"""Add the scalar aggregates the paper cites to data/p2_official.json.

`fill_numbers.resolve()` supports list indexing and `@k=v` filtering but no
aggregates, so the min/max are written here as scalars instead of being asked for
in a slot path.
"""
import io
import json
import os

DATA = r'E:\数学建模\_swc2026\SWC2026_C\data'
p = os.path.join(DATA, 'p2_official.json')
d = json.load(io.open(p, encoding='utf-8'))

g = d['derived']['prefix_gain_cm_by_lead']
pen = d['derived']['delay_penalty_cm_by_ctx']
d['derived']['prefix_gain_max_cm'] = round(max(g.values()), 3)
d['derived']['prefix_gain_min_cm'] = round(min(g.values()), 3)
d['derived']['delay_penalty_min_cm'] = round(min(pen.values()), 3)
d['derived']['delay_penalty_max_cm'] = round(max(pen.values()), 3)
json.dump(d, io.open(p, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
print('prefix gain', d['derived']['prefix_gain_min_cm'], '..', d['derived']['prefix_gain_max_cm'])
print('delay penalty', d['derived']['delay_penalty_min_cm'], '..', d['derived']['delay_penalty_max_cm'])

# repoint the three aggregate slots at the new scalar keys
fp = r'E:\数学建模\_swc2026\SWC2026_C\code\fill_numbers.py'
s = io.open(fp, encoding='utf-8').read()
for name, path in (('PDelayPenaltyMin', '["derived", "delay_penalty_min_cm"]'),
                   ('PDelayPenaltyMax', '["derived", "delay_penalty_max_cm"]'),
                   ('PPrefixGainMax', '["derived", "prefix_gain_max_cm"]')):
    import re
    pat = re.compile(r'add\("%s", "p2_official", \[[^\]]*\], "[a-z0-9]+"\)' % name)
    assert pat.search(s), name
    s = pat.sub('add("%s", "p2_official", %s, "f2")' % (name, path), s)
io.open(fp, 'w', encoding='utf-8', newline='\n').write(s)
print('slots repointed')