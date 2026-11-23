# -*- coding: utf-8 -*-
"""B 题数值对账器（数据层）—— 由 Lead 手写，不用骨架模板。

设计原则：**每条断言都从 JSON 里的原始量重算派生量**，而不是把文件里的数
硬编码一遍再比一次（那样只能证明文件没被手改，证明不了模型自洽）。

输出末行固定为 `declared=N checked=N failures=M`，供 pipeline 的 G5 正则解析。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

declared = 0
checked = 0
fails: list[str] = []


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def claim(label, actual, expected, tol):
    """actual 与 expected 必须是同一量纲的数；tol 为绝对容差。"""
    global declared, checked
    declared += 1
    checked += 1
    try:
        ok = abs(float(actual) - float(expected)) <= tol
    except Exception as e:  # noqa: BLE001
        fails.append(f"{label}: 无法比较 {actual!r} vs {expected!r} ({e})")
        return
    if not ok:
        fails.append(f"{label}: {actual} != {expected} (tol {tol})")


def truth(label, cond, detail=""):
    global declared, checked
    declared += 1
    checked += 1
    if not cond:
        fails.append(f"{label}: 断言不成立 {detail}")


# ---------------------------------------------------------------- P1
p1 = load("p1.json")
obs = p1["observability"]["T1"]
claim("P1 T1 面积分数=可观测格/全场格", obs["frac_of_field_3d"],
      obs["obs3d_cells"] / obs["total_cells"], 5e-6)
claim("P1 T1 俯仰可行占比", obs["frac_of_feasible_3d"],
      obs["obs3d_cells"] / obs["feasible_cells"], 5e-5)
claim("P1 T1 平面阴影漏掉的份额", obs["planar_missed_share_of_3d"],
      obs["planar_missed_cells"] / obs["obs3d_cells"], 5e-5)
truth("P1 T1 三维判定必须是平面阴影的超集",
      obs["planar_missed_cells"] >= 0 and obs["reverse_diff_cells"] == 0)

t1 = p1["p1_T1"]
claim("P1 Q 上确界 = 1/r_min（解析）", t1["q_sup"], 1.0 / t1["r_min_analytic"], 1e-7)
claim("P1 连续最优 Q = 1/r", t1["continuous"]["q"], 1.0 / t1["continuous"]["r"], 1e-7)
truth("P1 连续解不劣于上确界", t1["continuous"]["q"] <= t1["q_sup"] + 1e-9,
      f"{t1['continuous']['q']} vs {t1['q_sup']}")
claim("P1 连续最优解在俯仰上限（elev≈80）", t1["continuous"]["elev_deg"], 80.0, 0.01)
claim("P1 三目标求和上界 = Σ 1/r_min(Ti)", p1["ext_Q3_targets"]["bound_sum_1_over_rmin"],
      sum(1.0 / p1["observability"][t]["r_min_elev"] for t in ("T1", "T2", "T3")), 1e-5)

# ------------------------------------------------------- P1 面积网格收敛
g = load("p1_area_grid.json")
for row in g["rows"]:
    claim(f"P1面积网格 ds={row['ds']} 分数=格数/总格", row["frac_vehicle"],
          row["cells_vehicle"] / row["n_cells"], 5e-5)
    claim(f"P1面积网格 ds={row['ds']} 严格口径分数", row["frac_vehicle_strict"],
          row["cells_vehicle_strict"] / row["n_cells"], 5e-5)
truth("P1 面积网格：1 m 与 0.5 m 的相切口径差必须 > 0（相切被计入）",
      g["rows"][0]["frac_vehicle"] - g["rows"][1]["frac_vehicle"] > 0.01,
      f"{g['rows'][0]['frac_vehicle']} vs {g['rows'][1]['frac_vehicle']}")

# ---------------------------------------------------------------- P2(1)
p2 = load("p2.json")
p21 = p2["p2_1"]
claim("P2.1 DRMS 下界 = σ_rad·r_min·√2（γ=90°）", p21["drms_lower_bound"],
      math.radians(1.0) * p21["r_min_analytic"] * math.sqrt(2.0), 1e-6)
at = p21["attained"]
claim("P2.1 下界可达：attained.drms = 下界", at["drms"], p21["drms_lower_bound"], 1e-6)
claim("P2.1 可达解 γ=90°", at["gamma_deg"], 90.0, 1e-3)
claim("P2.1 可达解两站等距 r1=r2=r_min", at["r1"], at["r2"], 1e-6)
claim("P2.1 可达解 r1=r_min", at["r1"], p21["r_min_analytic"], 1e-4)
claim("P2.1 基线 = 两站水平距离（r1=r2、γ=90°）", at["baseline"],
      math.sqrt(2.0) * p21["r_min_analytic"], 2e-3)
claim("P2.1 稳健档 DRMS（仰角留 0.5°）", at["robust"]["drms"],
      math.radians(1.0) * at["robust"]["r_eff"] * math.sqrt(2.0), 1e-5)
truth("P2.1 稳健档 DRMS 必须大于理论下界",
      at["robust"]["drms"] > p21["drms_lower_bound"])
claim("P2.1 稳健代价 = (DRMS_robust/DRMS_floor - 1)*100", at["robust"]["cost_pct"],
      (at["robust"]["drms"] / p21["drms_lower_bound"] - 1.0) * 100.0, 0.05)

# ---------------------------------------------------------------- P2(2)
p22 = p2["p2_2"]
for row in p22["rows"]:
    claim(f"P2.2 cap={row['cap_m']} makespan = max(starts)", row["exact_makespan"],
          max(row["exact_starts"].values()), 1e-3)
    claim(f"P2.2 cap={row['cap_m']} 与贪心的相对差 = gap_s/makespan", row["gap_rel"],
          row["gap_s"] / row["exact_makespan"], 5e-5)
    for tgt in ("T1", "T2", "T3"):
        d = row["drms_exact"][tgt]
        tag = f"P2.2 cap={row['cap_m']} {tgt}"
        if abs(d["gamma_deg"]) < 0.5:          # 两站几乎共线 → 交会退化
            truth(tag + " 夹角≈0° 时 DRMS 必须判为不可用（inf）",
                  math.isinf(d["drms"]), f"γ={d['gamma_deg']} drms={d['drms']}")
        else:
            claim(tag + " DRMS 与 r1,r2,γ 一致",
                  d["drms"],
                  math.radians(1.0) * math.hypot(d["r1"], d["r2"])
                  / abs(math.sin(math.radians(d["gamma_deg"]))), 0.06)

for cap in ("unconstrained", "cap20"):
    rec = p22[cap]
    tl = rec["timeline"]
    for veh, segs in tl.items():
        for s in segs:
            tag = f"P2.2[{cap}] {veh}->{s['alert']}"
            claim(tag + " 观测窗=5 s", s["obs_end"] - s["obs_start"], 5.0, 1e-4)
            claim(tag + " ready = arrive + slew", s["ready"], s["arrive"] + s["slew"], 1e-4)
            claim(tag + " free = obs_end + reset", s["free"], s["obs_end"] + s["reset"], 1e-3)
            truth(tag + " 观测只能在 ready 之后开始", s["obs_start"] >= s["ready"] - 1e-6,
                  f"{s['obs_start']} < {s['ready']}")
    for alr, pair in rec["assign"].items():
        starts = [s["obs_start"] for v in pair for s in tl[v] if s["alert"] == alr]
        claim(f"P2.2[{cap}] {alr} 两车同步开始观测", max(starts), min(starts), 1e-6)
        claim(f"P2.2[{cap}] {alr} 开始时刻 = starts 表", rec["starts"][alr], min(starts), 5e-3)
    claim(f"P2.2[{cap}] makespan = max(starts)", rec["makespan"],
          max(rec["starts"].values()), 1e-6)

# ---------------------------------------------------------------- P3
p3 = load("p3.json")["p3"]
z = p3["z975"]
claim("P3 预算角 = 5/z(.975)", p3["budget_deg"], 5.0 / z, 1e-6)
claim("P3 定位项允许 σ = sqrt(budget²-0.8²-0.6²)", p3["sigma_loc_allow_deg"],
      math.sqrt(p3["budget_deg"] ** 2 - 0.8 ** 2 - 0.6 ** 2), 1e-5)
claim("P3 允许 σ_s = r·σ_loc_allow（小角近似）", p3["sigma_s_allow_m"],
      40.0 * math.radians(p3["sigma_loc_allow_deg"]), 1e-4)
claim("P3 s_max 闭式 = [r·sqrt(σ_loc²-0.8²-0.6²)·π/180 - a]/b", p3["s_max"],
      (40.0 * math.sqrt(p3["budget_deg"] ** 2 - 0.8 ** 2 - 0.6 ** 2) * math.pi / 180.0 - 0.3) / 0.02,
      2e-3)
claim("P3 二分与闭式一致", p3["s_max_bisect"], p3["s_max"], 1e-3)
ab = p3["ab_constraint"]
claim("P3 a=80 m 时 b 上限 = σ_allow/80", ab["b_max"], ab["sigma_s_allow"] / 80.0, 1e-6)
claim("P3 a=0.3 时 b 上限 = (σ_allow-0.3)/80", ab["b_at_a_eq_03"],
      (ab["sigma_s_allow"] - 0.3) / 80.0, 1e-6)
claim("P3 名义 b=0.02 的超额", ab["shortfall_b"], 0.02 - ab["b_at_a_eq_03"], 1e-6)
claim("P3 交点 σ ≈ 1.6384 m", ab["sigma_s_allow"], p3["sigma_s_allow_m"], 1e-4)

# ---------------------------------------------------------------- 汇总
print(f"declared={declared} checked={checked} failures={len(fails)}")
for f in fails:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
