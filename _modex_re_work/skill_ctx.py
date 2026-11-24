# -*- coding: utf-8 -*-
import re, io, glob, os
base = r'C:\modex-mh-agent\resources\app\dist\assets'
for name in ['NewWorkflow-jYGn8LmF.js','main-DVHyaWu0.js','WorkflowDetail-CMut1qsO.js','AccountStepModels-CxXXdaQ_.js']:
    p = os.path.join(base, name)
    s = io.open(p, encoding='utf-8', errors='ignore').read()
    out = io.open(r'E:\数学建模\_modex_re_work\ctx_' + name + '.txt', 'w', encoding='utf-8')
    for m in re.finditer(r'[sS]kill', s):
        a = max(0, m.start()-200); b = min(len(s), m.end()+300)
        out.write(f'--- {m.start()} ---\n{s[a:b]}\n')
    out.close()
print('ok')
