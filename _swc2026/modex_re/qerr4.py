# -*- coding: utf-8 -*-
import json
p=r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json"
d=json.load(open(p,encoding="utf-8"))
with open(r"E:\数学建模\_swc2026\modex_re\qsample.txt","w",encoding="utf-8") as f:
    for x in d[:10]: f.write(repr(x)[:1000]+"\n")
    for x in d:
        if isinstance(x,str) and "resume" in x.lower(): f.write("RESUME:"+x[:500]+"\n"); break
print("done", type(d[0]))
