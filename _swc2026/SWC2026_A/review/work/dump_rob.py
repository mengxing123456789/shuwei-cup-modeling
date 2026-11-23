# -*- coding: utf-8 -*-
import json
d = json.load(open("data/p4_econ.json", encoding="utf-8"))
for c in ["Case1", "Case2", "Case3"]:
    r = d["robustness"][c]
    print("=" * 8, c, "base", r["base_ts"], "npv", round(r["base_npv"] / 1e4, 1), "span", round(r["npv_span_rel"], 4))
    for k, v in r["cases"].items():
        print(" %-9s ts=%5.1f d_ts=%+5.1f dNPV=%+9.1f changed=%s" % (k, v["ts"], v["d_ts"], v["d_npv"] / 1e4, v["changed"]))
