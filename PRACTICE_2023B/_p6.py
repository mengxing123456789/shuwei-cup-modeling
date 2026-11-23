import json, statistics
def L(p): return json.load(open(p,encoding="utf-8"))
q1=L("data/results_q1.json"); q2=L("data/results_q2.json"); q3=L("data/results_q3.json")
q5=L("data/results_q5.json"); bd=L("data/results_boundary.json"); b=L("data/results_binding.json")
print("== q1 CS Tar mean/thr/ratio ==")
for c in ["CS","CE","LG"]:
    for p,v in q1["combos"][c]["products"].items():
        print(c,p,"first",v["first"],"last",v["last"],"d",round(v["delta_end"],3),"d%",round(v["delta_end_pct"],3),
              "span",round(v["span"],4),"mean",round(v["mean"],4),"thr",round(v["thr_trend"],4),"ratio",round(v["span_over_thr"],4),
              "trend",v["trend_significant"],"steps",v["n_step_exceed"],"/",v["n_step"])
print("== q2 meta units? ==")
print(json.dumps(q2.get("meta",{}),ensure_ascii=False)[:900])
print("== q2 CS CO / CE CH4 / LG CO spans ==")
for c,g in [("CS","CO"),("CE","CH4"),("LG","CO"),("CS","C2H4"),("CS","C4H10"),("LG","C2H6")]:
    v=q2["combos"][c]["gases"][g]
    print(c,g,"span",v["span"],"thr",v["thr_trend"],"ratio",v["span_over_thr"],"tier",v["tier"])
print("== boundary counts ==")
for c,v in bd["combos"].items():
    print(c,{k:v[k] for k in v if k.startswith("n_") or k=="max_abs_diff_on_overlap"})
print("== binding eps/A7 ==")
for s in b["sources"]:
    if s.get("id") in ("eps_rel","A7"):
        print(s["id"],json.dumps(s.get("measure"),ensure_ascii=False)[:600])
print("== q5 interval CS Tar r=0.15 ==")
print(json.dumps(q5["combos"]["CS"],ensure_ascii=False)[:600])
