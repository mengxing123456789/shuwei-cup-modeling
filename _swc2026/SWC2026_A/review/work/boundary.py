# -*- coding: utf-8 -*-
"""Boundary audit for the Pareto knees: sweep each design variable at the knee."""
import json, os, sys
sys.path.insert(0, os.path.abspath("code"))
import p4_econ as P4
import mm_common as MC

D3 = json.load(open("data/p3_decline.json", encoding="utf-8"))
prm = {}
for c in MC.CASE_KEYS:
    m = D3["M5_params"][c]
    prm[c] = dict(Ainf=m["Ainf"], tau=m["tau"], p=m["p"], a=m["a"],
                  D=D3["shared_D"][c]["D"], D_sd=D3["shared_D"][c]["D_sd"])
P4.OUT["_prm"] = prm
D1 = json.load(open("data/p1_mechanistic.json", encoding="utf-8"))
V0 = {}
for c in MC.CASE_KEYS:
    Rp = D1["scaling"][c]["R_numeric_60d"]
    aface = 4.0 * MC.FRAC[c]["Lf"] * MC.FRAC[c]["hf"]
    V0[c] = dict(geo=float(MC.GEO[c]["phi0"] * aface * Rp), emp=1500.0)

D4 = json.load(open("data/p4_econ.json", encoding="utf-8"))
for cal in ("geo", "emp"):
    print("#" * 20, cal)
    for c in MC.CASE_KEYS:
        m = D4["pareto_meta"][f"{c}|{cal}"]["knee"]
        base = dict(ts=m["ts"], cn=m["cn"], Vinj=m["Vinj"], qinj=m["qinj"], fCO2=m["fCO2"])
        v0 = V0[c][cal]
        print("=" * 8, c, cal, "knee", {k: round(v, 2) for k, v in base.items()},
              "NPV_wan", round(m["npv"] / 1e4, 1))
        for name, vals in [
            ("qinj", [400, 600, 800, 1000, 1200]),
            ("Vinj", [3000, 4000, 5000, 6000, 7000, 8000]),
            ("fCO2", [0.2, 0.4, 0.6, 0.8, 0.9, 1.0]),
            ("cn", [0.25, 0.5, 0.75, 1.0, 1.25, 1.5]),
        ]:
            out = []
            for v in vals:
                kw = dict(base)
                kw[name] = v
                s = P4.scheme(c, kw["ts"], kw["cn"], kw["Vinj"], kw["qinj"], kw["fCO2"], V0=v0)
                out.append((v, round(s["npv"] / 1e4, 1), round(s["EUR_m3"], 0)))
            print(" ", name, out)
        # optimize ts along each boundary
        print("  ts-sweep boundaries:")
        for label, kw in [("qinj=1200", dict(base, qinj=1200)),
                          ("Vinj=8000", dict(base, Vinj=8000)),
                          ("fCO2=1.0", dict(base, fCO2=1.0)),
                          ("cn=0.25", dict(base, cn=0.25))]:
            best = max((P4.scheme(c, ts, kw["cn"], kw["Vinj"], kw["qinj"], kw["fCO2"], V0=v0)["npv"], ts)
                       for ts in range(5, 61))
            print("   ", label, "best ts", best[1], "NPV_wan", round(best[0] / 1e4, 1))
