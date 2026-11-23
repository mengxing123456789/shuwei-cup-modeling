import json,io,sys
def L(p):
    return json.load(open(p,encoding="utf-8"))
q3=L("data/results_q3.json")
print("== q3 products ratio_CE_over_LG ==")
for p,v in q3["products"].items():
    r=v["ratio_CE_over_LG"]
    print(p,"min=%.4f max=%.4f"%(min(r),max(r)),"Delta range",round(min(v["Delta"]),3),round(max(v["Delta"]),3),"n_exceed",v["n_exceed"],"/",v["n"],"sign_changes",v["sign_changes"])
print("flips",q3["flips"])
print("== q3 gases ==")
for g,v in q3["gases"].items():
    r=v["ratio_CE_over_LG"]
    print(g,"min=%.4f max=%.4f"%(min(r),max(r)),"n_exceed",v["n_exceed"],"/",v["n"],"abs_max",round(v["abs_max"],4))
