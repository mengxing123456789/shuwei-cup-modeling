# -*- coding: utf-8 -*-
import json, os
D = "data"
L = lambda f: json.load(open(os.path.join(D, f), encoding="utf-8"))
tm=L("results_timing.json"); q1=L("results_q1.json"); q2=L("results_q2.json")
q3=L("results_q3.json"); q5=L("results_q5.json"); bn=L("results_binding.json")
bd=L("results_boundary.json"); pt=L("results_perturb.json")
c={x["name"]:x for x in tm["calls"]}
print("=== TIMING ===")
for n in ("q1","q2","q3","q4","q5","pipeline_q1_to_q5"):
    print(n, c[n]["median_ms"], "min",c[n]["min_ms"],"max",c[n]["max_ms"],"stdev",c[n]["stdev_ms"])
wsum=sum(c[n]["median_ms"] for n in ("q1","q2","q3","q4","q5"))
print("sum5median=",round(wsum,3)," q1/pipeline=",round(100*c['q1']['median_ms']/c['pipeline_q1_to_q5']['median_ms'],4),
      " q1/sum5=",round(100*c['q1']['median_ms']/wsum,4))
print("=== Q1 Tar per combo ===")
for cs in ("CS","CE","LG"):
    p=q1["combos"][cs]["products"]["Tar"]
    print(cs,"y0",p["y"][0],"y1",p["y"][1],"yN",p["y"][-1],
          "delta_end_pct",round(p["delta_end_pct"],6),"span",round(p["span"],6),
          "mean",round(p["mean"],6),"thr_trend",round(p["thr_trend"],6),"span_over_thr",round(p["span_over_thr"],6))
print("=== Q2 gases selected ===")
for cs in ("CS","CE","LG"):
    for g,v in q2["combos"][cs]["gases"].items():
        if g in ("CH4","CO","C4H10","C2H6","H2") or abs(v["span"]-2.5)<1e-9:
            print(cs,g,"mean",round(v["mean"],6),"thr_trend",round(v["thr_trend"],6),
                  "span",round(v["span"],6),"sot",round(v["span_over_thr"],4),"tier",v["tier"],
                  "nstep",v["n_step"],"nsexc",v["n_step_exceed"])
print("=== Q3 products/gases n_exceed/n ===")
for k,v in q3["products"].items(): print("P",k,"n_exceed",v["n_exceed"],"n",v["n"],"mean_Delta",round(v["mean_Delta"],4))
for k,v in q3["gases"].items(): print("G",k,"n_exceed",v["n_exceed"],"n",v["n"])
print("=== Q5 loo_rmse_rel ===")
for cs in ("CS","CE","LG"):
    print(cs,{k:round(x,8) for k,x in q5["combos"][cs]["loo_rmse_rel"].items()})
print("=== binding A7 & eps_rel ===")
for s in bn["sources"]:
    if s["id"] in ("A7","eps_rel"):
        print(s["id"], json.dumps(s["measure"],ensure_ascii=False)[:700])
print("=== boundary stars ===")
for cs in ("CS","CE","LG"):
    print(cs,"star",bd["combos"][cs]["n_boundary_star"],"star2",bd["combos"][cs]["n_extrapolation_star2"])
print("=== perturb counts ===", pt["meta"]["counts"])
