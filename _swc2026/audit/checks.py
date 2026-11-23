# -*- coding: utf-8 -*-
import os, json, glob, collections, numpy as np, pandas as pd
ROOT = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN'
BASE = os.path.join(ROOT, 'Raw_Data')
CON = os.path.join(ROOT, 'Restocking_Tasks_and_Constraints')
OUT = r'E:\数学建模\_swc2026\audit'
L = []

# ---- 1. bad frame stats ----
L.append('===== bad-frame stats =====')
for ds in ('EgoPro', 'EgoStandard'):
    tot = bad = 0
    reasons = collections.Counter()
    per = []
    for r in sorted(os.listdir(os.path.join(BASE, ds))):
        df = pd.read_csv(os.path.join(BASE, ds, r, 'tables', 'annotation_bad_frame_pose_hand.csv'), encoding='utf-8-sig')
        tot += len(df); bad += int(df['is_bad'].sum())
        for c in [c for c in df.columns if c.startswith('problem_type[')]:
            reasons.update(df[c].dropna().astype(str).tolist())
        per.append((r[:8], len(df), int(df['is_bad'].sum())))
    L.append('%s: rows=%d is_bad=%d (%.2f%%) reasons=%s' % (ds, tot, bad, 100.0 * bad / tot, dict(reasons)))
    L.append('   per-record bad counts: %s' % per)

# EgoDemo bad frames from json
demo = os.path.join(BASE, 'EgoDemo')
tot_bad = 0; tot_frames = 0
for r in sorted(os.listdir(demo)):
    j = json.load(open(os.path.join(demo, r, 'bad_frame_ratio.json'), encoding='utf-8'))
    tot_bad += len(j['hand_bad_frame_details']); tot_frames += j['total_frames']
L.append('EgoDemo: frames=%d hand_bad_frame_details=%d (%.2f%%)' % (tot_frames, tot_bad, 100.0 * tot_bad / tot_frames))
# episodes quality fields vs json
mism = []
for r in sorted(os.listdir(demo)):
    j = json.load(open(os.path.join(demo, r, 'bad_frame_ratio.json'), encoding='utf-8'))
    ep = pd.read_parquet(os.path.join(demo, r, 'meta', 'episodes', 'chunk-000', 'file-000.parquet'))
    if int(ep['quality/hand_bad_frame_count'].iloc[0]) != len(j['hand_bad_frame_details']):
        mism.append((r, int(ep['quality/hand_bad_frame_count'].iloc[0]), len(j['hand_bad_frame_details'])))
L.append('EgoDemo quality/hand_bad_frame_count == len(json details) for all? %s ; mismatches=%s' % (not mism, mism))
# reason counts in episodes
q = collections.Counter()
for r in sorted(os.listdir(demo)):
    ep = pd.read_parquet(os.path.join(demo, r, 'meta', 'episodes', 'chunk-000', 'file-000.parquet'))
    q[ep['quality/hand_bad_reason_counts'].iloc[0]] += 1
L.append('EgoDemo quality/hand_bad_reason_counts values: %s' % dict(q))

# ---- 2. NaN / inf check on key numeric tables ----
L.append('')
L.append('===== NaN/inf scan (numeric columns) =====')
for ds in ('EgoPro', 'EgoStandard'):
    for rel in ('tables/pose_head.csv', 'tables/pose_left_hand.csv', 'tables/sensor_camera_head_left_extrinsic.csv'):
        n_nan = n_inf = n = 0
        for r in sorted(os.listdir(os.path.join(BASE, ds)))[:4]:
            df = pd.read_csv(os.path.join(BASE, ds, r, rel.replace('/', os.sep)), encoding='utf-8-sig')
            num = df.select_dtypes('number')
            n += num.size
            n_nan += int(num.isna().sum().sum())
            n_inf += int(np.isinf(num.to_numpy(dtype='float64')).sum())
        L.append('  %s %-46s cells=%d nan=%d inf=%d (4 recs)' % (ds, rel, n, n_nan, n_inf))

# ---- 3. record_split uuid join ----
L.append('')
L.append('===== record_split join check =====')
rs = pd.read_csv(os.path.join(CON, 'record_split.csv'), encoding='utf-8-sig')
uuids = {}
for r in sorted(os.listdir(demo)):
    ep = pd.read_parquet(os.path.join(demo, r, 'meta', 'episodes', 'chunk-000', 'file-000.parquet'))
    uuids[ep['episode_uuid'].iloc[0]] = ('EgoDemo', r)
