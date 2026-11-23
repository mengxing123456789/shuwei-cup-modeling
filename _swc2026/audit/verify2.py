# -*- coding: utf-8 -*-
import pandas as pd, os, collections
B = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN'
C = os.path.join(B, 'Restocking_Tasks_and_Constraints')
idx = pd.read_csv(os.path.join(C, 'source_segment_index.csv'), encoding='utf-8-sig')
print('duration min %.3f max %.3f' % (idx.duration_s.min(), idx.duration_s.max()))
print('start min %.3f max %.3f  end max %.3f' % (idx.start_s.min(), idx.start_s.max(), idx.end_s.max()))
print('top10 longest'); print(idx.nlargest(5, 'duration_s')[['unit_id', 'sample', 'start_s', 'end_s', 'duration_s']].to_string(index=False))
rs = pd.read_csv(os.path.join(C, 'record_split.csv'), encoding='utf-8-sig')
print('env', rs.environment_id.nunique(), 'scene', rs.scene_id.nunique(), 'op', rs.operator_id.nunique())
g = rs.groupby('operator_id').environment_id.nunique()
print('operators with >1 env:', int((g > 1).sum()), sorted(g[g > 1].index.str[:8].tolist()))
print('splits', rs.split.value_counts().to_dict())
print('split env counts', rs.groupby('split').environment_id.nunique().to_dict())
print('dataset counts', rs.dataset.value_counts().to_dict())
# header.sender check
send = collections.Counter()
for ds in ('EgoPro', 'EgoStandard'):
    for r in sorted(os.listdir(os.path.join(B, 'Raw_Data', ds))):
        t = os.path.join(B, 'Raw_Data', ds, r, 'tables', 'pose_head.csv')
        d = pd.read_csv(t, encoding='utf-8-sig', usecols=['header.sender'])
        send.update(d['header.sender'].unique().tolist())
print('header.sender values', dict(send))