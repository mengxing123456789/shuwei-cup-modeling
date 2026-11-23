"""Q5 robustness: gamma, discount, CN, tail estimator and areal-vs-station anchor.

All calculations reuse the calibration of s06_q5 (anchor: 2021 Zhengzhou event, Oref in
runoff space). Uniform plans only; hotspot results are rescaled analytically where noted.
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

CODE = Path(__file__).parent
sys.path.insert(0, str(CODE))
import common as C
import s06_q5 as Q5

R = C.RESULTS
ANCHOR = 296.4240664806609          # Oref, mm of runoff surplus (Zhengzhou 2021, RL3d(2))
BASE = pd.read_csv(R / "q5_baselines.csv").set_index("city")


def plan_bcr(city: str, s_mm: float, gamma: float, discount: float, cn=None, fit=None) -> dict:
    cfg = Q5.CITIES[city]
    am = Q5.load_annual(cfg["id"])
    rain3 = am["rx3day"].to_numpy(dtype=float)
    f = fit if fit is not None else C.gev_fit_lmom(rain3)
    rl2 = float(C.gev_return_level(f, 2))
    cap = rl2 + s_mm
    cn_use = cfg["cn"] if cn is None else cn
    over = Q5.overflow_depth(rain3, cn_use, cap)
    loss_city = Q5.city_loss_scale(cfg["area_km2"], gamma)
    dmg = loss_city * np.power(np.clip(over / ANCHOR, 0.0, None), gamma)
    ead = float(np.mean(dmg))
    base_ead = float(np.mean(loss_city * np.power(
        np.clip(Q5.overflow_depth(rain3, cn_use, rl2) / ANCHOR, 0.0, None), gamma)))
    capex = Q5.P["storage_cost_per_m3"] * s_mm * cfg["area_km2"] * 1e3
    annual = (Q5.crf(discount, Q5.P["horizon"]) + Q5.P["om_share"]) * capex
    return {"city": city, "storage_mm": s_mm, "gamma": gamma, "discount": discount,
            "cn": cn_use, "ead": ead, "base_ead": base_ead,
            "bcr": (base_ead - ead) / annual if annual > 0 else np.nan}


rows = []
for city, s in [("Haikou", 5.0), ("Haikou", 80.0), ("Guangzhou", 5.0), ("Zhengzhou", 5.0)]:
    for gamma in (1.2, 1.5, 1.8):
        for disc in (0.02, 0.04, 0.06):
            rows.append(plan_bcr(city, s, gamma, disc))
df = pd.DataFrame(rows)
df.to_csv(R / "q5_sensitivity.csv", index=False)
print("== uniform-plan BCR: gamma x discount ==")
piv = df.pivot_table(index=["city", "storage_mm"], columns=["gamma", "discount"], values="bcr")
print(piv.round(2).to_string())

print("\n== CN sensitivity, Haikou S=5 mm, gamma 1.5, r=4% ==")
for cn in (75.0, 82.0, 85.0, 95.0):
    r = plan_bcr("Haikou", 5.0, 1.5, 0.04, cn=cn)
    print(f"CN {cn:5.1f}: EAD {r['ead']/1e8:7.2f}e8  baseline {r['base_ead']/1e8:7.2f}e8  BCR {r['bcr']:.3f}")

print("\n== tail estimator: L-moments vs MLE design depth, Haikou S=5 mm ==")
for city in ("Haikou", "Zhengzhou"):
    for name, f in (("LM", C.gev_fit_lmom), ("MLE", C.gev_fit)):
        am = Q5.load_annual(Q5.CITIES[city]["id"])
        fit = f(am["rx3day"].to_numpy(dtype=float))
        r = plan_bcr(city, 5.0, 1.5, 0.04, fit=fit)
        print(f"{city:10s} {name:3s} RL3d(2) = {float(C.gev_return_level(fit, 2)):7.2f} mm  BCR = {r['bcr']:.3f}")

print("\n== areal ($449) vs station ($313.4) anchor ==")
# analytic rescale: Oref_station = Q(313.4) - C, with C = RL3d(2) of Zhengzhou
am = Q5.load_annual(Q5.CITIES["Zhengzhou"]["id"])
fz = C.gev_fit_lmom(am["rx3day"].to_numpy(dtype=float))
cap_z = float(C.gev_return_level(fz, 2))
o_area = float(Q5.scs_runoff(449.0, 85.0) - cap_z)
o_station = float(Q5.scs_runoff(313.4, 85.0) - cap_z)
print(f"Oref areal {o_area:.2f} mm, Oref station {o_station:.2f} mm, damage scale x{(o_area/o_station)**1.5:.3f}")
print("Every BCR below is multiplied by that factor if the station anchor is used instead.")
_base = pd.read_csv(R / "q5_baselines.csv").set_index("city")
for city in ("Haikou", "Guangzhou", "Zhengzhou"):
    b = float(_base.loc[city, "bcr_econ"])
    print(f"{city}: uniform BCR at its own optimum {b:.3f} -> {b * (o_area/o_station)**1.5:.3f} "
          "under the station anchor")