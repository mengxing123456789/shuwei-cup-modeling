import json,io,sys
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
p=r"E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json"
d=json.load(open(p,encoding="utf-8"))
print(list(d.keys()))
for k,v in d["pareto"].items():
    print(k, type(v), len(v)); print(v[0]); break
print("pareto_meta keys", list(d["pareto_meta"].keys())[:8])
