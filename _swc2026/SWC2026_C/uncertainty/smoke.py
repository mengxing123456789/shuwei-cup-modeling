"""One-record end-to-end smoke chain.

record -> P1 reliability -> P2/P3 predictive distributions -> single-job
decision -> VoI. Writes data/uncertainty_smoke.json (new file; existing
data/*.json are read-only).
"""
from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .decision import Decider, JobSpec, ScheduleContext
from .jsonio import DATA, att_dir, write_json
from .predictive import DurationPredictor, PositionPredictor
from .reliability import ReliabilityModel
from .types import FrameWindow, PredictiveRequest, StepReport

UNIT_ID = "U_41540a43a2a7"   # validation, family A, sample E015, duration 3.0 s
SAMPLE = "E015"
CASE = "S1"
JOB_ID = "S1_J05"            # family A, release 20 s, due 55 s, weight 3, zone Z4


def _load_record(sample: str = SAMPLE) -> pd.Series:
    recs = pd.read_csv(DATA / "panel_records.csv")
    hit = recs[(recs["sample"] == sample) & (recs.dataset == "EgoDemo")]
    if len(hit) != 1:
        raise RuntimeError(f"expected exactly one record for {sample}, got {len(hit)}")
    return hit.iloc[0]


def _load_zones() -> dict[str, tuple[float, float]]:
    z = pd.read_csv(att_dir() / "service_zones.csv")
    return {str(r.zone_id): (float(r.x), float(r.y)) for r in z.itertuples()}


def _load_job(case: str, job_id: str) -> JobSpec:
    t = pd.read_csv(att_dir() / "tasks.csv")
    hit = t[(t.case_id == case) & (t.job_id == job_id)]
    if len(hit) != 1:
        raise RuntimeError(f"job {case}/{job_id} not found")
    r = hit.iloc[0]
    return JobSpec(
        job_id=str(r.job_id),
        case_id=str(r.case_id),
        family=str(r.family_id),
        release_s=float(r.release_s),
        due_s=float(r.due_s),
        weight=float(r.priority_weight),
        zone=str(r.zone_id),
        duration_true_s=None,
    )


def _timed(steps: list[StepReport], name: str, fn):
    t0 = time.perf_counter()
    value = fn()
    ms = (time.perf_counter() - t0) * 1000.0
    return value, ms


