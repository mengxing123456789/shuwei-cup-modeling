# -*- coding: utf-8 -*-
import json
d=json.load(open(r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json",encoding="utf-8"))
out=[]
for e in d:
    s=e.get("s","")
    low=s.lower()
    if any(k in low for k in ("resume","auto_resume","error_code","same_session","fresh_context")):
        if len(s)<900: out.append(f'[{e.get("sec")}@{e.get("off")}] {s}')
open(r"E:\数学建模\_swc2026\modex_re\qresume.txt","w",encoding="utf-8").write("\n---\n".join(out))
print(len(out))
