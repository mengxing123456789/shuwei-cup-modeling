import json
D=r"E:\数学建模\_swc2026\SWC2026_A\data"
e=json.load(open(D+r"\p4_econ.json",encoding="utf-8"))
print("== pareto_meta ==")
for k,v in e["pareto_meta"].items():
    print(k, list(v.keys()), v.get("n_front"))
    kn=v.get("knee")
    if kn: print("   knee:", {x:(round(kn[x],2) if isinstance(kn[x],float) else kn[x]) for x in ["ts","cn","Vinj","EUR_m3","cost_nom","npv"]})
print("== opt_ts ==")
for k,v in e["optimum_ts"].items(): print(k, v["ts_grid"], round(v["npv_max"]/1e4,2), round(v["ts_closed"],2), v["band_2pct"])
print("== V0 ==", json.dumps(e["V0"],ensure_ascii=False))
s=json.load(open(D+r"\p5_sobol.json",encoding="utf-8"))
for c in ["Case1","Case2","Case3"]:
    for key in ["npv","ts"]:
        S=s["sobol"][c][key]["S1"]; print(c,key,[(a,round(b,3)) for a,b in sorted(S.items(),key=lambda x:-x[1])[:4]],"sum",round(sum(S.values()),3))
