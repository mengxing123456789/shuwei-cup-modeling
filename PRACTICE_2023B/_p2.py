import json
def L(p): return json.load(open(p,encoding="utf-8"))
pt=L("data/results_perturb.json")
print("meta:",json.dumps(pt["meta"],ensure_ascii=False,indent=1)[:1500])
print("runs keys:",list(pt["runs"].keys())[:50])
b=L("data/results_binding.json")
for s in b["sources"]:
    print("SRC",s.get("id"),s.get("binding"))
