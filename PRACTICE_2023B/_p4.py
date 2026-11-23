import json
def L(p): return json.load(open(p,encoding="utf-8"))
pt=L("data/results_perturb.json")
print("runs len",len(pt["runs"]))
for r in pt["runs"]:
    print(r.get("id"),r.get("class"),r.get("feasible"),r.get("flip"),r.get("max_rel_change"))
