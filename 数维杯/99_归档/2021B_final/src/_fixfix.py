"""Numbers for the post-review corrections: BCR ceiling, risk ranking, RMSE bootstrap, gamma/discount sweep."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

CODE = Path(__file__).parent
sys.path.insert(0, str(CODE))
import common as C
import s06_q5 as Q5

R = C.RESULTS
rng = np.random.default_rng(20211117)

# --- (a) ceiling of the uniform grid -----------------------------------
base = pd.read_csv(R / "q5_baselines.csv").set_index("city")
grid = pd.read_csv(R / "q5_portfolio_grid.csv")
grid["bcr"] = (grid["city"].map(base["baseline_ead_cny"]) - grid["ead_cny"]) / grid["annual_cost_cny"].clip(lower=1)
print("== uniform grid: best BCR per city ==")
idx = grid.groupby("city")["bcr"].idxmax()
print(grid.loc[idx, ["city", "green", "T_pipe", "storage_mm", "bcr", "capex_cny", "ead_cny"]]
      .sort_values("bcr", ascending=False).to_string(index=False))
print("\ngrid BCR > 1 rows:", int((grid["bcr"] > 1).sum()), "of", len(grid))
print(grid[grid["bcr"] > 1].sort_values("bcr", ascending=False)
      .head(8)[["city", "green", "T_pipe", "storage_mm", "bcr"]].to_string(index=False))

# --- (b) risk ranking ---------------------------------------------------
risk = pd.read_csv(R / "q3_city_risk.csv").sort_values("risk_rank")
print("\n== risk ranking (top 10) ==")
print(risk.head(10)[["risk_rank", "city", "p_exceed_record_10y", "rl_10yr", "rl_50yr"]].to_string(index=False))

# --- (c) Q1 return levels ----------------------------------------------
rl = pd.read_csv(R / "q1_return_levels_daily.csv")
print("\n== q1 return levels ==")
print(rl.to_string(index=False))

# --- (d) paired bootstrap on RMSE differences ---------------------------
pred = pd.read_csv(R / "q3_city_predictions.csv")
obs = pred["obs_max_rx1day"].to_numpy(float)
methods = ["GEV_T14", "GEV_Emax", "GEV_Emax_trend", "GEV_LM_T14", "pred_Ridge"]


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


print("\n== paired bootstrap over cities (2000 resamples) ==")
scores = {m: rmse(pred[m].to_numpy(float), obs) for m in methods}
for m in methods:
    print(f"{m:16s} RMSE = {scores[m]:.3f}")
for a, b in [("GEV_T14", "GEV_Emax"), ("GEV_Emax", "GEV_Emax_trend"), ("GEV_Emax", "pred_Ridge")]:
    diffs = []
    n = len(obs)
    for _ in range(2000):
        i = rng.integers(0, n, n)
        diffs.append(rmse(pred[a].to_numpy(float)[i], obs[i]) - rmse(pred[b].to_numpy(float)[i], obs[i]))
    diffs = np.array(diffs)
    print(f"RMSE({a}) - RMSE({b}) = {scores[a] - scores[b]:+.2f}  95% CI [{np.percentile(diffs, 2.5):+.2f}, {np.percentile(diffs, 97.5):+.2f}]  P(diff>0)={np.mean(diffs > 0):.3f}")

# --- (e) gamma x discount sweep on Haikou plans -------------------------
print("\n== gamma x discount sweep, Haikou ==")
hk = Q5.CITIES["Haikou"]
ann = Q5.load_annual(hk["id"])
fit3 = C.gev_fit(ann["rx3day"].dropna().to_numpy(float))
cap0 = float(C.gev_return_level(fit3, 2))
over_ref = float(Q5.scs_runoff(449.0, hk["cn"]) - cap0)
print(f"Haikou RL3d(2) = {cap0:.2f} mm, Oref = {over_ref:.2f} mm, baseline EAD = {base.loc['Haikou','baseline_ead_cny']/1e8:.2f} 1e8")

plans = {"uniform T2 S5": (2, 5.0, 0.0), "uniform T2 S80": (2, 80.0, 0.0), "hotspot h2 m20 S5": (2, 5.0, 0.0)}
for gname, (tp, s, green) in plans.items():
    capex = s * hk["area_km2"] * 1e3 * Q5.P["storage_cost_per_m3"]
    if green:
        capex += green * hk["area_km2"] * Q5.P["green_cost_per_km2"]
    cap = float(C.gev_return_level(fit3, tp)) + s
    cn = hk["cn"] - Q5.P["green_cn_drop"] * green
    for gamma in (1.2, 1.5, 1.8):
        ead, cvar, deaths, over = Q5.evaluate(ann["rx3day"].to_numpy(float), cn, cap, hk["area_km2"],
                                              Q5.OFFICIAL_LOSS, over_ref, gamma, hk["deaths_ref"],
                                              Q5.P["deaths_elasticity"])
        for disc in (0.02, 0.04, 0.06):
            annual = (Q5.crf(disc, 30) + Q5.P["om_share"]) * capex
            bcr = (base.loc["Haikou", "baseline_ead_cny"] - ead) / max(annual, 1.0)
            print(f"{gname:20s} gamma={gamma:.1f} r={disc:.2f}  EAD={ead/1e8:7.2f}e8  annual={annual/1e8:5.2f}e8  BCR={bcr:6.2f}")

# hotspot variant: damage multiplier on the protected 2% is handled by scaling damage there
print("\n== hotspot h2 m20, Haikou, gamma sweep (S=5 mm) ==")
cap = float(C.gev_return_level(fit3, 2)) + 5.0
capex = 5.0 * hk["area_km2"] * 1e3 * Q5.P["storage_cost_per_m3"]
annual = (Q5.crf(0.04, 30) + Q5.P["om_share"]) * capex
for gamma in (1.2, 1.5, 1.8):
    ead, _, _, _ = Q5.evaluate(ann["rx3day"].to_numpy(float), hk["cn"], cap, hk["area_km2"],
                               Q5.OFFICIAL_LOSS, over_ref, gamma, hk["deaths_ref"], Q5.P["deaths_elasticity"])
    h = 0.02
    ead_hot = ead * (1 - h) + ead * h * 20
    bcr = (base.loc["Haikou", "baseline_ead_cny"] - ead_hot) / max(annual, 1.0)
    print(f"gamma={gamma:.1f}  EAD={ead/1e8:.2f}e8  BCR={bcr:.2f}")
