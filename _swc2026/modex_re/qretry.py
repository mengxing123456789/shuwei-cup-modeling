# -*- coding: utf-8 -*-
import json, re
rows=json.load(open(r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json",encoding='utf-8'))
kws=["transient_provider","unknown_process","inactivity","empty_tool","unfinished_turn","bun_panic","retry","重试","失败","错误码","error_code","RESUME","resume_"]
out=[]
seen=set()
for r in rows:
    s=r['s']
    if len(s)<6 or s in seen: continue
    if any(k in s for k in kws):
        # filter mojibake: require <=5 replacement chars or valid Chinese
        seen.add(s); out.append(s)
open(r"E:\数学建模\_swc2026\modex_re\engine_retry_strings.txt","w",encoding="utf-8").write("\n---\n".join(out))
print(len(out))
