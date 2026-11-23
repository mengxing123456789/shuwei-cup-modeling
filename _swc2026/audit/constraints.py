# -*- coding: utf-8 -*-
import os, json, pandas as pd, collections
D = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints'
OUT = r'E:\数学建模\_swc2026\audit'
L = []
for fn in ('tasks.csv', 'job_families.csv', 'service_zones.csv'):
    p = os.path.join(D, fn)
    df = pd.read_csv(p, encoding='utf-8-sig')
    L.append('===== %s : rows=%d cols=%d =====' % (fn, len(df), len(df.columns)))
    L.append('columns: %s' % list(df.columns))
    with pd.option_context('display.max_rows', 300, 'display.max_columns', 50, 'display.width', 250, 'display.max_colwidth', 120):
        L.append(df.to_string(index=True))
    L.append('')

p = os.path.join(D, 'common_conditions.json')
j = json.load(open(p, encoding='utf-8'))
L.append('===== common_conditions.json FULL =====')
L.append(json.dumps(j, ensure_ascii=False, indent=1))
L.append('')

for fn in ('record_split.csv', 'source_segment_index.csv'):
    p = os.path.join(D, fn)
    df = pd.read_csv(p, encoding='utf-8-sig')
    L.append('===== %s : rows=%d cols=%d =====' % (fn, len(df), len(df.columns)))
    L.append('columns: %s' % list(df.columns))
    L.append('dtypes: %s' % dict(df.dtypes.astype(str)))
    L.append('head(3):')
    L.append(df.head(3).to_string())
    L.append('null counts: %s' % df.isna().sum().to_dict())
    for c in df.columns:
        u = df[c].nunique(dropna=True)
        if u <= 15:
            vc = df[c].value_counts(dropna=False)
            L.append('  values[%s] uniq=%d : %s' % (c, u, dict(vc)))
        else:
            L.append('  values[%s] uniq=%d : sample=%s' % (c, u, df[c].dropna().unique()[:6].tolist()))
    L.append('')

open(os.path.join(OUT, 'constraints.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(L))