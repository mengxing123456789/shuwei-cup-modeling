# -*- coding: utf-8 -*-
import os, json, collections, io, sys
ROOT = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN'
OUT = r'E:\数学建模\_swc2026\audit'
os.makedirs(OUT, exist_ok=True)

files = []
for dp, dns, fns in os.walk(ROOT):
    for fn in fns:
        p = os.path.join(dp, fn)
        rel = os.path.relpath(p, ROOT)
        try:
            sz = os.path.getsize(p)
        except OSError:
            sz = -1
        files.append((rel, sz))

def ds(rel):
    parts = rel.split(os.sep)
    return parts[1] if parts[0] == 'Raw_Data' else 'Constraints'

per = collections.defaultdict(list)
for rel, sz in files:
    per[ds(rel)].append((rel, sz))

L = []
L.append('TOTAL FILES %d  TOTAL MB %.1f' % (len(files), sum(s for _, s in files) / 1048576.0))
for k in sorted(per):
    fs = per[k]
    c = collections.Counter(os.path.splitext(r)[1].lower() for r, s in fs)
    L.append('%-12s files=%4d  MB=%9.1f  ext=%s' % (k, len(fs), sum(s for _, s in fs) / 1048576.0, dict(sorted(c.items()))))

# record sets
def rec_of(rel):
    parts = rel.split(os.sep)
    if parts[0] == 'Raw_Data' and parts[1] in ('EgoDemo', 'EgoPro', 'EgoStandard') and len(parts) > 2:
        return parts[1], parts[2]
    return None, None

recs = collections.defaultdict(set)
for rel, sz in files:
    d, r = rec_of(rel)
    if d:
        recs[d].add(r)
for d in ('EgoDemo', 'EgoPro', 'EgoStandard'):
    rs = sorted(recs[d])
    L.append('RECORDS %s n=%d  first=%s last=%s' % (d, len(rs), rs[0] if rs else '-', rs[-1] if rs else '-'))

# per-record file layout, normalized
def norm(rel, d, r):
    x = rel.split(os.sep)
    # drop root, dataset, record
    sub = x[3:]
    s = '/'.join(sub)
    s = s.replace(r, '{UUID}')
    s = s.replace('E0', 'E0')  # keep
    return s

for d in ('EgoDemo', 'EgoPro', 'EgoStandard'):
    pat = collections.Counter()
    perrec = collections.defaultdict(list)
    for rel, sz in files:
        dd, r = rec_of(rel)
        if dd != d:
            continue
        n = norm(rel, d, r)
        pat[n] += 1
        perrec[r].append(n)
    L.append('')
    L.append('=== %s layout patterns (pattern -> #files total) ===' % d)
    for p, c in sorted(pat.items()):
        L.append('  %-70s %4d' % (p, c))
    # per-record distinct counts
    cnt = collections.Counter(frozenset(v) for v in perrec.values())
    L.append('  distinct layout variants: %d' % len(cnt))
    for k, c in cnt.most_common():
        L.append('   variant x%d files=%d: %s' % (c, len(k), ' | '.join(sorted(k))[:400]))

# size distribution of largest files
L.append('')
L.append('=== top 15 largest files ===')
for rel, sz in sorted(files, key=lambda t: -t[1])[:15]:
    L.append('  %8.1f MB  %s' % (sz / 1048576.0, rel))

# list constraints dir
L.append('')
L.append('=== Constraints dir ===')
for rel, sz in sorted(per['Constraints']):
    L.append('  %10d B  %s' % (sz, rel))

# EgoDemo record dirs contents detail (first 3 + last)
for d in ('EgoDemo',):
    L.append('')
    L.append('=== %s per-record file list (first 3, all paths) ===' % d)
    for r in sorted(recs[d])[:3]:
        L.append(' -- %s' % r)
        for rel, sz in sorted(files):
            dd, rr = rec_of(rel)
            if dd == d and rr == r:
                L.append('    %10d  %s' % (sz, rel.split(os.sep, 3)[3]))

# EgoPro/EgoStandard per-record dir listing (first 2)
for d in ('EgoPro', 'EgoStandard'):
    L.append('')
    L.append('=== %s per-record listing (first 2) ===' % d)
    for r in sorted(recs[d])[:2]:
        L.append(' -- %s' % r)
        for rel, sz in sorted(files):
            dd, rr = rec_of(rel)
            if dd == d and rr == r:
                L.append('    %10d  %s' % (sz, rel.split(os.sep, 3)[3]))

open(os.path.join(OUT, 'inv.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))