def run(data_dir: str | Path | None = None) -> dict[str, Any]:
    D = Path(data_dir or DATA)
    wall0 = time.perf_counter()
    rec = _load_record()
    record_id = int(rec.rec)
    fps = float(rec.fps)
    zones = _load_zones()
    unit_row = pd.read_csv(D / "p3_duration_predictions.csv").query(
        "unit_id == @UNIT_ID and prefix == 0.2"
    ).iloc[0]

    t_fit0 = time.perf_counter()
    rel = ReliabilityModel(D)
    fit_ms = (time.perf_counter() - t_fit0) * 1000.0

    steps: list[StepReport] = []
    windows = {
        "0.2": FrameWindow(record_id, 0, int(round(0.2 * fps)), fps),
        "0.6": FrameWindow(record_id, 0, int(round(0.6 * fps)), fps),
        "1.0": FrameWindow(record_id, 0, int(round(1.0 * fps)), fps),
    }

    def _rel_step():
        out = {}
        for tag, w in windows.items():
            frames = rel.frame_reliability(w)
            dom = rel.resolve_hand(record_id, None)
            seg_dom = rel.segment(w, hand=None)
            seg_l = rel.segment(w, hand="L")
            seg_r = rel.segment(w, hand="R")
            out[tag] = {
                "window": w.as_dict(),
                "dominant_hand": dom,
                "frames": {h: frames[h].as_dict() for h in ("L", "R")},
                "segment_dominant": seg_dom.as_dict(),
                "segment_L": seg_l.as_dict(),
                "segment_R": seg_r.as_dict(),
            }
        return out

    rel_out, rel_ms = _timed(steps, "P1 reliability", _rel_step)
    steps.append(StepReport("P1 reliability (3 windows)", rel_ms, {"windows": list(rel_out)}))

    ctx02 = rel.segment(windows["0.2"], hand=None).as_context()
    ctx06 = rel.segment(windows["0.6"], hand=None).as_context()
    ctx10 = rel.segment(windows["1.0"], hand=None).as_context()

    dp = DurationPredictor(D)
    pp = PositionPredictor(D)

    def _pred_step():
        base = PredictiveRequest(UNIT_ID, "A", 0.2, reliability=None, representation="quantile")
        cond = PredictiveRequest(UNIT_ID, "A", 0.2, reliability=ctx02, representation="quantile")
        reps = dp.all_representations(cond)
        nxt = dp.distribution(
            PredictiveRequest(UNIT_ID, "A", 0.6, reliability=ctx06, representation="quantile")
        )
        pos = pp.radial(0.2, reliability=ctx02, representation="lognormal")
        pos_neutral = pp.radial(0.2, reliability=None, representation="lognormal")
        return {
            "neutral": dp.distribution(base),
            "conditioned": reps,
            "next_prefix": nxt,
            "position": pos,
            "position_neutral": pos_neutral,
        }

    pred, pred_ms = _timed(steps, "P2/P3 predictive", _pred_step)
    steps.append(StepReport("P2/P3 distributions", pred_ms, {"representations": list(pred["conditioned"])}))

    job = _load_job(CASE, JOB_ID)
    sctx = ScheduleContext(
        now_s=0.0,
        horizon_s=100.0,
        budget_s=32.0,
        spent_s=0.0,
        current_zone="Z0",
        alpha=1.0,
        beta=0.5,
        reserve_min=0.2,
        speed=1.0,
        changeover_s=0.5,
        review_delay_s=1.0,
        review_cost_s=1.0,
        shadow_price=0.02,
        pressure_override=None,
        zones=zones,
    )

    def _decision_step():
        d = Decider().decide(job, pred["conditioned"]["quantile"], sctx)
        v = Decider().voi(job, pred["neutral"], pred["next_prefix"], d.start_s, sctx)
        return d, v

    (dec, voi), dec_ms = _timed(steps, "single-job decision + VoI", _decision_step)
    steps.append(StepReport("Decider.decide + Decider.voi", dec_ms, {"action": dec.action, "voi": voi.net_value}))

    # Synthetic stress points: not official dues, used only to show the
    # risk-sensitive branch where P(late) is interior and VoI can change sign.
    def _stress_step():
        scan = []
        for qv in (0.3, 0.5, 0.7, 0.85, 0.95):
            due = float(dec.start_s + pred["neutral"].quantile(qv))
            j = replace(job, due_s=due)
            d = Decider().decide(j, pred["conditioned"]["quantile"], sctx)
            v = Decider().voi(j, pred["neutral"], pred["next_prefix"], d.start_s, sctx)
            scan.append(
                {
                    "quantile_of_neutral": float(qv),
                    "due_s": due,
                    "p0": v.p0,
                    "p1": v.p1,
                    "net_value": v.net_value,
                    "decided": v.decided,
                }
            )
        mid = scan[1]
        j = replace(job, due_s=float(mid["due_s"]))
        d = Decider().decide(j, pred["conditioned"]["quantile"], sctx)
        v = Decider().voi(j, pred["neutral"], pred["next_prefix"], d.start_s, sctx)
        return j, d, v, scan

    stress_job, stress_dec, stress_voi, voi_scan = _stress_step()

    total_ms = (time.perf_counter() - wall0) * 1000.0
    timings = {
        "model_fit_ms": fit_ms,
        "chain_total_ms_including_fit": total_ms,
        "P1_reliability_ms": rel_ms,
        "P2_P3_predictive_ms": pred_ms,
        "decision_voi_ms": dec_ms,
        "steps": [s.as_dict() for s in steps],
    }

    out: dict[str, Any] = {
        "meta": {
            "track": "U / unified uncertainty chain",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "interpreter": "E:\\Mini\\envs\\mathmodel\\python.exe",
            "sources_read_only": [
                "data/panel.npz",
                "data/state.npz",
                "data/panel_records.csv",
                "data/feature_names.json",
                "data/p1_reliability.json",
                "data/p2_interval.json",
                "data/p2_gpu.json",
                "data/p3_duration_predictions.csv",
                "data/p1b_gpu.json",
            ],
            "new_products": ["data/uncertainty_smoke.json", "data/uncertainty_consistency.json", "data/uncertainty_reliability.json"],
        },
        "record": {
            "record_id": record_id,
            "dataset": str(rec.dataset),
            "sample": str(rec["sample"]),
            "env": str(rec.env),
            "split": str(rec.split),
            "n_frames": int(rec.n),
            "fps": fps,
            "duration_s": float(rec.dur),
            "segment_0": {"start_s": 0.0, "end_s": 3.0, "duration_s": 3.0},
        },
        "unit": {
            "unit_id": UNIT_ID,
            "family": str(unit_row.family),
            "duration_s": float(unit_row.duration),
            "pred_prefix_0.2_s": float(unit_row.pred),
            "split": str(unit_row.split),
            "why_this_unit": "validation family-A unit whose 3.0 s duration equals record 14 segment 0 (0-3 s); prefix 0.2/0.6/1.0 maps to the first 6/18/30 frames",
        },
        "reliability": {
            "model": "rebuilt p1_model.py + validation calibration",
            "calibrator": rel.calibrator.name,
            "calibrator_candidates_validation": rel.calibrator_rows,
            "metrics": rel.metrics(),
            "reference_p1_reliability": rel.card()["reference_p1_reliability"],
            "contexts": {"0.2": ctx02.as_dict(), "0.6": ctx06.as_dict(), "1.0": ctx10.as_dict()},
            "windows": rel_out,
            "placeholder_neural": rel.card()["placeholder_neural"],
        },
        "predictive": {
            "duration_target": "service_duration_s",
            "neutral": pred["neutral"].summary(),
            "conditioned_quantile": pred["conditioned"]["quantile"].summary(),
            "conditioned_empirical": pred["conditioned"]["empirical"].summary(),
            "conditioned_gaussian": pred["conditioned"]["gaussian"].summary(),
            "next_prefix_0.6": pred["next_prefix"].summary(),
            "conditioning": {
                "r_seg": ctx02.r_seg,
                "kappa": 1.0,
                "factor": pred["conditioned"]["quantile"].meta["reliability_factor"],
                "variance_ratio": pred["conditioned"]["quantile"].meta["variance_ratio"],
                "coupling": "variance factor = 1 + kappa*(1-r)/r applied to residual pool, not to a Gaussian sigma",
            },
            "position_target": "radial_position_error_m",
            "position_conditioned": pred["position"].summary(),
            "position_neutral": pred["position_neutral"].summary(),
            "position_gpu_reference": pp.gpu_reference(),
        },
        "decision": {
            "job": job.as_dict(),
            "context": sctx.as_dict(),
            "result": dec.as_dict(),
            "distribution_kind": pred["conditioned"]["quantile"].kind,
            "note": "Decider consumes PredictiveDistribution only; pred point estimate is never passed",
        },
        "voi": {
            "job": job.as_dict(),
            "report": voi.as_dict(),
            "start_s": dec.start_s,
            "why": "p0 from neutral prefix-0.2 distribution, p1 from prefix-0.6 distribution already conditioned on the longer window; gain is w*(p1-p0) minus shadow price",
        },
        "stress_synthetic": {
            "label": "SYNTHETIC sensitivity, not an official due",
            "job": stress_job.as_dict(),
            "decision": stress_dec.as_dict(),
            "voi": stress_voi.as_dict(),
            "voi_scan": voi_scan,
            "scan_note": "due = official start + quantile of the neutral prefix-0.2 distribution; p0 neutral, p1 prefix-0.6 conditioned on the longer window",
        },
        "timings_ms": timings,
        "degradation": [
            {
                "component": "P1b TCN",
                "status": "PLACEHOLDER",
                "reason": "code/train_gpu_p1b.py writes data/p1b_gpu.json only; no .pt checkpoint exists",
                "fallback": "calibrated logistic + Mahalanobis fusion (rebuilt p1_model.py)",
                "reference_test_auc": 0.82203,
            },
            {
                "component": "P2 GPU GRU",
                "status": "PLACEHOLDER",
                "reason": "code/train_gpu_p2.py writes data/p2_gpu.json only; no .pt checkpoint exists",
                "fallback": "ridge/conformal P2 radial error from data/p2_interval.json",
                "reference": "data/p2_gpu.json v2 endpoint rows are aggregate only",
            },
            {
                "component": "P2 -> P3 coupling",
                "status": "OPEN",
                "reason": "no measured mapping from radial position error to annotation duration; not wired",
                "fallback": "P3 duration distribution uses its own residual pool; P1 reliability only widens it",
            },
        ],
    }
    write_json(D / "uncertainty_smoke.json", out)
    rel.save_card(D / "uncertainty_reliability.json")
    return out


if __name__ == "__main__":
    o = run()
    print(json.dumps({
        "wrote": str(DATA / "uncertainty_smoke.json"),
        "calibrator": o["reliability"]["calibrator"],
        "r_seg_0.2": o["reliability"]["contexts"]["0.2"]["r_seg"],
        "p_on_time": o["decision"]["result"]["p_on_time"],
        "voi_net": o["voi"]["report"]["net_value"],
        "total_ms": o["timings_ms"]["chain_total_ms_including_fit"],
    }, ensure_ascii=False, indent=2))