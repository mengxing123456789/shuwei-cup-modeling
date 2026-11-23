"""Ten-year probability that a city exceeds its 1961-2010 daily record.

The earlier risk table mixed two definitions: the probability over the short
held-out window and the ten-year probability.  This script recomputes one
consistent quantity for all 23 cities of the forecast panel:

    p10 = 1 - (1 - P(X > record_1961_2010))^10

with the annual exceedance probability taken from the L-moment GEV fit of the
1961-2010 annual maxima, so the ranking behind the paper's risk table is
reproducible from a single stored file.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import genextreme

import common as C

TRAIN = (1961, 2010)
HORIZON = 10


def city_series(sid: str, city: str) -> pd.DataFrame:
    path = C.RESULTS / "ghcn" / f"{sid}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    g = C.load_ghcn_wide(path)
    return g[["date", "prcp_mm"]]


def main() -> None:
    pred = pd.read_csv(C.RESULTS / "q3_city_predictions.csv")
    risk = pd.read_csv(C.RESULTS / "q3_city_risk.csv").set_index("city")
    rows = []
    for rec in pred.itertuples(index=False):
        d = city_series(rec.id, rec.city)
        ai = C.annual_indices(C.daily_grid(d[["date", "prcp_mm"]]))
        tr = ai.loc[TRAIN[0]:TRAIN[1]]
        x = tr["rx1day"].dropna().to_numpy(dtype=float)
        fit = C.gev_fit_lmom(x)
        fit_mle = C.gev_fit(x)
        record = float(np.max(x))
        p_annual = C.gev_exceed_prob(fit, record)
        p_annual_mle = C.gev_exceed_prob(fit_mle, record)
        p10 = 1.0 - (1.0 - p_annual) ** HORIZON
        p10_mle = 1.0 - (1.0 - p_annual_mle) ** HORIZON
        rows.append(
            {
                "city": rec.city,
                "id": rec.id,
                "n_train": int(len(x)),
                "record_mm": round(record, 1),
                "p_annual": p_annual,
                "p10": p10,
                "p_annual_mle": p_annual_mle,
                "p10_mle": p10_mle,
                "rl_10yr": round(float(risk.loc[rec.city, "rl_10yr"]), 2),
                "rl_50yr": round(float(risk.loc[rec.city, "rl_50yr"]), 2),
                "pred_next_decade_max_RF": round(float(risk.loc[rec.city, "pred_next_decade_max_RF"]), 2),
                "pred_next_decade_max_GBR": round(float(risk.loc[rec.city, "pred_next_decade_max_GBR"]), 2),
                "pred_loocv_RF": round(float(rec.pred_RF), 2),
            }
        )
    out = pd.DataFrame(rows).sort_values("p10", ascending=False).reset_index(drop=True)
    out["rank_p10"] = np.arange(1, len(out) + 1)
    out["rank_p10_mle"] = out["p10_mle"].rank(ascending=False, method="min").astype(int)
    out["rank_rf"] = out["pred_next_decade_max_RF"].rank(ascending=False, method="min").astype(int)
    out["risk_rank"] = out[["rank_p10", "rank_rf"]].mean(axis=1).rank(method="min").astype(int)
    out.to_csv(C.RESULTS / "q3_risk_table.csv", index=False)
    print(out.head(12).to_string(index=False))
    zc = out[out["city"] == "Zhengzhou"].iloc[0]
    payload = {
        "n_cities": int(len(out)),
        "horizon_years": HORIZON,
        "top10": out.head(10).round(4).to_dict(orient="records"),
        "zhengzhou": {
            "p10": round(float(zc["p10"]), 4),
            "rank_p10": int(zc["rank_p10"]),
            "risk_rank": int(zc["risk_rank"]),
            "record_mm": float(zc["record_mm"]),
            "rl_10yr": float(zc["rl_10yr"]),
            "pred_RF": float(zc["pred_next_decade_max_RF"]),
        },
    }
    (C.RESULTS / "q3_risk_table.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload["zhengzhou"], indent=2))


if __name__ == "__main__":
    main()