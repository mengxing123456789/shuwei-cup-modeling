"""P1 interface: calibrated per-frame trust -> segment reliability.

This is a faithful rebuild of code/p1_model.py (same features, same stacking,
same C=0.1 balanced logistic, same Mahalanobis geometry), plus the two pieces
p1_model.py did not ship: a calibrator selected on validation and an explicit
frame->segment aggregation with an effective sample size.

Reference metrics are read from data/p1_reliability.json (read-only).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import calibration
from .jsonio import DATA, jsonable
from .types import (
    FrameReliability,
    FrameWindow,
    ReliabilityContext,
    SegmentReliability,
    aggregate_frames,
)

FEATURES = [
    "L_collinearity",
    "L_bone_cv",
    "L_min_gap",
    "L_bbox_vol",
    "L_z_std",
    "L_palm_width",
    "L_jump",
    "L_jump_max",
    "jump_mean5",
    "jump_max_mean5",
]


def add_context(X: np.ndarray) -> np.ndarray:
    """Replicates p1_model.add_context: 5-frame trailing mean of cols 6,7."""
    out = [X]
    for j in (6, 7):
        c = np.convolve(X[:, j], np.ones(5) / 5.0, mode="same")
        out.append(c[:, None])
    return np.hstack(out)


class ReliabilityModel:
    """Fit once, then answer (record, window, hand) queries."""

    def __init__(self, data_dir: str | Path | None = None, ar1_rho: float = 0.6) -> None:
        self.D = Path(data_dir or DATA)
        self.ar1_rho = float(ar1_rho)
        self._load()
        self._fit()
        self._calibrate()

    # ------------------------------------------------------------------ load
    def _load(self) -> None:
        z = np.load(os.path.join(self.D, "state.npz"))
        self.gl = z["gl"].astype(float)
        self.gr = z["gr"].astype(float)
        self.badL = z["badL"].astype(int)
        self.badR = z["badR"].astype(int)
        self.rec = z["rec"].astype(int)
        self.n_rows = int(len(self.rec))
        self.recs = pd.read_csv(os.path.join(self.D, "panel_records.csv"))
        self.row_of = {int(r): np.flatnonzero(self.rec == int(r)) for r in self.recs.rec}
        self.split_of = {int(r.rec): str(r.split) for r in self.recs.itertuples()}
        self.env_of = {int(r.rec): str(r.env) for r in self.recs.itertuples()}
        self.fps_of = {int(r.rec): float(r.fps) for r in self.recs.itertuples()}
        names = json.load(open(os.path.join(self.D, "feature_names.json"), encoding="utf-8"))
        dom = names.get("dominant", {})
        self.dom_hand = {int(k): str(v) for k, v in dom.items()}
        if not self.dom_hand:
            dom_i = z["dom"]
            self.dom_hand = {int(r): ("R" if int(dom_i[i]) else "L") for i, r in enumerate(self.recs.rec)}
        self.p1_ref = json.load(open(os.path.join(self.D, "p1_reliability.json"), encoding="utf-8"))
        self._rows_by_split: dict[str, list[tuple[np.ndarray, str]]] = {}

    # ------------------------------------------------------------------- fit
    def _build_split(self, split: str) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[str], np.ndarray]:
        rec_list = [int(r) for r in self.recs.rec if self.split_of[int(r)] == split]
        Xs, ys, rows, hands, rec_ids = [], [], [], [], []
        for r in rec_list:
            ii = self.row_of[r]
            for h, X, b in (("L", self.gl, self.badL), ("R", self.gr, self.badR)):
                Xs.append(X[ii])
                ys.append(b[ii])
                rows.append(ii)
                hands.append(h)
                rec_ids.append(np.full(len(ii), r))
        X = np.vstack(Xs)
        y = np.concatenate(ys).astype(int)
        Xc = add_context(X)
        return Xc, y, rows, hands, np.concatenate(rec_ids)

    def _fit(self) -> None:
        splits = ("train", "validation", "test")
        built = {s: self._build_split(s) for s in splits}
        Xtr, ytr = built["train"][0], built["train"][1]
        self.scaler = StandardScaler().fit(Xtr)
        Ztr = self.scaler.transform(Xtr)
        self.clf = LogisticRegression(
            C=0.1, class_weight="balanced", max_iter=5000, solver="liblinear"
        ).fit(Ztr, ytr)
        self.cov = np.cov(Ztr.T) + np.eye(Ztr.shape[1]) * 1e-6
        self.cov_inv = np.linalg.pinv(self.cov)

        self.p_raw = {"L": np.full(self.n_rows, np.nan), "R": np.full(self.n_rows, np.nan)}
        self.p_bad = {"L": np.full(self.n_rows, np.nan), "R": np.full(self.n_rows, np.nan)}
        self.r_geo = {"L": np.full(self.n_rows, np.nan), "R": np.full(self.n_rows, np.nan)}
        self.r_fused = {"L": np.full(self.n_rows, np.nan), "R": np.full(self.n_rows, np.nan)}
        self.y = np.full(self.n_rows, -1, dtype=int)
        self.split_tag = np.full(self.n_rows, "", dtype=object)
        self.env_tag = np.full(self.n_rows, "", dtype=object)

        p_parts, y_parts, split_parts, row_parts, hand_parts = [], [], [], [], []
        for s in splits:
            Xc, y, rows, hands, rec_ids = built[s]
            Z = self.scaler.transform(Xc)
            p = self.clf.predict_proba(Z)[:, 1]
            d2 = np.einsum("ij,jk,ik->i", Z, self.cov_inv, Z)
            if s == "train":
                self.median_d2 = float(np.median(d2))
            rg = np.exp(-0.5 * d2 / self.median_d2)
            pos = 0
            for ii, h in zip(rows, hands):
                n = len(ii)
                yy = y[pos : pos + n]
                pp = p[pos : pos + n]
                gg = rg[pos : pos + n]
                rr = rec_ids[pos : pos + n]
                pos += n
                self.p_raw[h][ii] = pp
                self.r_geo[h][ii] = gg
                self.y[ii] = yy
                self.split_tag[ii] = s
                self.env_tag[ii] = self.env_of[int(rr[0])]
            p_parts.append(p)
            y_parts.append(y)
            split_parts.append(np.full(len(y), s, dtype=object))
            row_parts.append(np.concatenate(rows))
            hand_parts.append(np.concatenate([np.full(len(ii), h, dtype=object) for ii, h in zip(rows, hands)]))
        self._p_all = np.concatenate(p_parts)
        self._y_all = np.concatenate(y_parts)
        self._split_all = np.concatenate(split_parts)
        self._rows_all = np.concatenate(row_parts)
        self._hands_all = np.concatenate(hand_parts)

    # ------------------------------------------------------------ calibration
    def _calibrate(self) -> None:
        m = self._split_all == "validation"
        self.calibrator, self.calibrator_rows = calibration.choose_calibrator(
            self._p_all[m], self._y_all[m]
        )
        p_cal = self.calibrator.apply(self._p_all)
        self.p_cal_all = p_cal
        for ii, h, pp in zip(self._rows_all, self._hands_all, p_cal):
            self.p_bad[h][ii] = pp
            self.r_fused[h][ii] = 0.5 * (1.0 - pp) + 0.5 * self.r_geo[h][ii]

    # ------------------------------------------------------------------ query
    def rows_for(self, window: FrameWindow) -> np.ndarray:
        base = self.row_of.get(int(window.record_id))
        if base is None:
            raise KeyError(f"record {window.record_id} not in panel")
        if window.end > len(base):
            raise ValueError(f"window end {window.end} > record length {len(base)}")
        return base[window.start : window.end]

    def resolve_hand(self, record_id: int, hand: str | None) -> str:
        if hand in ("L", "R"):
            return str(hand)
        if hand in (None, "dominant"):
            return self.dom_hand[int(record_id)]
        raise ValueError(f"unknown hand selector: {hand}")

    def frame_reliability(self, window: FrameWindow, hands: Iterable[str] = ("L", "R")) -> dict[str, FrameReliability]:
        ii = self.rows_for(window)
        out: dict[str, FrameReliability] = {}
        for h in hands:
            if h not in ("L", "R"):
                raise ValueError(f"unknown hand: {h}")
            out[h] = FrameReliability(
                record_id=window.record_id,
                hand=h,
                frame_index=ii.copy(),
                p_bad_raw=self.p_raw[h][ii].copy(),
                p_bad=self.p_bad[h][ii].copy(),
                r_geo=self.r_geo[h][ii].copy(),
                r=self.r_fused[h][ii].copy(),
                calibrator=self.calibrator.name,
                source="rebuilt p1_model.py (logistic + Mahalanobis), calibrated on validation",
                placeholder=False,
                meta={"window": window.as_dict(), "neural_branch": "PLACEHOLDER"},
            )
        return out

    def segment(
        self, window: FrameWindow, hand: str | None = None, method: str = "geometric"
    ) -> SegmentReliability:
        h = self.resolve_hand(window.record_id, hand)
        ii = self.rows_for(window)
        agg = aggregate_frames(
            self.r_fused[h][ii], self.p_bad[h][ii], method=method, ar1_rho=self.ar1_rho
        )
        return SegmentReliability(
            record_id=window.record_id,
            hand=h,
            start=window.start,
            end=window.end,
            fps=window.fps,
            r_seg=agg["r_seg"],
            r_mean=agg["r_mean"],
            r_geo=agg["r_geo"],
            r_min=agg["r_min"],
            p_bad_seg=agg["p_bad_seg"],
            p_any_bad_indep=agg["p_any_bad_indep"],
            p_any_bad_eff=agg["p_any_bad_eff"],
            n_frames=agg["n_frames"],
            n_eff=agg["n_eff"],
            aggregation=agg["aggregation"],
            calibrator=self.calibrator.name,
            source="P1 frame model rebuilt from code/p1_model.py",
            placeholder=False,
            meta={"ar1_rho": self.ar1_rho, "neural_branch": "PLACEHOLDER"},
        )

    def context(
        self, window: FrameWindow, hand: str | None = None, method: str = "geometric"
    ) -> ReliabilityContext:
        return self.segment(window, hand=hand, method=method).as_context()

    # ------------------------------------------------------------------- card
    def metrics(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for s in ("train", "validation", "test"):
            m = self._split_all == s
            y = self._y_all[m]
            rg = self.r_geo_all(s)
            p_raw = self._p_all[m]
            fu = 0.5 * self.p_cal_all[m] + 0.5 * (1.0 - rg)
            fu_raw = 0.5 * p_raw + 0.5 * (1.0 - rg)
            out[s] = {
                "calibrated": calibration.scorecard(y, self.p_cal_all[m]),
                "raw_logistic_auc": calibration.auc(y, p_raw),
                "geometry_auc": calibration.auc(y, -rg),
                "fused_auc": calibration.auc(y, fu),
                "fused_ap": calibration.ap(y, fu),
                "fused_auc_raw_p_mix": calibration.auc(y, fu_raw),
                "fused_ap_raw_p_mix": calibration.ap(y, fu_raw),
                "base_rate": float(np.mean(y)),
            }
        return out

    def r_geo_all(self, split: str) -> np.ndarray:
        m = self._split_all == split
        rows = self._rows_all[m]
        hands = self._hands_all[m]
        return np.asarray([self.r_geo[h][ii] for ii, h in zip(rows, hands)], dtype=float)

    def per_env_test(self) -> list[dict[str, Any]]:
        rows = []
        m = self._split_all == "test"
        env_all = self.env_tag[self._rows_all]
        for env in sorted(set(env_all[m])):
            em = m & (env_all == env)
            if int(np.sum(self._y_all[em])) < 5:
                continue
            rows.append(
                {
                    "env": env,
                    "n": int(np.sum(em)),
                    "positives": int(np.sum(self._y_all[em])),
                    "auc_calibrated": calibration.auc(self._y_all[em], self.p_cal_all[em]),
                }
            )
        return rows

    def card(self) -> dict[str, Any]:
        coef = {n: float(v) for n, v in zip(FEATURES, self.clf.coef_[0])}
        ref_coef = self.p1_ref.get("coef", {})
        coef_diff = {
            n: abs(coef[n] - float(ref_coef[n])) for n in FEATURES if n in ref_coef
        }
        metrics = self.metrics()
        ref_test = float(self.p1_ref.get("auc_bad_calibrated", {}).get("test", float("nan")))
        ref_fused = float(self.p1_ref.get("auc_bad_fused", {}).get("test", float("nan")))
        return {
            "_meta": {
                "role": "P1 reliability interface",
                "source": "rebuilt from code/p1_model.py; reference data/p1_reliability.json",
                "n_frames_total": self.n_rows,
                "features": FEATURES,
                "label": "annotated hand bad frame (occlusion/edge)",
                "calibration_fit_split": "validation",
                "auc_convention": "AUC_bad: higher means better ranking of bad frames",
            },
            "coef": coef,
            "intercept": float(self.clf.intercept_[0]),
            "scaler_mean": [float(v) for v in self.scaler.mean_],
            "scaler_scale": [float(v) for v in self.scaler.scale_],
            "mahalanobis": {"median_d2_train": self.median_d2, "cov_regularizer": 1e-6},
            "calibration": {
                "chosen": self.calibrator.name,
                "params": self.calibrator.card()["params"],
                "candidates_validation": self.calibrator_rows,
            },
            "metrics": metrics,
            "reference_p1_reliability": {
                "auc_bad_calibrated_test": ref_test,
                "auc_bad_fused_test": ref_fused,
                "delta_calibrated_test": (metrics["test"]["raw_logistic_auc"] - ref_test)
                if metrics["test"]["raw_logistic_auc"] is not None
                else None,
                "delta_fused_raw_mix_test": (metrics["test"]["fused_auc_raw_p_mix"] - ref_fused)
                if metrics["test"]["fused_auc_raw_p_mix"] is not None
                else None,
                "delta_fused_calibrated_mix_test": (metrics["test"]["fused_auc"] - ref_fused)
                if metrics["test"]["fused_auc"] is not None
                else None,
                "fusion_note": (
                    "p1_reliability.json mixed the raw (uncalibrated) logistic p with r_geo at 50/50. "
                    "Replacing p by a monotone calibrated probability keeps AUC of that branch identical "
                    "but changes the scale of the 50/50 mixture, so the fused AUC moves toward the geometry "
                    "branch. Raw-mix AUC reproduces the reference exactly; calibrated-mix AUC is the honest "
                    "number for the calibrated interface."
                ),
                "coef_max_abs_diff": max(coef_diff.values()) if coef_diff else None,
                "coef_diff_by_name": coef_diff,
            },
            "per_env_test": self.per_env_test(),
            "placeholder_neural": {
                "status": "PLACEHOLDER",
                "reason": "code/train_gpu_p1b.py saves only data/p1b_gpu.json; no .pt checkpoint exists",
                "fallback": "calibrated logistic + Mahalanobis fusion implemented here",
                "reference_test_auc": 0.82203,
                "source": "data/p1b_gpu.json",
            },
        }

    def save_card(self, path: str | Path = "uncertainty_reliability.json") -> Path:
        from .jsonio import write_json

        return write_json(path, self.card())