# -*- coding: utf-8 -*-
"""A genuine TRAINED predictor for Question 2, so the backup paper has a
real fitted model with train/validation/test discipline — not only a
method-of-moments Kalman filter whose only "fitting" is a variance estimate.

The official statement (problem.txt lines 49-51) asks to use the training set
for parameter fitting, validation for model selection, test for evaluation,
and explicitly names "few parameters, such as a constant predictor or a simple
linear model" as a baseline.  This script supplies exactly that, on the SAME
clean prefix+mask windows and the SAME endpoint-error metric as the Kalman
filter in code/alt_p2_kalman.py, so every number is directly comparable.

Models (per mask horizon L in {6,12,18,30} frames):
  * ridge: a multi-output ridge regression from the flattened 6-frame prefix
    (6*63 = 378 features) to the endpoint DISPLACEMENT from the last visible
    frame (63 targets), wrapped in a StandardScaler pipeline.  Regularisation
    strength is selected on the validation split from a 6-point grid, and a
    5-fold GroupKFold (grouped by record) cross-validation on the training
    split is reported as an independent fitting-quality check.
  * linear-velocity: the few-parameter model named by the statement — a single
    scalar a(L) fitted by least squares on train, prediction
        tgt = last_visible + a(L) * (last_visible - previous_visible).
    This is the data-driven analogue of the Kalman damping factor alpha^L.

Nothing is claimed about which model wins until it is measured.  Both ridge and
linear-velocity are evaluated on the same capped-300 test windows that produced
Table~ref{tab:p2mask}.  Output: data/alt_p2_train.json.
"""
import os
import sys
import json
import math
import time
from datetime import datetime

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import alt_p2_kalman as K  # noqa: E402

from sklearn.linear_model import Ridge  # noqa: E402
from sklearn.neural_network import MLPRegressor  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

DATA = os.path.join(ROOT, "data")
MASK_LENGTHS = [6, 12, 18, 30]
ALPHA_GRID = [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]


def _xy(obs, tgt):
    """feature = flattened prefix; target = displacement from last visible frame."""
    X = obs.reshape(len(obs), -1).astype(np.float64)
    last = obs[:, -1, :].reshape(len(obs), -1)
    Y = tgt.reshape(len(tgt), -1) - last
    return X, Y, last


def _err_cm(pred_abs, tgt):
    e = np.linalg.norm(pred_abs.reshape(-1, 21, 3) - tgt.reshape(-1, 21, 3), axis=-1)
    return e * 100.0


def _summary(e):
    flat = e.ravel()
    return dict(mean_cm=round(float(flat.mean()), 3),
                rmse_cm=round(float(np.sqrt((flat ** 2).mean())), 3),
                median_cm=round(float(np.median(flat)), 3),
                p90_cm=round(float(np.percentile(flat, 90)), 3),
                wrist_cm=round(float(e[:, 0].mean()), 3),
                fingertips_cm=round(float(e[:, [4, 8, 12, 16, 20]].mean()), 3),
                n_windows=int(e.shape[0]))


def _windows(z, recs, L, R, dom, split, Lf, cap):
    o, t, r = K.windows_for(z, recs, L, R, dom, split, K.PREFIX, Lf, cap=cap)
    return o, t, r


