# -*- coding: utf-8 -*-
"""敏感性：σψ / 车速 / 俯仰上限 的 OAT + 三因子联合抽样（1000 次，固定种子）。

口径：
- σψ 只进入 P2/P4 的测角误差链，P3 的 σ(s)=0.3+0.02s 与云台零偏是另一条链，不混用；
- 车速只对"计划固定、执行变慢"重放时间线，不重解指派（重解的成本见 P2(2) 的 98 s）；
- 俯仰上限改变可观测域面积（重算 1 m 栅格）与解析半径 r_min；
- 联合抽样给 Spearman 秩相关，用 numpy 自行排序，不引入 scipy。
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

import common as C

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
SEED = 20261120
N_JOINT = 1000


def load(name):
    return json.load(open(os.path.join(DATA, name), encoding="utf-8"))


def retime(tl, v_new):
    """固定指派、按新速度重放时间线，返回 makespan。"""
    ent = {}
    for v, ms in tl.items():
        for e in ms:
            ent.setdefault(e["alert"], {})[v] = e
    order = sorted(ent, key=lambda a: min(e["obs_start"] for e in ent[a].values()))
    free = {v: 0.0 for v in tl}
    st = {}
    for a in order:
        rr = []
        for v, e in ent[a].items():
            arr = free.get(v, 0.0) + (e["arrive"] - e["depart"]) * C.SPEED / v_new
            rr.append(arr + e["slew"])
        s = max(rr)
        st[a] = s
        for v, e in ent[a].items():
            free[v] = s + C.T_OBS + e["reset"]
    return max(st.values()), st


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean()
    ry -= ry.mean()
    return float((rx * ry).sum() / math.sqrt((rx ** 2).sum() * (ry ** 2).sum()))


def area_frac(elev_max, t):
    old = C.ELEV_MAX
    C.ELEV_MAX = float(elev_max)
    try:
        obs = C.observability(t, 1.0, "3d")
        ok = obs["obs"] & obs["geom"] & obs["elev"]
        return float(ok.sum() / obs["obs"].size)
    finally:
        C.ELEV_MAX = old


def main():
    p1, p2, p3, p4 = load("p1.json"), load("p2.json"), load("p3.json"), load("p4.json")
    tl = p2["p2_2"]["unconstrained"]["timeline"]
    H = {t: C.TARGETS[t][2] for t in ("T1", "T2", "T3")}
    mk0, st0 = retime(tl, C.SPEED)

    oat_sig = []
    for s in (0.5, 0.75, 1.0, 1.5, 2.0):
        r = C.SIGMA_RAD * math.sqrt(2) * p2["p2_1"]["r_min_analytic"] * (s / 1.0)
        oat_sig.append(dict(sigma_deg=s, drms_lb_T2=round(r, 6),
                            travel1_s_at_v3=round(p2["p2_1"]["attained"]["travel1_s"] * 3.0 / C.SPEED, 4),
                            p2_drms=round(p2["p2_1"]["attained"]["drms"] * s, 6),
                            p4_drms=round(float(np.mean([x["drms_new"] for x in p4["p4"]["rows"]
                                                         if x["drms_new"]])) * s, 6),
                            d_pct=round((s - 1.0) * 100, 2)))
    oat_v = []
    for v in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
        mk, st = retime(tl, v)
        oat_v.append(dict(v=v, makespan=round(float(mk), 4), delta_s=round(float(mk - mk0), 4),
                          d_pct=round(float((mk / mk0 - 1) * 100), 3)))
    base_area = {t: area_frac(80.0, t) for t in ("T1", "T2", "T3")}
    oat_e = []
    for e in (75.0, 77.5, 80.0, 82.5, 85.0):
        row = dict(elev_max=e)
        for t in ("T1", "T2", "T3"):
            a = area_frac(e, t)
            row["area_" + t] = round(100 * a, 4)
        row["r_min_T2"] = round(float((H["T2"] - C.CAM_Z) / math.tan(math.radians(e))), 6)
        row["drms_lb_T2"] = round(float(C.SIGMA_RAD * math.sqrt(2) * row["r_min_T2"]), 6)
        row["delta_area_T1_pp"] = round(row["area_T1"] - 100 * base_area["T1"], 4)
        row["delta_area_T2_pp"] = round(row["area_T2"] - 100 * base_area["T2"], 4)
        oat_e.append(row)

    rng = np.random.default_rng(SEED)
    sg = rng.uniform(0.5, 2.0, N_JOINT)
    vv = rng.uniform(2.0, 5.0, N_JOINT)
    em = rng.uniform(75.0, 85.0, N_JOINT)
    rmin = {t: (H[t] - C.CAM_Z) / np.tan(np.radians(em)) for t in H}
    dr = {t: sg * np.pi / 180 * math.sqrt(2) * rmin[t] for t in H}
    mk = np.array([retime(tl, float(v))[0] for v in vv])
    joint = dict(n=N_JOINT, seed=SEED, ranges=dict(sigma=[0.5, 2.0], v=[2.0, 5.0], elev=[75.0, 85.0]),
                 out={})
    for nm, y in (("drms_lb_T1", dr["T1"]), ("drms_lb_T2", dr["T2"]), ("drms_lb_T3", dr["T3"]),
                  ("makespan", mk)):
        joint["out"][nm] = dict(mean=round(float(y.mean()), 5), std=round(float(y.std(ddof=1)), 5),
                                p05=round(float(np.quantile(y, 0.05)), 5),
                                p95=round(float(np.quantile(y, 0.95)), 5),
                                rho_sigma=round(spearman(sg, y), 4),
                                rho_v=round(spearman(vv, y), 4),
                                rho_elev=round(spearman(em, y), 4))
    # σ 的一阶敏感度（对数斜率）：d ln E / d ln σ
    joint["log_slope_drms_T2_vs_sigma"] = round(float(np.polyfit(np.log(sg), np.log(dr["T2"]), 1)[0]), 4)

    out = {"_meta": C.meta("sens.py")}
    sp = []
    for v in (2.0, 3.0, 5.0):
        sp.append(dict(v=v, travel_s1=round(float(p2["p2_1"]["attained"]["travel1_s"] * 3.0 / v), 4),
                      travel_s2=round(float(p2["p2_1"]["attained"]["travel2_s"] * 3.0 / v), 4),
                      drms=round(float(p2["p2_1"]["attained"]["drms"]), 6)))
    out["sens"] = dict(p2_1_speed_table=sp, baseline_makespan=round(float(mk0), 4), baseline_starts={a: round(float(s), 4) for a, s in st0.items()},
                       oat_sigma=oat_sig, oat_speed=oat_v, oat_elev=oat_e, joint=joint,
                       calibers=dict(
                           speed="固定指派重放（不改指派），makespan 只含 5 s 观测与复位 slew",
                           elev="面积按 1 m 栅格重算；elev 改变可观测域，未重解站位",
                           sigma="P2/P4 的测角链，DRMS 与 σ 严格线性（log 斜率应为 1.0）"))
    C.dump("sens.json", out)
    for r in oat_sig:
        print("SIG", r)
    for r in oat_v:
        print("V", r)
    for r in oat_e:
        print("E", r)
    print("JOINT", json.dumps(joint["out"], ensure_ascii=False))
    print("slope", joint["log_slope_drms_T2_vs_sigma"])


if __name__ == "__main__":
    main()