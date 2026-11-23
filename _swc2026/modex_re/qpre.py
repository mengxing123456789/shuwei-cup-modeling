# -*- coding: utf-8 -*-
import json
rows=json.load(open(r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json",encoding='utf-8'))
kws=["precompile","pre-compile","编译预处理",".mh/","vision_ledger","changes.json","submission_check","writing_check","main_output_receipt","receipt","回执"]
for kw in kws:
    hits=[r['s'] for r in rows if kw in r['s']]
    print("==",kw,len(hits))
    for s in hits[:12]: print(repr(s[:500]))
