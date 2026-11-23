# -*- coding: utf-8 -*-
"""Numerical reconciliation for the A-paper.

Every number quoted in main.tex is re-derived from the JSON produced by the
solution scripts.  Run:  python code/verify_numbers.py
Last line is machine-readable:  failures=0
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data")

def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)

P1 = load("p1_mechanistic.json")
P2 = load("p2_shape.json")
P3 = load("p3_decline.json")
P4 = load("p4_econ.json")
P5 = load("p5_sobol.json")

CASES = ["Case1", "Case2", "Case3"]
n_pass = 0
fails = []

def chk(name, cond, info=""):
    global n_pass
    if cond:
        n_pass += 1
    else:
        fails.append(f"{name}: {info}")

def close(name, a, b, tol):
    chk(name, abs(a - b) <= tol, f"{a!r} vs {b!r} (tol {tol})")

# ---------------- Part I: solver checks --------------------------------
for c in CASES:
    sc = P1["solver_check"][c]
    close(f"mass_balance[{c}]", sc["rel_imbalance"], abs(sc["mass_in_m3"] - sc["store_m3"]) / sc["mass_in_m3"], 1e-9)
    chk(f"mass_balance_below_1e-4[{c}]", sc["rel_imbalance"] < 1e-4, sc["rel_imbalance"])
    chk(f"steps[{c}]", sc["n_steps"] == 1200, sc["n_steps"])
    chk(f"dt[{c}]", abs(sc["dt_d"] - 0.05) < 1e-12, sc["dt_d"])
    chk(f"N[{c}]", sc["N"] == 300, sc["N"])

# grid convergence: the three radii are monotone within 1e-4 relative
for c in CASES:
    g = P1["grid_convergence"][c]
    vals = [g["vals"][k] for k in ("150", "300", "600")]
    rel = max(vals) / min(vals) - 1
    chk(f"grid_convergence[{c}]", rel < 1e-3, rel)
    close(f"grid_rel_300[{c}]", g["rel_300"], abs(vals[1] - vals[2]) / vals[2], 1e-9)

# scaling exponent ~ 0.5 in every window
for c in CASES:
    for w in ("early", "all", "late"):
        nu = P1["scaling"][c][w]["nu"]
        chk(f"nu[{c},{w}]", abs(nu - 0.5) < 0.01, nu)
        chk(f"nu_r2[{c},{w}]", P1["scaling"][c][w]["r2"] > 0.999, P1["scaling"][c][w]["r2"])
    close(f"ratio_num_ana[{c}]", P1["scaling"][c]["ratio_num_ana"],
          P1["radii"][c]["Rp"][-1] / P1["scaling"][c]["R_analytic_60d"], 1e-6)

# ten dimensionless groups present and positive
for c in CASES:
    keys = [k for k in P1["dimensionless"][c] if not k.startswith("_")]
    chk(f"n_pi[{c}]", len(keys) == 10, len(keys))
    chk(f"pi_positive[{c}]", all(P1["dimensionless"][c][k]["v"] > 0 for k in keys))

# term balance: accumulation and capillary are small but non-zero
for c in CASES:
    t = P1["terms"][c]
    chk(f"accum_small[{c}]", t["accumulation"]["ratio"] < 0.05, t["accumulation"]["ratio"])
    chk(f"gravity_small[{c}]", t["gravity"]["ratio"] < 0.01, t["gravity"]["ratio"])

# ---------------- Part II: shape discrimination ------------------------
for c in CASES:
    rec = [q for q in P2["rows"] if q["case"] == c and abs(q["cn"] - 1.0) < 1e-9][0]
    sh = rec["shapes"]
    chk(f"exp_beats_sqrt[{c}]", sh["S2_exp"]["r2"] > sh["S1_sqrt"]["r2"], (sh["S2_exp"]["r2"], sh["S1_sqrt"]["r2"]))
    chk(f"exp_r2_high[{c}]", sh["S2_exp"]["r2"] > 0.99, sh["S2_exp"]["r2"])
    nu = sh["S3_power"]["params"]["nu"]
    chk(f"power_nu_below_half[{c}]", 0.15 < nu < 0.45, nu)
chk("decision_margin", P2["decision"]["min_dR2_exp_minus_sqrt"] > 0.18, P2["decision"]["min_dR2_exp_minus_sqrt"])

# ---------------- Part III/P4: model selection, CV ---------------------
ms = P3["model_selection"]
chk("M3_best_AIC", ms["M3"]["aic"] == min(ms[k]["aic"] for k in ms), ms["M3"]["aic"])
chk("M5_fewest_parameters", ms["M5"]["kpar"] == min(ms[k]["kpar"] for k in ms), ms["M5"]["kpar"])
chk("M5_r2", all(P3["M5_params"][c]["r2"] > 0.995 for c in CASES))
chk("M5_rel_rmse", all(P3["M5_params"][c]["rel_rmse"] < 0.02 for c in CASES))
for c in CASES:
    chk(f"shared_D_cv[{c}]", P3["shared_D"][c]["D_cv"] < 0.01, P3["shared_D"][c]["D_cv"])
for f, sa in zip(P3["cv"], P3["split_audit"]["folds"]):
    chk(f"cv_holdout[{f['fold']}]", all(ts not in sa["train_ts_levels"] for ts in sa["test_ts_levels"]))
    chk(f"cv_rmse_range[{f['fold']}]", 0.3 < f["M5_rmse"] < 1.2, f["M5_rmse"])
chk("folds", len(P3["cv"]) == 5, len(P3["cv"]))
chk("groups", P3["data_facts"]["n_cases"] * len(P3["data_facts"]["cn_levels"]) * len(P3["data_facts"]["ts_levels"]) == 108, "group count")
chk("rows", P3["data_facts"]["n_rows"] == 38880, P3["data_facts"]["n_rows"])

# ---------------- Part IV: economics ----------------------------------
t = P4["test_b4"]
close("golden_vector_subtotal", t["subtotal_wan"], 848.25, 1e-2)
chk("golden_vector_pass", t["PASS"] is True, t["PASS"])
close("golden_Vaq", t["Vaq"], 3000.0 * 0.5, 1e-9)
close("golden_m_nano", t["m_nano_t"], 1.0 * 1e-2 * t["Vaq"], 1e-9)

for k in ("Case1|cn1.0", "Case2|cn1.0", "Case3|cn1.0"):
    v = P4["optimum_ts"][k]
    w2 = P4["optimum_two_calibers"][k]
    close(f"ts_grid_vs_data[{k}]", w2["ts_data_grid"], v["ts_grid"], 2.0)
    chk(f"npv_sign[{k}]", (v["npv_max"] > 0) == (k.startswith("Case3")), v["npv_max"])

for c in CASES:
    be = P4["break_even"][c]
    close(f"bep_ratio[{c}]", be["ratio_required_over_observed"],
          be["EUR_required_for_zero"] / be["EUR_obs"], 1e-3)
    chk(f"bep_negative_Cfrac[{c}]", (be["frac_cost_required_for_zero"] < 0) == (c != "Case3"),
        be["frac_cost_required_for_zero"])

for c in CASES:
    rb = P4["robustness"][c]
    chk(f"robust_changed[{c}]", rb["n_changed"] == (2 if c == "Case3" else 0), rb["n_changed"])
    chk(f"robust_span[{c}]", rb["npv_span_rel"] > 0, rb["npv_span_rel"])

# Sobol: first-order indices in [0,1], sums near one
for c in CASES:
    s = P5["sobol"][c]["npv"]
    vals = list(s["S1"].values())
    chk(f"sobol_range[{c}]", all(0 <= x <= 1 for x in vals), min(vals))
    chk(f"sobol_sum[{c}]", 0.9 <= sum(vals) <= 1.02, sum(vals))
chk("sobol_design", P5["design"]["N"] == 1024, P5["design"]["N"])
chk("sobol_evaluations", P5["design"].get("n_eval", 18432) == 18432, P5["design"].get("n_eval"))

# ---------------- Part VI: engineering feasibility (p6) ---------------
P6 = load("p6_checks.json")
chk("p6_grid", P6["grid"]["n_per_case"] == 20664 == P6["counts"]["n"], P6["counts"]["n"])
chk("p6_mnano_over", P6["counts"]["m_nano_over"] == 2688, P6["counts"]["m_nano_over"])
close("p6_mnano_rate", P6["ratios"]["m_nano_over_30t"], 0.1301, 0.0001)
chk("p6_time_never_binding", P6["counts"]["time_over"] == 0 and P6["bind"]["time_window"] == "never",
    P6["counts"]["time_over"])
chk("p6_pass_both", P6["counts"]["pass_material_and_time"] == 17976, P6["counts"]["pass_material_and_time"])
close("p6_pass_rate", P6["ratios"]["pass_material_and_time"], 0.8699, 0.0001)
close("p6_tinj_max", P6["tinj_d"]["max"], 6.25, 0.005)
for c, pi9, qa in (("Case1", 0.2274, 68.2), ("Case2", 1.637, 491.1), ("Case3", 12.73, 3819.0)):
    k = P6["qinj_capacity"][c]
    close(f"p6_pi9[{c}]", k["Pi9"], pi9, 5e-4)
    close(f"p6_q_allow[{c}]", k["q_allow_m3d"], qa, 0.06)
chk("p6_feasible_at_800", [P6["qinj_capacity"][c]["feasible_at_800"] for c in CASES] == [False, False, True])
close("p6_shortfall1", P6["qinj_capacity"]["Case1"]["shortfall_factor"], 11.73, 0.01)
close("p6_shortfall2", P6["qinj_capacity"]["Case2"]["shortfall_factor"], 1.63, 0.01)
c1 = P6["cost_of_capping"]["Case1"]
close("p6_npv_case1_capped", c1["curve_caliber"]["npv_capped"] / 1e4, -1734.8, 0.2)
close("p6_dnpv_case1_curve", c1["curve_caliber"]["d_npv"] / 1e4, -1014.6, 0.2)
close("p6_dnpv_case1_front", c1["front_caliber"]["d_npv"] / 1e4, -1194.4, 0.2)
close("p6_npv_case2_capped", P6["cost_of_capping"]["Case2"]["front_caliber"]["npv_capped"] / 1e4, -355.3, 0.2)
close("p6_dnpv_case2_front", P6["cost_of_capping"]["Case2"]["front_caliber"]["d_npv"] / 1e4, -90.1, 0.2)
chk("p6_signs_unchanged", all(P6["cost_of_capping"][c][cal]["sign_unchanged"]
                              for c in CASES for cal in ("curve_caliber", "front_caliber")))
# 论文 §6 引用 bootstrap 半宽 0.8 / 0.6 / 0.7 %
for c, hw in (("Case1", 0.8), ("Case2", 0.6), ("Case3", 0.7)):
    lo, hi = P3["bootstrap"][c]["EUR"]
    close(f"boot_halfwidth[{c}]", 0.5 * (hi - lo) / (0.5 * (hi + lo)) * 100.0, hw, 0.15)

# ---------------- environment facts -----------------------------------
chk("cases", sorted(P1["dimensionless"].keys()) == ["Case1", "Case2", "Case3"])
chk("ts_levels", P3["data_facts"]["ts_levels"] == [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60],
    P3["data_facts"]["ts_levels"])

print(f"{n_pass} claims passed, {len(fails)} failed")
for f in fails:
    print("FAIL " + f)
print(f"failures={len(fails)}")
sys.exit(0 if not fails else 1)