for ds in ('EgoPro', 'EgoStandard'):
    for r in sorted(os.listdir(os.path.join(BASE, ds))):
        sm = pd.read_csv(os.path.join(BASE, ds, r, 'session_metadata.csv'), encoding='utf-8-sig')
        mp = dict(zip(sm['field'], sm['value'].astype(str)))
        uuids[mp['task_info.episode_uuid']] = (ds, r)
L.append('records found=%d ; split uuids=%d ; intersection=%d' % (len(uuids), len(rs), len(set(uuids) & set(rs['episode_uuid']))))
missing = set(rs['episode_uuid']) - set(uuids)
L.append('split uuids not found in records: %s' % list(missing)[:5])
# dataset label consistency
bad = [(u, uuids[u][0], d) for u, d in zip(rs['episode_uuid'], rs['dataset']) if u in uuids and uuids[u][0] != d]
L.append('dataset label mismatches: %d %s' % (len(bad), bad[:5]))
# env label consistency
badenv = []
for u, e in zip(rs['episode_uuid'], rs['environment_id']):
    if u not in uuids:
        continue
    ds, r = uuids[u]
    if ds == 'EgoDemo':
        continue
    sm = pd.read_csv(os.path.join(BASE, ds, r, 'session_metadata.csv'), encoding='utf-8-sig')
    mp = dict(zip(sm['field'], sm['value'].astype(str)))
    if mp.get('task_info.environment_id') != e:
        badenv.append((u[:8], mp.get('task_info.environment_id'), e))
L.append('env label mismatches (EgoPro/Std): %d %s' % (len(badenv), badenv[:5]))
# operator label vs session metadata
badop = []
for u, o in zip(rs['episode_uuid'], rs['operator_id']):
    if u not in uuids:
        continue
    ds, r = uuids[u]
    if ds == 'EgoDemo':
        continue
    sm = pd.read_csv(os.path.join(BASE, ds, r, 'session_metadata.csv'), encoding='utf-8-sig')
    mp = dict(zip(sm['field'], sm['value'].astype(str)))
    if mp.get('operator.operator_id') != o:
        badop.append((u[:8], mp.get('operator.operator_id'), o))
L.append('operator label mismatches (EgoPro/Std): %d %s' % (len(badop), badop[:5]))

# ---- 4. source_segment_index vs annotation ----
L.append('')
L.append('===== source_segment_index vs annotation =====')
ss = pd.read_csv(os.path.join(CON, 'source_segment_index.csv'), encoding='utf-8-sig')
L.append('eligible=0 rows:')
L.append(ss[ss['eligible'] == 0][['unit_id', 'sample', 'dataset', 'start_s', 'end_s', 'duration_s', 'exclusion_reason']].to_string(index=False))
L.append('duration range: [%.3f, %.3f] ; rows with duration<1.2: %d ; eligible=1 & duration<1.2: %d' % (
    ss['duration_s'].min(), ss['duration_s'].max(), int((ss['duration_s'] < 1.2).sum()), int(((ss['eligible'] == 1) & (ss['duration_s'] < 1.2)).sum())))
L.append('duration == end-start max abs err: %.2e' % float(np.max(np.abs(ss['duration_s'] - (ss['end_s'] - ss['start_s'])))))
# E001 compare
for sample in ('E001', 'E003'):
    sub = ss[ss['sample'] == sample].sort_values('source_segment_index')
    ann = json.load(open(os.path.join(demo, sample, 'annotation.json'), encoding='utf-8'))['subtask_annotations']
    match = len(sub) == len(ann) and all(abs(sub.iloc[i]['start_s'] - ann[i]['start_time']) < 1e-6 and abs(sub.iloc[i]['end_s'] - ann[i]['end_time']) < 1e-6 for i in range(len(ann)))
    L.append('  %s: index rows=%d annotation subtasks=%d exact_match=%s' % (sample, len(sub), len(ann), match))
# EgoPro compare first record
r0 = sorted(os.listdir(os.path.join(BASE, 'EgoPro')))[0]
sm = pd.read_csv(os.path.join(BASE, 'EgoPro', r0, 'session_metadata.csv'), encoding='utf-8-sig')
mp = dict(zip(sm['field'], sm['value'].astype(str)))
sub = ss[ss['episode_uuid'] == mp['task_info.episode_uuid']].sort_values('source_segment_index')
seg = pd.read_csv(os.path.join(BASE, 'EgoPro', r0, 'tables', 'annotation_semantic_segments.csv'), encoding='utf-8-sig')
L.append('  EgoPro %s: index rows=%d segments=%d starts_eq=%s ends_eq=%s' % (
    r0[:8], len(sub), len(seg), np.allclose(sub['start_s'].values, seg['segment.start_time'].values),
    np.allclose(sub['end_s'].values, seg['segment.end_time'].values)))
