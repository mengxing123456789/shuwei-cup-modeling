# -*- coding: utf-8 -*-
import io
p = r'C:\modex-mh-agent\resources\app\dist\assets\NewWorkflow-jYGn8LmF.js'
s = io.open(p, encoding='utf-8', errors='ignore').read()
for marker in ['Pt=[', 'jt=[', 'Ot=[', 'Et=[']:
    i = s.find(marker)
    print(marker, i)
    if i != -1:
        io.open(r'E:\数学建模\_modex_re_work\newflow_' + marker.replace('[','').replace('=','') + '.txt', 'w', encoding='utf-8').write(s[i:i+8000])
