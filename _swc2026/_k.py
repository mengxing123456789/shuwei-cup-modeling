import json
d=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\data\p3_decline.json",encoding="utf-8"))
print(json.dumps(d["cv"][0],ensure_ascii=False)[:900])
print(json.dumps(d["split_audit"]["folds"][0],ensure_ascii=False)[:600])
print(json.dumps(d["data_facts"],ensure_ascii=False)[:400])
