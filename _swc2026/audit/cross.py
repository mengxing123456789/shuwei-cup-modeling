# -*- coding: utf-8 -*-
import os, numpy as np, pandas as pd, json, collections
BASE = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Raw_Data'
OUT = r'E:\数学建模\_swc2026\audit'
L = []

# ---- EgoDemo ranges per record ----
import pyarrow.parquet as pq
demo = os.path.join(BASE, 'EgoDemo')
L.append('===== EgoDemo: head/hand position ranges per record (meters?) =====')
L.append('rec  head_x  head_y  head_z | Lwrist_x Lwrist_y Lwrist_z | bone_len_med(m)')
for r in sorted(os.listdir(demo)):
    rows = pq.read_table(os.path.join(demo, r, 'data', 'chunk-000', 'file-000.parquet'),
                         columns=['observation.state.head_world', 'observation.state.hand_left_world']).to_pylist()
    h = np.array([row['observation.state.head_world'][0] for row in rows], dtype=float)
    hl = np.array([row['observation.state.hand_left_world'] for row in rows], dtype=float)
    d = np.linalg.norm(hl[:, 1, :] - hl[:, 0, :], axis=1)  # thumbMCP - wrist
    d = d[np.isfinite(d)]
    L.append('%s %7.2f %7.2f %7.2f | %7.2f %7.2f %7.2f | %.4f' % (
        r, h[:, 0].min(), h[:, 0].max(), h[:, 2].max(),
        hl[:, 0, 0].min(), hl[:, 0, 1].max(), hl[:, 0, 2].max(),
        np.median(d) if len(d) else -1))

# ---- EgoPro/EgoStandard: pose_head origin ranges per record ----
for ds in ('EgoPro', 'EgoStandard'):
    L.append('')
    L.append('===== %s: pose_head pos range per record =====' % ds)
    for r in sorted(os.listdir(os.path.join(BASE, ds))):
        p = os.path.join(BASE, ds, r, 'tables', 'pose_head.csv')
        df = pd.read_csv(p, encoding='utf-8-sig', usecols=['transforms[0].pos.x', 'transforms[0].pos.y', 'transforms[0].pos.z'])
        L.append('%s  x[%7.2f,%7.2f] y[%7.2f,%7.2f] z[%7.2f,%7.2f]' % (
            r[:8], df.iloc[:, 0].min(), df.iloc[:, 0].max(), df.iloc[:, 1].min(), df.iloc[:, 1].max(),
            df.iloc[:, 2].min(), df.iloc[:, 2].max()))

# ---- alignment of tables within a record ----
L.append('')
L.append('===== intra-record alignment (EgoPro first) =====')
r = sorted(os.listdir(os.path.join(BASE, 'EgoPro')))[0]
d = os.path.join(BASE, 'EgoPro', r)
base = pd.read_csv(os.path.join(d, 'videos', 'head_left_frames.csv'), encoding='utf-8-sig')
for rel in ('tables/pose_head.csv', 'tables/pose_left_hand.csv', 'tables/annotation_bad_frame_pose_hand.csv',
            'tables/sensor_camera_head_left_intrinsic.csv', 'tables/sensor_camera_head_left_extrinsic.csv'):
    df = pd.read_csv(os.path.join(d, rel.replace('/', os.sep)), encoding='utf-8-sig')
    same_len = len(df) == len(base)
    same_log = same_len and np.array_equal(df['_log_time_ns'].values, base['_log_time_ns'].values)
    same_vts = ('video_timestamp_ns' in df) and np.array_equal(df['video_timestamp_ns'].values, base['video_timestamp_ns'].values)
    L.append('  %-52s rows=%d len_eq=%s log_eq=%s vts_eq=%s' % (rel, len(df), same_len, same_log, same_vts))

# ---- headcam variance / relation ----
L.append('')
L.append('===== pose_headcam vs pose_head (same record) =====')
d = os.path.join(BASE, 'EgoPro', sorted(os.listdir(os.path.join(BASE, 'EgoPro')))[0])
for name in ('pose_head.csv', 'pose_headcam.csv', 'pose_right_eye_cam.csv'):
    df = pd.read_csv(os.path.join(d, 'tables', name), encoding='utf-8-sig', usecols=['transforms[0].pos.x', 'transforms[0].pos.y', 'transforms[0].pos.z'])
    L.append('  %-22s x[%.4f,%.4f] y[%.4f,%.4f] z[%.4f,%.4f] std=(%.4f,%.4f,%.4f)' % (
        name, df.iloc[:, 0].min(), df.iloc[:, 0].max(), df.iloc[:, 1].min(), df.iloc[:, 1].max(),
        df.iloc[:, 2].min(), df.iloc[:, 2].max(), df.iloc[:, 0].std(), df.iloc[:, 1].std(), df.iloc[:, 2].std()))

# ---- bad frame table ----
L.append('')
L.append('===== annotation_bad_frame_pose_hand.csv (EgoPro first) =====')
df = pd.read_csv(os.path.join(d, 'tables', 'annotation_bad_frame_pose_hand.csv'), encoding='utf-8-sig')
L.append('  rows=%d is_bad values=%s' % (len(df), df['is_bad'].value_counts().to_dict()))
pt = [c for c in df.columns if c.startswith('problem_type[')]
L.append('  problem_type cols=%s' % pt)
for c in pt:
    L.append('    %s: %s' % (c, df[c].value_counts(dropna=False).to_dict()))
L.append('  sample rows: %s' % df.head(3).to_dict('records'))

# ---- semantic segments sample ----
L.append('')
L.append('===== annotation_semantic_segments.csv samples =====')
for ds in ('EgoPro', 'EgoStandard'):
    for rr in sorted(os.listdir(os.path.join(BASE, ds)))[:2]:
        p = os.path.join(BASE, ds, rr, 'tables', 'annotation_semantic_segments.csv')
        s = pd.read_csv(p, encoding='utf-8-sig')
        L.append('-- %s / %s rows=%d' % (ds, rr[:8], len(s)))
        for _, row in s.head(4).iterrows():
            L.append('   t=%.1f-%.1f skill_len=%s task=%s | seg=%s' % (
                row['segment.start_time'], row['segment.end_time'], row['segment.skill.length'],
                str(row['task_description'])[:60], str(row['segment.subtask_description'])[:70]))

# ---- task name / env per record ----
L.append('')
L.append('===== per-record task / env / split =====')
rs = pd.read_csv(r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\record_split.csv', encoding='utf-8-sig')
L.append('distinct environments per split: %s' % rs.groupby('split')['environment_id'].nunique().to_dict())
L.append('distinct records per split: %s' % rs.groupby('split').size().to_dict())
L.append('operators per split: %s' % rs.groupby('split')['operator_id'].nunique().to_dict())
L.append('operators spanning >1 env: %s' % (rs.groupby('operator_id')['environment_id'].nunique() > 1).sum())
# EgoPro/EgoStandard session task names
for ds in ('EgoPro', 'EgoStandard'):
    L.append('-- %s task names' % ds)
    for rr in sorted(os.listdir(os.path.join(BASE, ds))):
        sm = pd.read_csv(os.path.join(BASE, ds, rr, 'session_metadata.csv'), encoding='utf-8-sig')
        mp = dict(zip(sm['field'], sm['value'].astype(str)))
        L.append('   %s | %s | %s | %s | %s dev' % (rr[:8], mp.get('task_info.task_name', '')[:42],
                 mp.get('task_info.environment_id', ''), mp.get('operator.collection_method.paradigm', ''),
                 mp.get('devices.length', '')))

open(os.path.join(OUT, 'cross.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))