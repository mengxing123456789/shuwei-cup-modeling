import json
def L(p): return json.load(open(p,encoding="utf-8"))
pt=L("data/results_perturb.json")
print("run keys:",list(pt["runs"][0].keys()))
print(json.dumps(pt["runs"][0],ensure_ascii=False)[:800])
print("---- flip runs ----")
for r in pt["runs"]:
    if r.get("n_flips") or r.get("flips") or r.get("flipped"):
        print(json.dumps(r,ensure_ascii=False)[:900])
print("---- infeasible ----")
for r in pt["runs"]:
    if not r.get("feasible",True):
        print(json.dumps(r,ensure_ascii=False)[:600])
