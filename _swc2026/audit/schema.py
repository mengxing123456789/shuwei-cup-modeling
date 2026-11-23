# -*- coding: utf-8 -*-
import os, json, collections, hashlib
import pyarrow.parquet as pq
ROOT = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Raw_Data\EgoDemo'
OUT = r'E:\数学建模\_swc2026\audit'
os.makedirs(OUT, exist_ok=True)
recs = sorted(os.listdir(ROOT))
L = []

def jload(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

# ---------- info.json ----------
L.append('===== meta/info.json =====')
info0 = jload(os.path.join(ROOT, recs[0], 'meta', 'info.json'))
L.append('--- FULL (E001) ---')
L.append(json.dumps(info0, ensure_ascii=False, indent=1))
same = sum(1 for r in recs if json.dumps(jload(os.path.join(ROOT, r, 'meta', 'info.json')), sort_keys=True) == json.dumps(info0, sort_keys=True))
L.append('records with identical info.json: %d/%d' % (same, len(recs)))
diffkeys = collections.Counter()
for r in recs:
    j = jload(os.path.join(ROOT, r, 'meta', 'info.json'))
    for k in set(j) | set(info0):
        if j.get(k) != info0.get(k):
            diffkeys[k] += 1
L.append('keys that differ across records: %s' % dict(diffkeys))

# ---------- stats.json structure ----------
L.append('')
L.append('===== meta/stats.json structure =====')
st = jload(os.path.join(ROOT, recs[0], 'meta', 'stats.json'))
def struct(o, depth=0, maxd=3):
    if isinstance(o, dict):
        return {k: struct(v, depth + 1, maxd) for k, v in list(o.items())[:60]}
    if isinstance(o, list):
        return ['list len=%d' % len(o)] + ([struct(o[0], depth + 1, maxd)] if o else [])
    return type(o).__name__
L.append('top keys: %s' % list(st))
L.append('one feature sample: %s' % json.dumps({k: st[k] for k in list(st)[:2]}, ensure_ascii=False)[:1500])

# ---------- parquet ----------
L.append('')
L.append('===== parquet schemas =====')
for rel in ('data/chunk-000/file-000.parquet', 'meta/episodes/chunk-000/file-000.parquet', 'meta/tasks.parquet'):
    p = os.path.join(ROOT, recs[0], rel)
    pf = pq.ParquetFile(p)
    L.append('-- %s : rows=%d cols=%d  (E001)' % (rel, pf.metadata.num_rows, pf.metadata.num_columns))
    for f in pf.schema_arrow:
        L.append('    %-34s %s' % (f.name, str(f.type)))
# row counts across records
L.append('-- data parquet num_rows per record:')
rows = {}
for r in recs:
    pf = pq.ParquetFile(os.path.join(ROOT, r, 'data', 'chunk-000', 'file-000.parquet'))
    rows[r] = pf.metadata.num_rows
L.append('%s' % rows)
L.append('total frames=%d' % sum(rows.values()))

# episodes content
ep = pq.read_table(os.path.join(ROOT, recs[0], 'meta', 'episodes', 'chunk-000', 'file-000.parquet')).to_pylist()
L.append('-- episodes rows: %s' % json.dumps(ep, ensure_ascii=False)[:1200])
tk = pq.read_table(os.path.join(ROOT, recs[0], 'meta', 'tasks.parquet')).to_pylist()
L.append('-- tasks rows: %s' % json.dumps(tk, ensure_ascii=False)[:800])

# ---------- annotation.json ----------
L.append('')
L.append('===== annotation.json =====')
for r in (recs[0], recs[2]):
    L.append('-- %s FULL --' % r)
    L.append(json.dumps(jload(os.path.join(ROOT, r, 'annotation.json')), ensure_ascii=False, indent=1)[:3000])
keyset = collections.Counter()
for r in recs:
    j = jload(os.path.join(ROOT, r, 'annotation.json'))
    keyset[tuple(sorted(j)) if isinstance(j, dict) else ('LIST', len(j))] += 1
L.append('key-shape variants: %s' % [(k, v) for k, v in keyset.items()])
# list lengths if list
for r in recs[:3]:
    j = jload(os.path.join(ROOT, r, 'annotation.json'))
    L.append('  %s type=%s len=%s' % (r, type(j).__name__, len(j) if hasattr(j, '__len__') else '-'))

# ---------- bad_frame_ratio.json ----------
L.append('')
L.append('===== bad_frame_ratio.json =====')
for r in (recs[0], recs[1], recs[2]):
    L.append('-- %s FULL --' % r)
    L.append(json.dumps(jload(os.path.join(ROOT, r, 'bad_frame_ratio.json')), ensure_ascii=False, indent=1)[:1500])
shapes = collections.Counter()
for r in recs:
    j = jload(os.path.join(ROOT, r, 'bad_frame_ratio.json'))
    shapes[json.dumps(j, sort_keys=True)[:40]] += 1
L.append('distinct prefixes: %d ; sample keys: %s' % (len(shapes), list(shapes)[:5]))

open(os.path.join(OUT, 'ego_demo_schema.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))