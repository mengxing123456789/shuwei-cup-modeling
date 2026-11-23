import os, sys, json
import numpy as np
sys.path.insert(0, r'E:\数学建模\_swc2026\SWC2026_C\code')
import best_p1a_seg as B

print('split values:', B.recs.split.value_counts().to_dict())
for sp in ('train', 'val', 'test'):
    rs = [int(r) for r in B.recs[B.recs.split == sp].rec]
    kt = {}
    for r in rs:
        ii, X = B.state_matrix(r)
        y = B.true_labels(r, ii)
        y = y[y >= 0]
        if len(y) == 0:
            continue
        kt[r] = int(len(np.unique(y)))
    multi = {r: k for r, k in kt.items() if k >= 2}
    print(f'{sp}: records={len(rs)} with_labels={len(kt)} seg>=2 -> {len(multi)}')
    if kt:
        ks = sorted(kt.values())
        print(f'   Ktrue min={ks[0]} median={int(np.median(ks))} max={ks[-1]}  dist={dict((k, ks.count(k)) for k in sorted(set(ks)))}')
    if multi:
        print('   multi-seg records:', dict(sorted(multi.items())))