# per-dataset segment counts vs table rows
cnt = collections.Counter()
for ds in ('EgoPro', 'EgoStandard'):
    for r in sorted(os.listdir(os.path.join(BASE, ds))):
        seg = pd.read_csv(os.path.join(BASE, ds, r, 'tables', 'annotation_semantic_segments.csv'), encoding='utf-8-sig')
        cnt[(ds, len(seg))] += 1
L.append('segment-row distribution: %s' % dict(cnt))

# ---- 5. mcap / docs / manifest search ----
L.append('')
L.append('===== mcap / documentation scan =====')
allfiles = []
for dp, dns, fns in os.walk(ROOT):
    for fn in fns:
        allfiles.append(os.path.join(dp, fn))
L.append('filenames containing mcap (case-insens): %s' % [f for f in allfiles if 'mcap' in f.lower()][:5])
L.append('extensions: %s' % dict(collections.Counter(os.path.splitext(f)[1].lower() for f in allfiles)))
L.append('doc-like files (md/txt/rst/yaml/docx/pdf): %s' % [os.path.relpath(f, ROOT) for f in allfiles if os.path.splitext(f)[1].lower() in ('.md', '.txt', '.rst', '.yaml', '.yml', '.docx', '.pdf')])
L.append('names containing manifest/documentation/readme/license: %s' % [os.path.relpath(f, ROOT) for f in allfiles if any(k in os.path.basename(f).lower() for k in ('manifest', 'documentation', 'readme', 'license', 'checksum'))])
L.append('names containing experiment/missing: %s' % [os.path.relpath(f, ROOT) for f in allfiles if any(k in os.path.basename(f).lower() for k in ('experiment', 'missing'))])

# search 'mcap' string in all json/csv (first 20 files sampled? do all json + session_metadata)
hits = []
for r in sorted(os.listdir(demo))[:3]:
    for fn in ('meta/info.json', 'annotation.json', 'bad_frame_ratio.json'):
        p = os.path.join(demo, r, fn.replace('/', os.sep))
        s = open(p, encoding='utf-8', errors='ignore').read()
        if 'mcap' in s.lower():
            hits.append(p)
for ds in ('EgoPro', 'EgoStandard'):
    for r in sorted(os.listdir(os.path.join(BASE, ds)))[:2]:
        p = os.path.join(BASE, ds, r, 'session_metadata.csv')
        s = open(p, encoding='utf-8', errors='ignore').read()
        if 'mcap' in s.lower():
            hits.append(p)
L.append("'mcap' string hits in sampled json/csv: %s" % hits)

# ---- 6. video fps vs info fps ----
L.append('')
L.append('===== video fps vs declared fps =====')
vids = json.load(open(os.path.join(OUT, 'videos.json'), encoding='utf-8'))
# rebuild record attribution from path is lost; use name+dir via os.walk again
import subprocess
FF = r'C:\Users\29900\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe'
rows = []
for ds in ('EgoDemo',):
    for r in sorted(os.listdir(os.path.join(BASE, ds))):
        info = json.load(open(os.path.join(demo, r, 'meta', 'info.json'), encoding='utf-8'))
        for cam in ('head_left', 'head_right', 'left_wrist', 'right_wrist'):
            p = os.path.join(demo, r, 'videos', 'observation.images.' + cam, 'chunk-000', 'file-000.mp4')
            if os.path.exists(p):
                o = subprocess.run([FF, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=avg_frame_rate', '-of', 'csv=p=0', p], capture_output=True, text=True)
                rows.append((r, cam, info['fps'], o.stdout.strip()))
L.append('EgoDemo declared vs actual fps (only where differ by >0.001):')
for r, cam, f, a in rows:
    an = eval(a.replace('/', '/1')) if '/' in a else float(a)
    # correct parse
    num, den = a.split('/')
    an = float(num) / float(den)
    if abs(an - f) > 0.001:
        L.append('   %s %-10s declared=%.1f actual=%s (%.4f)' % (r, cam, f, a, an))
L.append('EgoPro table step 33332992-33334016 ns -> 30.00015 fps nominal')

open(os.path.join(OUT, 'gaps.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))