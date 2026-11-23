# -*- coding: utf-8 -*-
"""
p6_checks.py —— 工程可行性核验（回应第三方检查清单「分别报告压力越界、材料消耗超标、
注入+焖井超 90 天的比例」）。

口径约定（必须与 p1/p4 一致）：
  Π9 = kΔp/(μ q/A_face)，q 取 Table A.3 的参考注入速率 q_ref = 300 m³/d（mm_common.REF）
  q_allow = Π9 · q_ref  = 在该压差下地层能接受的最大排量；q_allow < 800 即「压力越界」

输出 data/p6_checks.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mm_common as MC
import p4_econ as P4

E = MC.ECON

M_NANO_CAP = 30.0        # t/井
T_WINDOW = 90.0          # d
Q_DESIGN = 800.0         # P4 精确前沿所用 qinj（设备上限）
Q_REF = 300.0            # Table A.3 参考注入速率，Π9 的估值点

CASES = ["Case1", "Case2", "Case3"]
# Π9 由 p1_mechanistic 在 q_ref=300 处算出（见 data/p1_mechanistic.json / tab_pi.tex）
PI9 = {"Case1": 0.2274, "Case2": 1.6370, "Case3": 12.7300}


def main():
    out = {"_meta": {"script": "p6_checks.py",
                     "purpose": "工程可行性核验：约束越界比例 + 注入能力上限 + 限流后的 NPV 代价",
                     "q_design": Q_DESIGN, "q_ref_pi9": Q_REF}}

    # ---------- 1) 单情景全网格（与 p4_econ.front_grid 同口径） ----------
    def enum_case():
        for ts in range(5, 61):
            for Vinj in range(1000, 5001, 100):
                for cn in (0.5, 1.0, 1.5):
                    for fCO2 in (0.2, 0.5, 0.8):
                        yield dict(ts=float(ts), Vinj=float(Vinj), cn=float(cn), fCO2=float(fCO2))

    grid = list(enum_case())
    n = len(grid)

    def m_nano(g):
        return (g["cn"] / 100.0) * 1000.0 * (g["Vinj"] * (1.0 - g["fCO2"])) / 1000.0

    def tinj(g):
        return g["Vinj"] / Q_DESIGN

    v_nano = sum(1 for g in grid if m_nano(g) > M_NANO_CAP)
    v_time = sum(1 for g in grid if tinj(g) + g["ts"] > T_WINDOW)
    v_ok = sum(1 for g in grid if (m_nano(g) <= M_NANO_CAP and tinj(g) + g["ts"] <= T_WINDOW))

    out["grid"] = dict(n_per_case=n, cases=CASES,
                       ts_range=[5, 60], Vinj_range=[1000, 5000, 100],
                       cn_levels=[0.5, 1.0, 1.5], fCO2_levels=[0.2, 0.5, 0.8],
                       qinj=Q_DESIGN)
    out["m_nano_t"] = dict(min=min(m_nano(g) for g in grid),
                           max=max(m_nano(g) for g in grid),
                           median=sorted(m_nano(g) for g in grid)[n // 2])
    out["tinj_d"] = dict(max=max(tinj(g) for g in grid))
    out["ratios"] = {"m_nano_over_30t": v_nano / n,
                     "tinj_plus_ts_over_90d": v_time / n,
                     "pass_material_and_time": v_ok / n}
    out["counts"] = {"m_nano_over": v_nano, "time_over": v_time,
                     "pass_material_and_time": v_ok, "n": n}
    out["bind"] = {"m_nano": "binding" if 0 < v_nano < n else ("never" if v_nano == 0 else "always"),
                   "time_window": "binding" if 0 < v_time < n else ("never" if v_time == 0 else "always"),
                   "note": "比例 0 = 该约束在设计域内恒不紧；1 = 恒不满足（设计域为空）"}

    # ---------- 2) 注入能力上限（压力是否越界） ----------
    cap = {}
    for c in CASES:
        q_allow = PI9[c] * Q_REF
        cap[c] = dict(Pi9=PI9[c], q_ref=Q_REF, q_allow_m3d=q_allow,
                      feasible_at_800=bool(q_allow >= Q_DESIGN),
                      shortfall_factor=Q_DESIGN / q_allow,
                      note="Π9<1 表示该压差下地层接受不了 imposed 排量，需要更高的井底压力 → 压力越界")
    out["qinj_capacity"] = cap

    # ---------- 3) 限流后的经济代价（两套口径分别算） ----------
    # 口径 A「曲线口径」= p4_econ 的 NPV(ts) 曲线：Vinj=3000, qinj=300, fCO2=0.5（论文 §5.4 表与图用这个）
    # 口径 B「前沿口径」= p4_econ 的精确前沿：Vinj 可变, qinj=800（设备上限）
    prm_all = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "data", "p4_econ.json"), encoding="utf-8"))["_prm"]
    plan = {"Case1": dict(ts=10.0, cn=1.0, Vinj=3000.0),
            "Case2": dict(ts=23.0, cn=1.0, Vinj=3000.0),
            "Case3": dict(ts=35.0, cn=1.0, Vinj=3000.0)}
    cost = {}
    for c in CASES:
        prm = prm_all[c]
        q_allow = cap[c]["q_allow_m3d"]

        # 口径 A
        baseA = P4.scheme(c, ts=plan[c]["ts"], cn=plan[c]["cn"], Vinj=plan[c]["Vinj"],
                          qinj=Q_REF, fCO2=0.5, prm=prm)
        qA = min(q_allow, Q_REF)
        limA = P4.scheme(c, ts=plan[c]["ts"], cn=plan[c]["cn"], Vinj=plan[c]["Vinj"],
                         qinj=qA, fCO2=0.5, prm=prm)

        # 口径 B
        baseB = P4.scheme(c, ts=plan[c]["ts"], cn=plan[c]["cn"], Vinj=plan[c]["Vinj"],
                          qinj=Q_DESIGN, fCO2=0.5, prm=prm)
        qB = min(q_allow, Q_DESIGN)
        limB = P4.scheme(c, ts=plan[c]["ts"], cn=plan[c]["cn"], Vinj=plan[c]["Vinj"],
                         qinj=qB, fCO2=0.5, prm=prm)

        cost[c] = dict(
            plan=plan[c],
            curve_caliber=dict(q_base=Q_REF, npv_base=baseA["npv"], tinj_base=baseA["tinj_d"],
                               q_used=qA, npv_capped=limA["npv"], tinj_capped=limA["tinj_d"],
                               d_npv=limA["npv"] - baseA["npv"],
                               sign_unchanged=bool((limA["npv"] > 0) == (baseA["npv"] > 0))),
            front_caliber=dict(q_base=Q_DESIGN, npv_base=baseB["npv"], tinj_base=baseB["tinj_d"],
                               q_used=qB, npv_capped=limB["npv"], tinj_capped=limB["tinj_d"],
                               d_npv=limB["npv"] - baseB["npv"],
                               sign_unchanged=bool((limB["npv"] > 0) == (baseB["npv"] > 0))),
        )
    out["cost_of_capping"] = cost

    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "p6_checks.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("n per case =", n)
    print("m_nano > 30 t      : %5d  %7.4f" % (v_nano, v_nano / n))
    print("tinj+ts  > 90 d    : %5d  %7.4f" % (v_time, v_time / n))
    print("pass material+time : %5d  %7.4f" % (v_ok, v_ok / n))
    print("m_nano range t: %.3f .. %.3f (median %.3f)" %
          (out["m_nano_t"]["min"], out["m_nano_t"]["max"], out["m_nano_t"]["median"]))
    print("tinj max d    : %.3f" % out["tinj_d"]["max"])
    print()
    for c in CASES:
        k = cap[c]
        print("%s Pi9=%.4f  q_allow=%8.1f m3/d  feasible@800=%-5s shortfall=%.2fx" %
              (c, k["Pi9"], k["q_allow_m3d"], k["feasible_at_800"], k["shortfall_factor"]))
    print()
    for c in CASES:
        r = cost[c]
        a, b = r["curve_caliber"], r["front_caliber"]
        print("%s [curve q:%6.1f->%6.1f] npv %11.1f -> %11.1f  dNPV %11.1f  sign same=%s" %
              (c, a["q_base"], a["q_used"], a["npv_base"], a["npv_capped"], a["d_npv"],
               a["sign_unchanged"]))
        print("%s [front q:%6.1f->%6.1f] npv %11.1f -> %11.1f  dNPV %11.1f  sign same=%s" %
              (" ", b["q_base"], b["q_used"], b["npv_base"], b["npv_capped"], b["d_npv"],
               b["sign_unchanged"]))
    print("written:", os.path.abspath(p))


if __name__ == "__main__":
    main()