def main():
    t0 = time.time()
    z, recs, L, R, dom = K.load_panel()
    out = dict(
        _meta=dict(
            title="Trained ridge / linear-velocity predictors for P2 (backup paper)",
            created=datetime.now().isoformat(timespec="seconds"),
            method="sklearn Ridge (StandardScaler + Ridge, multi-output) on flattened 6-frame prefix; "
                   "alpha selected on validation; 5-fold GroupKFold on train; "
                   "linear-velocity is a 1-parameter least-squares extrapolation",
            feature_dim=6 * 63, target_dim=63,
            alpha_grid=ALPHA_GRID,
            splits="train fit / validation model selection / test evaluation (official record_split.csv)",
            windows="clean prefix(6)+mask(L) windows, same as alt_p2_kalman.py; test capped at 300/split",
            metric="mean per-keypoint 3D endpoint error, cm (identical to tab:p2mask)",
            runtime_s=None),
        horizons={})

    for Lf in MASK_LENGTHS:
        # train: all windows (no cap); groups = record id for grouped CV
        otr, ttr, rtr = _windows(z, recs, L, R, dom, "train", Lf, cap=100000)
        ova, tva, rva = _windows(z, recs, L, R, dom, "validation", Lf, cap=100000)
        ote, tte, rte = _windows(z, recs, L, R, dom, "test", Lf, cap=K.CAP)
        Xtr, Ytr, ltr = _xy(otr, ttr)
        Xva, Yva, lva = _xy(ova, tva)
        Xte, Yte, lte = _xy(ote, tte)

        # --- validation-based model selection of the ridge penalty ---
        val_curve = []
        best = (None, 1e18)
        for a in ALPHA_GRID:
            m = make_pipeline(StandardScaler(), Ridge(alpha=a))
            m.fit(Xtr, Ytr)
            pv = lva + m.predict(Xva)
            ev = _err_cm(pv, tva)
            vm = float(ev.mean())
            val_curve.append(dict(alpha=a, val_mean_cm=round(vm, 3)))
            if vm < best[1]:
                best = (a, vm)
        alpha_star = best[0]

        # --- 5-fold GroupKFold cross-validation on train at alpha_star ---
        gkf = GroupKFold(n_splits=5)
        cv_means = []
        for ti, vi in gkf.split(Xtr, Ytr, groups=rtr):
            m = make_pipeline(StandardScaler(), Ridge(alpha=alpha_star))
            m.fit(Xtr[ti], Ytr[ti])
            pcv = ltr[vi] + m.predict(Xtr[vi])
            cv_means.append(float(_err_cm(pcv, ttr[vi]).mean()))

        # --- final ridge: refit on train, evaluate on test ---
        ridge = make_pipeline(StandardScaler(), Ridge(alpha=alpha_star))
        ridge.fit(Xtr, Ytr)
        pr = lte + ridge.predict(Xte)
        er = _err_cm(pr, tte)

        # --- split-conformal interval on the ridge (official "interval coverage") ---
        # Calibration = validation residuals (displacement in m, *100 -> cm);
        # score = per-window sup-norm over the 63 output coordinates. The conformal
        # radius q_hat is the (1-alpha)-quantile with finite-sample correction, so
        # a +/-q_hat box around the point forecast has >=1-alpha marginal coverage.
        res_va = (Yva - ridge.predict(Xva)) * 100.0             # (n_val,63) cm
        score_va = np.abs(res_va).max(axis=1)                    # (n_val,)
        alpha_conf = 0.10
        k = int(math.ceil((len(score_va) + 1) * (1 - alpha_conf)))
        q_hat = float(np.sort(score_va)[min(k, len(score_va)) - 1])
        res_te = (Yte - ridge.predict(Xte)) * 100.0
        covered = (np.abs(res_te).max(axis=1) <= q_hat + 1e-9)
        conf = dict(nominal=round(1 - alpha_conf, 2),
                    n_calibration=int(len(score_va)),
                    radius_cm=round(q_hat, 3),
                    box_width_cm=round(2 * q_hat, 3),
                    test_coverage=round(float(covered.mean()), 3),
                    n_test=int(len(covered)))

        # --- 1-parameter linear-velocity model, fit on train by least squares ---
        vel = (otr[:, -1, :] - otr[:, -2, :]).reshape(len(otr), -1)      # (n,63)
        disp = Ytr                                                       # (n,63)
        a_L = float(np.dot(vel.ravel(), disp.ravel()) / np.dot(vel.ravel(), vel.ravel()))
        vel_te = (ote[:, -1, :] - ote[:, -2, :]).reshape(len(ote), -1)
        p_lin = lte + a_L * vel_te
        el = _err_cm(p_lin, tte)

        # --- compact nonlinear model: does added capacity beat the linear ridge? ---
        # MLP with early stopping on an internal validation fraction of TRAIN only.
        # This is a deliberately small net; the question is whether nonlinearity
        # helps at all on horizon-dominated extrapolation, not to win a benchmark.
        mlp = make_pipeline(StandardScaler(),
                            MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=300,
                                         early_stopping=True, validation_fraction=0.15,
                                         random_state=7, learning_rate_init=1e-3))
        mlp.fit(Xtr, Ytr)
        en = _err_cm(lte + mlp.predict(Xte), tte)
        mlp_est = mlp[-1]

        # --- reference rows from the published Kalman table (same test windows) ---
        kp = json.load(open(os.path.join(DATA, "alt_p2.json"), encoding="utf-8"))
        krow = next(r for r in kp["mask_protocol"]["rows"] if r["L_frames"] == Lf)
        bl = next(r for r in kp["mask_protocol"]["baselines"]
                  if r["L_frames"] == Lf and r["method"] == "cv")

        out["horizons"][str(Lf)] = dict(
            L_s=round(Lf / K.FPS, 2), L_frames=Lf,
            n_train=int(len(otr)), n_val=int(len(ova)), n_test=int(len(ote)),
            alpha_star=alpha_star, val_curve=val_curve,
            cv5_mean_cm=round(float(np.mean(cv_means)), 3),
            cv5_fold_means_cm=[round(x, 3) for x in cv_means],
            ridge=_summary(er),
            conformal=conf,
            linear_velocity=dict(coef_a=round(a_L, 4), **_summary(el)),
            mlp=dict(hidden_layer_sizes=[64, 32], epochs=int(mlp_est.n_iter_),
                     final_loss=round(float(mlp_est.loss_), 6),
                     early_stopping=True, **_summary(en)),
            reference=dict(kalman_mean_cm=krow["mean_cm"],
                           kalman_rmse_cm=krow["rmse_cm"],
                           hold_mean_cm=next(r["mean_cm"] for r in kp["mask_protocol"]["baselines"]
                                             if r["L_frames"] == Lf and r["method"] == "hold"),
                           cv_mean_cm=bl["mean_cm"],
                           linear_fit_mean_cm=next(r["mean_cm"] for r in kp["mask_protocol"]["baselines"]
                                                   if r["L_frames"] == Lf and r["method"] == "linear")))

    # aggregate comparison for the paper
    comp = []
    for Lf in MASK_LENGTHS:
        h = out["horizons"][str(Lf)]
        comp.append(dict(L_s=h["L_s"],
                         kalman=h["reference"]["kalman_mean_cm"],
                         ridge=h["ridge"]["mean_cm"],
                         linear_velocity=h["linear_velocity"]["mean_cm"],
                         mlp=h["mlp"]["mean_cm"],
                         hold=h["reference"]["hold_mean_cm"],
                         cv=h["reference"]["cv_mean_cm"]))
    out["comparison"] = comp
    out["_meta"]["runtime_s"] = round(time.time() - t0, 1)

    path = os.path.join(DATA, "alt_p2_train.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", path, "runtime", out["_meta"]["runtime_s"], flush=True)
    for c in comp:
        print("  L=%.1fs  kalman=%.3f  ridge=%.3f  linvel=%.3f  mlp=%.3f  hold=%.3f  cv=%.3f" % (
            c["L_s"], c["kalman"], c["ridge"], c["linear_velocity"], c["mlp"],
            c["hold"], c["cv"]), flush=True)
    for Lf in MASK_LENGTHS:
        h = out["horizons"][str(Lf)]
        print("  L=%2d alpha*=%-6s cv5=%.3f  a(L)=%.4f  mlp_ep=%d mlp_loss=%.5f  n(tr/va/te)=%d/%d/%d" % (
            Lf, h["alpha_star"], h["cv5_mean_cm"], h["linear_velocity"]["coef_a"],
            h["mlp"]["epochs"], h["mlp"]["final_loss"],
            h["n_train"], h["n_val"], h["n_test"]), flush=True)


if __name__ == "__main__":
    main()
