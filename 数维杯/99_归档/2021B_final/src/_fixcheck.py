"""Collect the exact numbers needed to fix the judge-evidence mismatches."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

R = Path(r"E:\数学建模\数维杯\03_实战演练\2021_B_ExtremeRainfall\03_results")

# --- Q3 ranking ---------------------------------------------------------
pred = pd.read_csv(R / "q3_city_predictions.csv")
print("== q3_city_predictions columns ==")
print(list(pred.columns))
if "p10" in pred.columns:
    cols = [c for c in ["city", "p10", "rl_10yr", "rl_50yr", "risk_rank", "obs_max_rx1day", "rf_pred"] if c in pred.columns]
    print(pred.sort_values("p10", ascending=False).head(8)[cols].to_string(index=False))

risk = pd.read_csv(R / "q3_city_risk.csv")
print("\n== q3_city_risk columns ==")
print(list(risk.columns))
print(risk.sort_values("rl_10yr", ascending=False).head(6).to_string(index=False))

# --- Q5 uniform grid ---------------------------------------------------
g = pd.read_csv(R / "q5_portfolio_grid.csv")
print("\n== q5_portfolio_grid columns ==")
print(list(g.columns))
best = g.loc[g.groupby("city")["bcr_econ"].idxmax()]
print("\n== max bcr_econ per city ==")
print(best[["city", "t_pipe", "s_depth", "green", "bcr_econ", "bcr_soc", "total_cost", "ead"]].to_string(index=False))
print("\nHaikou grid rows sorted by bcr_econ, top 6:")
hk = g[g["city"] == "Haikou"].sort_values("bcr_econ", ascending=False).head(6)
print(hk[["t_pipe", "s_depth", "green", "bcr_econ", "bcr_soc", "total_cost", "ead"]].to_string(index=False))

# --- Q5 selective: the three "--" cells --------------------------------
sel = pd.read_csv(R / "q5_selective_protection.csv")
print("\n== selective columns ==", list(sel.columns))
print(sel.to_string(index=False))

# --- Q1 return-level CIs ----------------------------------------------
rl = pd.read_csv(R / "q1_return_levels_daily.csv")
print("\n== q1_return_levels_daily ==")
print(rl.to_string(index=False))

# --- Q2 ge50 median ----------------------------------------------------
tr = pd.read_csv(R / "q2_city_trends.csv")
print("\nge50 pct/decade: median", tr["ge50_pct_per_decade"].median(), "mean", tr["ge50_pct_per_decade"].mean())

# --- SCS-CN spot checks ------------------------------------------------
def scs_cn(P, cn):
    S = 25400.0 / cn - 254.0
    return (P - 0.2 * S) ** 2 / (P + 0.8 * S)

for cn in (75, 80, 85, 90, 95):
    print(f"CN{cn}: Q(201.9)={scs_cn(201.9, cn):.3f}  Q(313.4)={scs_cn(313.4, cn):.3f}  Q(449)={scs_cn(449, cn):.3f}")

area = 1180.0
q_peak = scs_cn(201.9, 85)
print("\npeak-hour runoff depth CN85 =", round(q_peak, 3), "mm; excess over 36 mm/h =", round(q_peak - 36, 3),
      "mm; volume =", f"{(q_peak - 36) / 1000 * area * 1e6:.4e}", "m3")
q_ev = scs_cn(313.4, 85)
print("event runoff depth CN85 =", round(q_ev, 3), "mm; volume =", f"{q_ev / 1000 * area * 1e6:.4e}",
      "m3; drain hours = 313.4/36 =", round(313.4 / 36, 4))
print("Q5: Q(449,85) =", round(scs_cn(449, 85), 3), "->", f"{(scs_cn(449, 85) - 102.9315) / 1000 * area * 1e6:.4e}", "m3 over ref")

# --- JSON values used by the paper ------------------------------------
res = json.loads((R / "q1_results.json").read_text(encoding="utf-8"))
print("\n== q1_results keys ==", list(res.keys()))
print("xi:", res.get("gev", {}).get("xi"), "n_boot:", res.get("gev", {}).get("n_boot"))
print("event:", json.dumps(res.get("event", {}), ensure_ascii=False)[:800])
print("waterlogging:", json.dumps(res.get("waterlogging", {}), ensure_ascii=False)[:1200])