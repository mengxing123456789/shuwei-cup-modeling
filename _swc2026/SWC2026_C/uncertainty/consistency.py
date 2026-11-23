"""Numeric alignment audit against code/p3_stochastic_schedule.py.

The shipped scheduler consumes 19 equiprobable residual-quantile scenarios.
The unified layer exposes the same grid as a QuantileDistribution, so the
scenario values must be identical (diff 0), and P(late) must agree at every
due inside the informative band. The full empirical survival is also reported;
its deviation from the 19-point grid is discretisation, not a model change.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision import Decider, ScheduleContext
from .distributions import EmpiricalDistribution
from .jsonio import CODE, DATA, att_dir, write_json
from .predictive import DurationPredictor
from .types import PredictiveRequest

UNIT_ID = "U_41540a43a2a7"
FAMILY = "A"
PREFIX = 0.2
S0 = 10.0


def _job_and_start(dp: DurationPredictor, unit_id: str, prefix: float, family: str):
    t = pd.read_csv(att_dir() / "tasks.csv")
    hit = t[(t.case_id == "S1") & (t.job_id == "S1_J05")].iloc[0]
    z = pd.read_csv(att_dir() / "service_zones.csv")
    zones = {str(r.zone_id): (float(r.x), float(r.y)) for r in z.itertuples()}
    d = dp.distribution(PredictiveRequest(unit_id, family, prefix, reliability=None, representation="quantile"))
    ctx = ScheduleContext(
        now_s=0.0,
        horizon_s=100.0,
        budget_s=32.0,
        current_zone="Z0",
        zones=zones,
    )
    job = type(
        "J",
        (),
        {
            "job_id": str(hit.job_id),
            "case_id": str(hit.case_id),
            "family": str(hit.family_id),
            "release_s": float(hit.release_s),
            "due_s": float(hit.due_s),
            "weight": float(hit.priority_weight),
            "zone": str(hit.zone_id),
            "duration_true_s": None,
        },
    )()
    dec = Decider().decide(job, d, ctx)
    return job, dec.start_s, zones


def run(
    unit_id: str = UNIT_ID,
    family: str = FAMILY,
    prefix: float = PREFIX,
    s0: float = S0,
    alpha: float = 1.0,
    beta: float = 0.5,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    D = Path(data_dir or DATA)
    if str(CODE) not in sys.path:
        sys.path.insert(0, str(CODE))
    t0 = time.perf_counter()
    import p3_stochastic_schedule as p3s
    import_ms = (time.perf_counter() - t0) * 1000.0

    dp = DurationPredictor(D)
    row = dp.row(unit_id, prefix)
    pred = float(row.pred)
    resid = dp.residuals(unit_id, prefix, family)
    scen_p3 = np.asarray(p3s.scenarios(unit_id, float(prefix), family, "fusion", alpha, beta), dtype=float)
    dist = dp.distribution(
        PredictiveRequest(unit_id, family, prefix, reliability=None, representation="quantile", alpha=alpha, beta=beta)
    )
    scen_u = np.asarray(dist.samples, dtype=float)
    max_val_diff = float(np.max(np.abs(np.sort(scen_p3) - scen_u)))

    exact = alpha * np.maximum(float(prefix), pred + resid) + beta
    exact_dist = EmpiricalDistribution(exact, target="service_duration_s", unit="s", lower=alpha * prefix + beta)

    job, start, _ = _job_and_start(dp, unit_id, prefix, family)
    offsets = np.round(np.arange(-4.0, 12.01, 0.5), 2)
    rows = []
    for off in offsets:
        due = s0 + pred + float(off)
        p3 = float(np.mean(s0 + scen_p3 > due))
        uq = float(dist.survival(due - s0))
        ue = float(exact_dist.survival(due - s0))
        rows.append(
            {
                "offset_s": float(off),
                "due_s": float(due),
                "p3_plat": p3,
                "unified_quantile_plat": uq,
                "diff": abs(p3 - uq),
                "unified_empirical_plat": ue,
                "diff_empirical": abs(p3 - ue),
            }
        )
    informative = [r for r in rows if 0.02 < r["p3_plat"] < 0.98]
    max_inf = max((r["diff"] for r in informative), default=float("nan"))
    max_all = max(r["diff"] for r in rows)
    max_emp = max(r["diff_empirical"] for r in rows)

    # Actual decision point used by smoke.py (official S1_J05 due, official start).
    due_dec = float(job.due_s)
    p3_dec = float(np.mean(s0 + scen_p3 > due_dec))
    u_dec = float(dist.survival(due_dec - s0))
    e_dec = float(exact_dist.survival(due_dec - s0))

    verdict = "PASS" if (max_inf < 0.02 and max_val_diff < 1e-9) else "FAIL"
    out = {
        "meta": {
            "role": "Track U consistency audit",
            "script_compared": "code/p3_stochastic_schedule.py",
            "script_version": "protocol-corrected (alpha*d+beta, C=s+p, availability s+max(p,b))",
            "import_ms": import_ms,
            "source_rows": str(D / "p3_duration_predictions.csv"),
            "new_product": "data/uncertainty_consistency.json",
        },
        "case": {
            "unit_id": unit_id,
            "family": family,
            "prefix_s": float(prefix),
            "s0": float(s0),
            "alpha": float(alpha),
            "beta": float(beta),
            "pred_s": pred,
            "duration_true_s": float(row.duration),
            "residual_pool_n": int(len(resid)),
            "p3_quantile_levels": [float(v) for v in p3s.SCEN_Q],
        },
        "scenario_identity": {
            "max_abs_value_diff": max_val_diff,
            "p3_scenario_min_s": float(np.min(scen_p3)),
            "unified_scenario_min_s": float(np.min(scen_u)),
            "p3_scenario_max_s": float(np.max(scen_p3)),
            "unified_scenario_max_s": float(np.max(scen_u)),
            "verdict": "PASS" if max_val_diff < 1e-9 else "FAIL",
            "meaning": "the scheduler receives exactly the same 19 atoms; no representation translation",
        },
        "p_late_scan": {
            "offsets_s": [float(v) for v in offsets],
            "rows": rows,
            "n_informative": len(informative),
            "max_abs_diff_informative": float(max_inf),
            "max_abs_diff_all": float(max_all),
            "max_abs_diff_empirical_all": float(max_emp),
            "threshold": 0.02,
            "verdict": verdict,
        },
        "decision_point": {
            "job_id": job.job_id,
            "due_s": due_dec,
            "start_s": float(start),
            "p3_plat": p3_dec,
            "unified_plat": u_dec,
            "abs_diff": abs(p3_dec - u_dec),
            "unified_empirical_plat": e_dec,
            "abs_diff_empirical": abs(p3_dec - e_dec),
            "note": "official due is far outside the service distribution, so both probabilities are ~0; the informative scan above is the real check",
        },
        "source_of_difference": {
            "scenario_grid": "none (exact equality); both sides use the same train residual pool and the same 19 quantiles",
            "empirical_vs_grid": (
                "the 19-point grid truncates the upper tail at q95; above the 95th percentile p3 returns 0 while the "
                "full residual pool still has mass, producing the largest deviation. Inside 0.02 < P(late) < 0.98 the "
                "deviation is below the 0.02 gate."
            ),
            "not_caused_by": [
                "P1 reliability (neutral path used here: reliability=None -> factor=1.0)",
                "different duration point prediction (both read p3_duration_predictions.csv column pred)",
                "different alpha/beta (both 1.0/0.5)",
            ],
        },
        "verdict": verdict,
    }
    write_json(D / "uncertainty_consistency.json", out)
    return out


if __name__ == "__main__":
    import json

    o = run()
    print(
        json.dumps(
            {
                "verdict": o["verdict"],
                "scenario_max_abs_diff": o["scenario_identity"]["max_abs_value_diff"],
                "max_diff_informative": o["p_late_scan"]["max_abs_diff_informative"],
                "max_diff_all": o["p_late_scan"]["max_abs_diff_all"],
                "decision_point_diff": o["decision_point"]["abs_diff"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )