# -*- coding: utf-8 -*-
import os, csv, collections, json, io
ROOT = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Raw_Data'
OUT = r'E:\数学建模\_swc2026\audit'
os.makedirs(OUT, exist_ok=True)

def nrows(p):
    # count newline-terminated lines, minus header
    n = 0
    last = b''
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            n += b.count(b'\n')
            last = b[-1:]
    if last not in (b'\n', b''):
        n += 1
    return max(n - 1, 0)

def header(p):
    with open(p, 'r', encoding='utf-8', newline='') as f:
        return next(csv.reader(f))

L = []
for dsname in ('EgoPro', 'EgoStandard'):
    d = os.path.join(ROOT, dsname)
    recs = sorted(os.listdir(d))
    tab = collections.defaultdict(list)
    for r in recs:
        for dp, dns, fns in os.walk(os.path.join(d, r)):
            for fn in fns:
                if fn.lower().endswith('.csv'):
                    p = os.path.join(dp, fn)
                    rel = os.path.relpath(p, os.path.join(d, r)).replace('\\', '/')
                    tab[rel].append(p)
    L.append('===== %s : %d records, %d csv files, %d table kinds =====' % (dsname, len(recs), sum(len(v) for v in tab.values()), len(tab)))
    for name in sorted(tab):
        ps = tab[name]
        hs = collections.Counter(tuple(header(p)) for p in ps)
        rc = [nrows(p) for p in ps]
        L.append('-- %s : n=%d rows[min=%d max=%d sum=%d] ncols=%s' % (name, len(ps), min(rc), max(rc), sum(rc), sorted({len(h) for h in hs})))
        for h, c in hs.most_common():
            L.append('   hdr x%d (%d cols): %s' % (c, len(h), ','.join(h)))
    L.append('')

open(os.path.join(OUT, 'csvstats.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))