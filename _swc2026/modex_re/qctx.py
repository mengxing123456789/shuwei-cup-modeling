import json,re
for fn,kws in [("artifact_context",["artifact","context","PROBLEM_FACTS","CROSS_PROBLEM_LEDGER","FIGURE_MANIFEST","manifest","dependency","graph","upstream"]),("workflow_engine",["PROBLEM_FACTS","CROSS_PROBLEM_LEDGER","FIGURE_MANIFEST"])]:
    rows=json.load(open(rf"E:\数学建模\_swc2026\modex_re\{fn}.strings.json",encoding='utf-8'))
    print("==",fn,len(rows))
    for kw in kws:
        hits=[r['s'] for r in rows if kw in r['s']]
        print("--",kw,len(hits))
        for s in hits[:8]: print(repr(s[:600]))
