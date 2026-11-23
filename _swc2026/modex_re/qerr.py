# -*- coding: utf-8 -*-
import json,re
p=r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json"
data=json.load(open(p,encoding="utf-8"))
if isinstance(data,dict):
    strs=[]
    for v in data.values():
        if isinstance(v,list): strs+=v
        else: strs.append(str(v))
else: strs=data
for kw in ["resume_error_code","resume_strategy","same_session","fresh_context","CHECK_UNAVAILABLE","PROTECTED","MODEL_KEY_MISSING","SKILL_","AUTO_RESUME","auto_resume"]:
    print("==",kw)
    n=0
    for s in strs:
        if kw in s and len(s)<600:
            print(repr(s)); n+=1
            if n>=12: break
