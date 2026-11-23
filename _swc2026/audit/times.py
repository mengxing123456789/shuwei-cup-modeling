# -*- coding: utf-8 -*-
import os, json, collections, numpy as np, pandas as pd
BASE = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Raw_Data'
OUT = r'E:\数学建模\_swc2026\audit'
L = []

def nz(a):
    a = np.asarray(a, dtype='float64')
    d = np.diff(a)
    return dict(n=len(a), first=float(a[0]), last=float(a[-1]), span=float(a[-1] - a[0]),
                dmin=float(d.min()), dmed=float(np.median(d)), dmax=float(d.max()),
                dmean=float(d.mean()), nuniq=int(len(np.unique(np.round(d, 6)))))

# ---------- EgoDemo per record ----------
L.append('===== EgoDemo per-record info =====')
L.append('rec  fps  total_frames  nfeatures  wrist  head_vid_res  dur_s(info)')
demo = os.path.join(BASE, 'EgoDemo')
for r in sorted(os.listdir(demo)):
    j = json.load(open(os.path.join(demo, r, 'meta', 'info.json'), encoding='utf-8'))
    feats = j['features']
    wrist = 'observation.images.left_wrist' in feats
    res = ''
    if 'observation.images.head_left' in feats:
        res = '%dx%d' % (feats['observation.images.head_left']['shape'][1], feats['observation.images.head_left']['shape'][0])
    dur = j['total_frames'] / j['fps'] if j['fps'] else 0
    L.append('%s %5.1f %7d %4d %5s %12s %.2f' % (r, j['fps'], j['total_frames'], len(feats), wrist, res, dur))

# timestamp from parquet
L.append('')
L.append('===== EgoDemo timestamp column (parquet data file) =====')
import pyarrow.parquet as pq
for r in ('E001', 'E003', 'E007'):
    t = pq.read_table(os.path.join(demo, r, 'data', 'chunk-000', 'file-000.parquet'), columns=['timestamp', 'frame_index', 'episode_index', 'index', 'task_index']).to_pandas()
    L.append('-- %s' % r)
    L.append('   timestamp %s' % nz(t['timestamp'].values))
    L.append('   frame_index %s' % nz(t['frame_index'].values))
    L.append('   episode_index uniq=%s index %s task_index uniq=%s' % (t['episode_index'].unique().tolist(), nz(t['index'].values), t['task_index'].unique().tolist()))

# ---------- EgoPro / EgoStandard time base ----------
def probe(ds, r):
    d = os.path.join(BASE, ds, r)
    L.append('')
    L.append('===== %s / %s =====' % (ds, r))
    for rel in ('tables/pose_head.csv', 'tables/pose_left_hand.csv', 'tables/sensor_camera_head_left_intrinsic.csv',
                'videos/head_left_frames.csv', 'tables/annotation_semantic_segments.csv'):
        p = os.path.join(d, rel.replace('/', os.sep))
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p, encoding='utf-8-sig')
        L.append('-- %s rows=%d cols=%d' % (rel, len(df), len(df.columns)))
        for c in ('_log_time_ns', '_publish_time_ns', '_sequence', '_offset_from_first_log_s', 'header.ts', 'header.count', 'timestamp', 'video_timestamp_ns'):
            if c in df.columns:
                s = df[c].values
                if pd.api.types.is_numeric_dtype(df[c]):
                    L.append('   %-22s dtype=%-8s %s' % (c, df[c].dtype, nz(s)))
                else:
                    L.append('   %-22s dtype=%s uniq=%s' % (c, df[c].dtype, df[c].unique()[:5]))
        # quaternion norm of first transform
        qc = [c for c in df.columns if c.endswith('.quat.w')]
        if qc:
            i = qc[0][:qc[0].index('.quat.w')]
            q = df[[i + '.quat.w', i + '.quat.x', i + '.quat.y', i + '.quat.z']].values
            L.append('   quat norm[0]: min=%.6f max=%.6f mean=%.6f' % (np.linalg.norm(q, axis=1).min(), np.linalg.norm(q, axis=1).max(), np.linalg.norm(q, axis=1).mean()))
            ps = df[[i + '.pos.x', i + '.pos.y', i + '.pos.z']].values
            L.append('   pos[0] xyz range: x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]' % (ps[:, 0].min(), ps[:, 0].max(), ps[:, 1].min(), ps[:, 1].max(), ps[:, 2].min(), ps[:, 2].max()))
        if 'transforms.length' in df.columns:
            L.append('   transforms.length uniq=%s' % df['transforms.length'].unique()[:5])
        if 'width' in df.columns and 'height' in df.columns and 'K[0]' in df.columns:
            L.append('   intrinsic: W=%s H=%s fx=%s fy=%s cx=%s cy=%s distortion_model=%s frame_id=%s' % (
                df['width'].unique()[:3], df['height'].unique()[:3], df['K[0]'].unique()[:3], df['K[4]'].unique()[:3],
                df['K[2]'].unique()[:3], df['K[5]'].unique()[:3], df['distortion_model'].unique()[:3], df['frame_id'].unique()[:3]))
        if 'segment.start_time' in df.columns:
            L.append('   segments: start=%s end=%s' % (df['segment.start_time'].tolist()[:6], df['segment.end_time'].tolist()[:6]))

probe('EgoPro', '291aff24-8b62-4a5e-b470-85114bdf86dc')
probe('EgoStandard', '01e98c50-1164-448f-a7ff-b722d7a1c19b')

# ---------- session_metadata ----------
L.append('')
L.append('===== session_metadata.csv (EgoPro 1 + EgoStandard 1) FULL =====')
for ds, r in (('EgoPro', '291aff24-8b62-4a5e-b470-85114bdf86dc'), ('EgoStandard', '01e98c50-1164-448f-a7ff-b722d7a1c19b')):
    p = os.path.join(BASE, ds, r, 'session_metadata.csv')
    df = pd.read_csv(p, encoding='utf-8-sig')
    L.append('-- %s / %s : rows=%d' % (ds, r, len(df)))
    for _, row in df.iterrows():
        L.append('   %-34s | %-40s | %s' % (row['field'], str(row['value'])[:40], row['value_type']))

open(os.path.join(OUT, 'times.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))