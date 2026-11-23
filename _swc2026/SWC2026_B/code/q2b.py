# -*- coding: utf-8 -*-
"""P2(2) 时间线的机器可读版（data/q2b.json）：逐车分段 + 五条不变量自检。

不变量：
  1) 每车条目按 depart 升序；
  2) arrive - depart = 走行时间（3 m/s，绕障最短路，可见图 Dijkstra）；
  3) ready = arrive + slew_s，obs_start = ready + wait_s，slew_s = max(|pan|,|tilt|)/30；
  4) 每警报 obs_start = 两车 obs_start 的较大者；
  5) reset_end = obs_end + max(回正 pan, 回正 tilt)/30。
"""
import json
import os

import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def slew_deg(pan, tilt):
    return max(abs(C.wrap180(pan)), abs(tilt)) / C.RATE


def build():
    p2 = json.load(open(os.path.join(DATA, "p2.json"), encoding="utf-8"))
    unc = p2["p2_2"]["unconstrained"]
    tl = unc["timeline"]
    alerts = {}
    out_tl = {}
    axes = {}
    err = dict(order=0.0, travel=0.0, slew=0.0, obs=0.0, reset=0.0)
    travel_offenders = []
    for v, rows in tl.items():
        out_tl[v] = []
        prev_dep = -1.0
        p_prev = C.VEH0[v]
        for e in rows:
            a = e["alert"]
            tx, ty, tz = C.target_xyz(a)
            x, y = e["station"]
            pan = C.bearing_deg((x, y), (tx, ty))
            tilt = C.elev_deg(x, y, a)
            slew = slew_deg(pan, tilt)
            reset = slew_deg(pan, tilt)
            d_est = C.travel_time(p_prev, (x, y))
            d_tl = e["arrive"] - e["depart"]
            err["order"] = max(err["order"], max(0.0, prev_dep - e["depart"]))
            err["travel"] = max(err["travel"], abs(d_est - d_tl))
            if abs(d_est - d_tl) > 1e-3:
                travel_offenders.append(dict(vehicle=v, alert=a, planned=round(float(d_tl), 6),
                                             dijkstra=round(float(d_est), 6)))
            err["slew"] = max(err["slew"], abs(slew - e["slew"]), abs(e["ready"] - (e["arrive"] + e["slew"])))
            err["obs"] = max(err["obs"], abs(e["obs_start"] - (e["ready"] + e["wait"])))
            err["reset"] = max(err["reset"], abs(reset - e["reset"]))
            prev_dep = e["depart"]
            p_prev = (x, y)
            out_tl[v].append(dict(to_alert=a, station=[round(float(x), 3), round(float(y), 3)],
                                  depart=round(float(e["depart"]), 6), arrive=round(float(e["arrive"]), 6),
                                  slew_s=round(float(e["slew"]), 6), ready=round(float(e["ready"]), 6),
                                  wait_s=round(float(e["wait"]), 6), obs_start=round(float(e["obs_start"]), 6),
                                  obs_end=round(float(e["obs_end"]), 6),
                                  reset_end=round(float(e["obs_end"] + e["reset"]), 6)))
            axes["%s->%s" % (v, a)] = dict(pan=round(float(pan), 3), tilt=round(float(tilt), 3),
                                           slew_s=round(float(slew), 6))
    veh_of = {}
    for v, rows in tl.items():
        for e in rows:
            veh_of.setdefault(e["alert"], []).append((v, e["obs_start"]))
    obs_err = 0.0
    for a, lst in veh_of.items():
        lst.sort(key=lambda z: z[1])
        alerts[a] = dict(obs_start=round(float(lst[-1][1]), 6), vehicles=[lst[0][0], lst[-1][0]],
                         wait_vehicle=lst[0][0], wait_s=round(float(lst[-1][1] - lst[0][1]), 6))
        obs_err = max(obs_err, max(abs(t - lst[-1][1]) for _, t in lst))
    err["obs"] = max(err["obs"], obs_err)
    res = dict(script="q2b.py", source="data/p2.json:p2_2.unconstrained",
               makespan=round(float(unc["makespan"]), 6),
               alerts=alerts, timeline=out_tl, slew_axis_deg=axes,
               invariant_max_err={k: float("%.3g" % v) for k, v in err.items()},
               invariant_tol=1e-3, all_ok=bool(max(err.values()) <= 1e-3),
               travel_offenders=travel_offenders[:8], n_travel_offenders=len(travel_offenders),
               note="wait_s>0 的车先到先等；obs_start=ready+wait_s；两车同刻开始")
    return res


if __name__ == "__main__":
    out = build()
    C.dump("q2b.json", out)
    print("[OK] q2b -> data/q2b.json  all_ok=%s  makespan=%.4f" % (out["all_ok"], out["makespan"]))
    print("  err", out["invariant_max_err"], "n_travel_offenders", out["n_travel_offenders"])
