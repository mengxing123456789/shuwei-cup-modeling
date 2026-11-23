# -*- coding: utf-8 -*-
import os, io
base = r'C:\modex-mh-agent\resources\app\dist\assets'
out = io.open(r'E:\数学建模\_modex_re_work\skill_zh_hits.txt','w',encoding='utf-8')
for fn in os.listdir(base):
    if not fn.endswith('.js'): continue
    s = io.open(os.path.join(base,fn), encoding='utf-8', errors='ignore').read()
    idx=0
    while True:
        i=s.find('技能',idx)
        if i<0: break
        out.write(f'== {fn} @{i}\n{s[max(0,i-100):i+200]}\n')
        idx=i+2
out.close()
print('done')
