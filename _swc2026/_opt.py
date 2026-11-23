import json
p=r"E:\数学建模\_swc2026\SWC2026_A\data\p4_econ.json"
d=json.load(open(p,encoding="utf-8"))
for k,v in d["optimum_ts"].items():
    if k.endswith("cn1.0") or "cn1.0" in k:
        print(k, {kk:v[kk] for kk in ["ts_grid","ts_closed","arg_closed","npv_max"]})
print("--- two calibers")
for k,v in d["optimum_two_calibers"].items():
    print(k, v.get("ts_data_grid"), v.get("ts_continuous"), v.get("d_ts"), round(v.get("npv_at_data_grid",0)/1e4,2) if v.get("npv_at_data_grid") is not None else None)
