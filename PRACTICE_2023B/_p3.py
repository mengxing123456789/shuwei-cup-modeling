import json
def L(p): return json.load(open(p,encoding="utf-8"))
t=L("data/results_timing.json")
print(json.dumps(t["meta"],ensure_ascii=False,indent=1)[:1200])
for c in t["calls"]:
    print(c.get("name"),c.get("median_ms"),c.get("min_ms"),c.get("max_ms"),c.get("stdev_ms"))
