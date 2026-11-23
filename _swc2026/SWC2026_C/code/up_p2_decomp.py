# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 error decomposition: how much of the 1.0 s error is systematic (fixable) vs
positionally irreducible, for the ridge baseline and the quantile model.

Reads the prediction dumps written by up_p2_quantile.py
(data/up_p2_{ridge,quantile}_pred_L{L}.npz) and recomputes nothing that was
already trained.  Extra probes (context-length sweep, cross-domain transfer) are
ridge-only and refit on train/validation inside this script.

Definitions (all in cm; 3-D Euclidean RMS = 100*sqrt(mean(||e||^2))):
  between_record_share : share of total squared error carried by differences in
                         per-record mean MSE (i.e. "some scenes are harder").
  fixable(X)           : 1 - MSE_after_removing_X / MSE_before, where X is an
                         oracle correction estimated on the TEST split itself
                         (upper bound on what calibration could ever recover).
  irreducible          : remaining 3-D RMS after removing the per-(record,horizon)
                         mean error vector -- the strictest oracle available to a
                         scene-calibrated forecaster, so its floor is what no
                         amount of bias correction can touch.
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
LENS = [6, 18, 30, 60]
CTX_PROBE = [5, 10, 20, 30]
PROBE_L = 30


def load_npz(path):
    z = np.load(path)
    return {k: z[k] for k in z.files}


def error(pred, tgt):
    return pred.astype(np.float64) - tgt.astype(np.float64)


def block(e, rec, env_group, tag):
    """e: (N,L,3) residual; rec: (N,) record id; env_group: (N,) string."""
    N, L, _ = e.shape
    mse = float(np.mean(np.sum(e ** 2, axis=2)))              # m^2, per (window,horizon)
    n3 = np.linalg.norm(e, axis=2)                            # (N,L) m
    tot_cm2 = mse * 1e4

    # --- between / within variance of per-window squared error -------------
    w_mse = np.mean(np.sum(e ** 2, axis=2), axis=1)           # (N,) per-window
    rec_mean = np.array([w_mse[rec == r].mean() for r in np.unique(rec)])
    rec_w = np.array([(rec == r).sum() / N for r in np.unique(rec)])
    between_rec = float(np.sum(rec_w * (rec_mean - w_mse.mean()) ** 2))

    h_mse = np.mean(np.sum(e ** 2, axis=2), axis=0)           # (L,) per-horizon
    # interaction: per (record, horizon) cell mean
    cells = {}
    for r in np.unique(rec):
        m = rec == r
        cells[int(r)] = h_mse * 0 + np.mean(np.sum(e[m] ** 2, axis=2), axis=0)
    cell_mean = np.stack([cells[int(r)] for r in rec])        # (N,L)
    within_h = float(np.mean(np.sum(e ** 2, axis=2) - cell_mean))

    # --- oracle bias removals (estimated on test itself) -------------------
    def fixable_after(sub):
        e2 = e - sub
        return float(100 * np.sqrt(np.mean(np.sum(e2 ** 2, axis=2))))

    glob_h = np.stack([e[:, h].mean(axis=0) for h in range(L)])            # (L,3)
    e_gh = e - glob_h[None]
    rec_bias = {int(r): e[rec == r].reshape(-1, 3).mean(axis=0) for r in np.unique(rec)}
    e_rb = e.copy()
    for r, b in rec_bias.items():
        e_rb[rec == r] = e[rec == r] - b
    rh_bias = {}
    for r in np.unique(rec):
        m = rec == r
        rh_bias[int(r)] = np.stack([e[m][:, h].mean(axis=0) for h in range(L)])
    e_rhb = e.copy()
    for r, bl in rh_bias.items():
        e_rhb[rec == r] = e[rec == r] - bl[None]
    # per-window offset over its own horizons (an oracle that knows the window's
    # systematic offset but not its future) is not available ex ante -> omit.

    axis = np.sqrt(np.mean(e ** 2, axis=(0, 1))) * 100        # (3,) cm
    per_win = np.sum(e ** 2, axis=(1, 2))
    order = np.sort(per_win)[::-1]
    tot = per_win.sum()
    def top_share(frac):
        k = max(1, int(round(frac * len(order))))
        return float(order[:k].sum() / tot)

    hold = np.linalg.norm(g_tgt_cache[tag], axis=2) * 100     # hold baseline (no displacement)
    hor = np.sqrt(np.mean(n3 ** 2, axis=0)) * 100             # (L,) cm
    hold_h = np.sqrt(np.mean(g_tgt_cache[tag] ** 2, axis=(0, 2))) * 100
    skill = 1 - (hor / hold_h) ** 2
    cross = np.where(hor >= hold_h)[0]
    return dict(
        tag=tag, n_windows=int(N), total_mse_cm2=float(tot_cm2),
        rmse_3d_cm=float(100 * np.sqrt(mse)),
        rmse_coord_cm=float(100 * np.sqrt(np.mean(e ** 2))),
        between_record_share=float(between_rec / mse),
        within_record_share=float(1 - between_rec / mse),
        horizon_x_record_interaction_cm2=float(within_h * 1e4),
        axis_horizon_rmse_cm=[[float(v) for v in np.sqrt(np.mean(e ** 2, axis=0)[:, a]) * 100]
                              for a in range(3)],
        mean_error_vector_cm=[[float(v) for v in glob_h[:, a] * 100] for a in range(3)],
        oracle=dict(
            global_horizon_bias=dict(rmse_3d_cm=fixable_after(glob_h[None]),
                                     fixable_share=float(1 - np.mean(np.sum(e_gh ** 2, axis=2)) / mse)),
            per_record_bias=dict(rmse_3d_cm=fixable_after(np.stack([rec_bias[int(r)] for r in rec])),
                                 fixable_share=float(1 - np.mean(np.sum(e_rb ** 2, axis=2)) / mse)),
            per_record_horizon_bias=dict(rmse_3d_cm=fixable_after(np.stack([rh_bias[int(r)] for r in rec])),
                                         fixable_share=float(1 - np.mean(np.sum(e_rhb ** 2, axis=2)) / mse))),
        irreducible_rmse_3d_cm=float(100 * np.sqrt(np.mean(np.sum(e_rhb ** 2, axis=2)))),
        axis_rmse_coord_cm=[float(x) for x in axis],
        axis_share_of_mse=[float(x) for x in (axis ** 2) / np.sum(axis ** 2)],
        horizon_rmse_3d_cm=[float(x) for x in hor],
        hold_horizon_rmse_3d_cm=[float(x) for x in hold_h],
        skill_vs_hold=[float(x) for x in skill],
        crossover_lead_frames=(int(cross[0]) if len(cross) else None),
        concentration=dict(top1pct=top_share(0.01), top5pct=top_share(0.05), top10pct=top_share(0.10)))


