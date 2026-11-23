# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Official-caliber P2 error: mean 3D distance R = mean ||p_hat - p_ref||_2.

Reads the frozen prediction caches written by up_p2_quantile.py / the ridge
replica, adds the hold-last baseline computed from the target sequence itself,
and reports R, RMSE, median, q90 and record-level bootstrap CIs.

No training, no test-time tuning: this is a re-calibration of the same
predictions under the metric defined in Problem 2 of the C statement.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RNG = np.random.default_rng(20261121)
NBOOT = 4000


def load_pred(name: str, lead: int):
    p = DATA / f"up_p2_{name}_pred_L{lead}.npz"
    d = np.load(p)
    out = {}
    for split in ("val", "test"):
        pred = d[split]
        if pred.ndim == 4:
            # quantile model: 11 taus, take the median (index 5)
            pred = pred[:, :, :, pred.shape[-1] // 2]
        tgt = d[f"{split}_tgt"]
        rec = d[f"{split}_rec"]
        if pred.shape != tgt.shape:
            raise SystemExit(f"shape mismatch {name} L{lead} {split}: {pred.shape} {tgt.shape}")
        out[split] = (pred.astype(np.float64), tgt.astype(np.float64), rec.astype(int))
    return out


def metrics(pred: np.ndarray, tgt: np.ndarray) -> dict:
    dist = np.linalg.norm(pred - tgt, axis=2)  # (N, H) metres
    return {
        "mean_R_cm": float(dist.mean() * 100.0),
        "rmse_3d_cm": float(np.sqrt((dist ** 2).mean()) * 100.0),
        "median_cm": float(np.median(dist) * 100.0),
        "q90_cm": float(np.quantile(dist, 0.90) * 100.0),
        "n_points": int(dist.size),
        "n_records": int(pred.shape[0]),
    }


def per_record_mean(pred: np.ndarray, tgt: np.ndarray) -> np.ndarray:
    dist = np.linalg.norm(pred - tgt, axis=2)
    return dist.mean(axis=1)


def boot_ci(values: np.ndarray, n: int = NBOOT) -> tuple[float, float]:
    n = len(values)
    draws = RNG.integers(0, n, size=(n_boot := 4000, n))
    means = values[draws].mean(axis=1)
    return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))


def main() -> None:
    result = {"_meta": {
        "script": "code/p2_official_distance.py",
        "official_metric": "R = (1/M) sum ||p_hat - p_ref||_2, mean over all predicted points",
        "source": "data/up_p2_{ridge,quantile}_pred_L*.npz (frozen predictions); hold-last = first target frame repeated",
        "bootstrap": "record-level, 4000 draws, 95% percentile interval",
    }, "by_lead": {}}

    for lead in (6, 18, 30, 60):
        ridge = load_pred("ridge", lead)
        quant = load_pred("quantile", lead)
        entry = {}
        for split in ("val", "test"):
            rp, rt, rr = ridge[split]
            qp, qt, qr = quant[split]
            # hold-last: repeat the first observed target state
            hp = np.repeat(rt[:, :1, :], rt.shape[1], axis=1)

            rows = {}
            for label, pred in (("hold", hp), ("ridge", rp), ("quantile", qp)):
                rows[label] = metrics(pred, rt)

            # paired, record-level differences (negative = model better than hold)
            for label, pred in (("ridge", rp), ("quantile", qp)):
                d = per_record_mean(pred, rt) - per_record_mean(hp, rt)
                lo, hi = boot_ci(d)
                rows[label]["delta_vs_hold_cm"] = float(d.mean() * 100.0)
                rows[label]["delta_ci95_cm"] = [lo * 100.0, hi * 100.0]

            entry[split] = rows
        result["by_lead"][str(lead)] = entry

    # headline: official R on test at the four horizons
    result["headline"] = {
        f"L{lead}": {
            "hold": result["by_lead"][str(lead)]["test"]["hold"]["mean_R_cm"],
            "ridge": result["by_lead"][str(lead)]["test"]["ridge"]["mean_R_cm"],
            "quantile": result["by_lead"][str(lead)]["test"]["quantile"]["mean_R_cm"],
        }
        for lead in (6, 18, 30, 60)
    }
    out = DATA / "p2_official_distance.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["headline"], indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
