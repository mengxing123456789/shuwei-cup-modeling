# -*- coding: utf-8 -*-
import json
p=r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json"
d=json.load(open(p,encoding="utf-8"))
out=[]
for s in d:
    if not isinstance(s,str): continue
    low=s.lower()
    if any(k in low for k in ("resume","auto_resume","error_code","same_session","fresh_context")):
        if len(s)<800: out.append(s)
open(r"E:\数学建模\_swc2026\modex_re\qresume.txt","w",encoding="utf-8").write("\n---\n".join(out))
print(len(out))
