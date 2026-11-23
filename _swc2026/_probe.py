import json
e=json.load(open(r"E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json",encoding="utf-8"))
v=e["npv_curves"]["Case1|cn1.0"]
print(type(v), len(v))
print(json.dumps(v,ensure_ascii=False)[:400])
print(list(e["npv_curves"].keys()))
