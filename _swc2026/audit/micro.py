# -*- coding: utf-8 -*-
import pandas as pd, os, numpy as np, json, collections
B = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Raw_Data'
tot = nanmodel = rident = rtot = 0
dlen = collections.Counter()
for ds in ('EgoPro', 'EgoStandard'):
    for r in sorted(os.listdir(os.path.join(B, ds))):
        T = os.path.join(B, ds, r, 'tables')
        for tb in sorted(os.listdir(T)):
            if 'intrinsic' not in tb:
                continue
            d = pd.read_csv(os.path.join(T, tb), encoding='utf-8-sig')
            tot += len(d)
            nanmodel += int(d['distortion_model'].isna().sum())
            dlen.update(d['D.length'].astype(int).tolist())
            R = d[['R[0]', 'R[1]', 'R[2]', 'R[3]', 'R[4]', 'R[5]', 'R[6]', 'R[7]', 'R[8]']].to_numpy(dtype=float)
            eye = np.array([1, 0, 0, 0, 1, 0, 0, 0, 1], dtype=float)
            rident += int((np.abs(R - eye).max(axis=1) < 1e-9).sum())
            rtot += len(R)
print('intrinsic rows', tot, 'distortion_model NaN', nanmodel, 'D.length counts', dict(dlen), 'R identity %d/%d' % (rident, rtot))
v = json.load(open(r'E:\数学建模\_swc2026\audit\videos.json', encoding='utf-8'))
print('videos.json type', type(v), len(v))
if isinstance(v, list):
    print('sample', v[0])
    res = collections.Counter((x.get('width'), x.get('height')) for x in v)
    print('resolution counts', dict(res))
elif isinstance(v, dict):
    print('keys', list(v)[:5])