g_tgt_cache = {}


def main():
    import time
    t0 = time.time()
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    env_of = recs.set_index("rec").env.to_dict()
    ds_of = recs.set_index("rec").dataset.to_dict()
    eg = lambda r: env_of[int(r)].split("_")[0]
    out = dict(_meta=dict(script="code/up_p2_decomp.py", seconds=None,
                          units="cm; rmse_3d = 100*sqrt(mean(||e||^2)), rmse_coord = 100*sqrt(mean(e^2))",
                          oracle_note="oracle corrections are fitted on the test split itself -> upper bounds "
                                      "on what calibration could recover, not achievable scores",
                          test_records=sorted(int(r) for r in recs[recs.split == "test"].rec)))

    for L in LENS:
        rid = f"_{L}"
        for arm in ("ridge", "quantile"):
            p = os.path.join(DATA, f"up_p2_{arm}_pred{rid}.npz")
            if not os.path.exists(p):
                continue
            z = load_npz(p)
            tgt = z["test_tgt"] if arm == "ridge" else z["test_tgt"]
            pred = z["test"] if arm == "ridge" else z["test"][..., 5]
            rec = z["test_rec"]
            g_tgt_cache[arm] = tgt.astype(np.float64)
            e = error(pred, tgt)
            key = "ridge" if arm == "ridge" else "quantile"
            out.setdefault(key, {})[str(L)] = block(e, rec, np.array([eg(r) for r in rec]), arm)
            print(f"{arm} L={L}: rmse3d={out[key][str(L)]['rmse_3d_cm']:.3f} "
                  f"irreducible={out[key][str(L)]['irreducible_rmse_3d_cm']:.3f} "
                  f"between_rec={out[key][str(L)]['between_record_share']:.3f}", flush=True)

    # ---- context-length probe (ridge, L=30) ------------------------------
    from up_p2_quantile import Panel, ridge_fit, ridge_predict
    P = Panel()
    ctx_tab = {}
    for k in CTX_PROBE:
        tr = P.windows("train", PROBE_L, 150, ctx=k)
        te = P.windows("test", PROBE_L, 400, ctx=k)
        sc, mdl = ridge_fit(tr, PROBE_L)
        pr = ridge_predict(sc, mdl, te["ctx"], PROBE_L)
        m = float(100 * np.sqrt(np.mean(np.sum((pr - te["tgt"]) ** 2, axis=2))))
        c = float(100 * np.sqrt(np.mean((pr - te["tgt"]) ** 2)))
        ctx_tab[str(k)] = dict(rmse_3d_cm=m, rmse_coord_cm=c, n_train=int(len(tr["rec"])),
                               n_test=int(len(te["rec"])))
        print(f"ctx={k} L=30 ridge: 3d={m:.3f} coord={c:.3f}", flush=True)
    out["context_sweep_L30_ridge"] = ctx_tab

    # ---- cross-domain transfer (ridge, L=30) -----------------------------
    tr_all = P.windows("train", PROBE_L, 150)
    te_all = P.windows("test", PROBE_L, 400)
    te_grp = np.array([eg(r) for r in te_all["rec"]])
    tab = {}
    for name in ("all", "EgoDemo", "EgoPro"):
        sel = np.ones(len(tr_all["rec"]), bool) if name == "all" else \
            np.array([ds_of[int(r)] == name for r in tr_all["rec"]])
        if sel.sum() == 0:
            continue
        sub = {k: v[sel] for k, v in tr_all.items()}
        sc, mdl = ridge_fit(sub, PROBE_L)
        pr = ridge_predict(sc, mdl, te_all["ctx"], PROBE_L)
        e = np.linalg.norm(pr - te_all["tgt"], axis=2) * 100
        row = dict(n_train_records=int(len(np.unique(sub["rec"]))),
                   n_train_windows=int(len(sub["rec"])),
                   rmse_3d_cm=float(np.sqrt(np.mean(e ** 2))),
                   by_test_group={g: float(np.sqrt(np.mean(e[te_grp == g] ** 2)))
                                  for g in sorted(set(te_grp))})
        tab[name] = row
        print(f"train={name} -> test 3d={row['rmse_3d_cm']:.3f} {row['by_test_group']}", flush=True)
    out["domain_transfer_L30_ridge"] = tab

    # ---- per-record table at L=30 ----------------------------------------
    z = load_npz(os.path.join(DATA, "up_p2_ridge_pred_30.npz"))
    zq = load_npz(os.path.join(DATA, "up_p2_quantile_pred_30.npz"))
    per = {}
    for r in np.unique(z["test_rec"]):
        m = z["test_rec"] == r
        er = np.linalg.norm(z["test"][m] - z["test_tgt"][m], axis=2) * 100
        eq = np.linalg.norm(zq["test"][m][..., 5] - zq["test_tgt"][m], axis=2) * 100
        per[str(int(r))] = dict(env=env_of[int(r)], dataset=ds_of[int(r)],
                                n=int(m.sum()),
                                ridge_3d_cm=float(np.sqrt(np.mean(er ** 2))),
                                quantile_3d_cm=float(np.sqrt(np.mean(eq ** 2))),
                                ridge_horizon_cm=[float(x) for x in np.sqrt(np.mean(er ** 2, axis=0))],
                                hold_3d_cm=float(np.sqrt(np.mean(np.sum(z["test_tgt"][m] ** 2, axis=2)) * 1e4)))
    out["per_record_L30"] = per
    out["_meta"]["seconds"] = round(time.time() - t0, 1)
    path = os.path.join(DATA, "up_p2_decomp.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"saved -> {path} ({out['_meta']['seconds']}s)", flush=True)


if __name__ == "__main__":
    main()