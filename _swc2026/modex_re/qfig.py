import json
rows=json.load(open(r"E:\数学建模\_swc2026\modex_re\workflow_engine.strings.json",encoding='utf-8'))
for kw in ["paper-figure-html","paper-figure-drawio","paper-figure"]:
    hits=[r['s'] for r in rows if kw in r['s']]
    print("==",kw,len(hits))
    for s in hits[:20]: print(repr(s[:300]))
