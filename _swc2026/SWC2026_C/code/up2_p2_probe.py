# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 v2 probe: where does the 1.0 s error come from, and what ceiling is reachable?

Reads only the cached prediction dumps and the panel (no training).
Outputs logs/up2_p2_probe.log lines and data/up2_p2_probe.json.
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
LOGS = os.path.abspath(os.path.join(HERE, "..", "logs"))
LENS = [6, 18, 30, 60]


def rmse3(e):
    return float(100 * np.sqrt(np.mean(np.sum(e ** 2, axis=2))))


def load(path):
    z = np.load(path)
    return {k: z[k] for k in z.files}


def main():
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    env_of = recs.set_index("rec").env.to_dict()
    ds_of = recs.set_index("rec").dataset.to_dict()
    out = {"_meta": {"script": "code/up2_p2_probe.py"}}
    lines = []

    def say(s):
        print(s, flush=True)
        lines.append(s)

    for L in LENS:
        zq = load(os.path.join(DATA, f"up_p2_quantile_pred_L{L}.npz"))
        tgt, rec = zq["test_tgt"].astype(np.float64), zq["test_rec"]
        pred = zq["test"][..., 5].astype(np.float64)
        e = pred - tgt
        blk = dict(rmse_3d=rmse3(e),
                   hold_rmse_3d=float(100 * np.sqrt(np.mean(np.sum(tgt ** 2, axis=2)))),
                   mean_abs_tgt_cm=float(100 * np.mean(np.linalg.norm(tgt, axis=2))),
                   max_abs_tgt_cm=float(100 * np.max(np.linalg.norm(tgt, axis=2))))
        # oracles (upper bounds on calibration)
        gh = np.stack([e[:, h].mean(axis=0) for h in range(L)])
        blk["oracle_global_h"] = rmse3(e - gh[None])
        rb = {int(r): e[rec == r].reshape(-1, 3).mean(axis=0) for r in np.unique(rec)}
        blk["oracle_rec_bias"] = rmse3(e - np.stack([rb[int(r)] for r in rec])[:, None, :])
        rh = {int(r): np.stack([e[rec == r][:, h].mean(axis=0) for h in range(L)]) for r in np.unique(rec)}
        e2 = e.copy()
        for r, b in rh.items():
            e2[rec == r] = e[rec == r] - b[None]
        blk["irreducible_rec_h"] = rmse3(e2)
        # per-record
        per = {}
        for r in np.unique(rec):
            m = rec == r
            er = np.linalg.norm(e[m], axis=2) * 100
            per[str(int(r))] = dict(env=str(env_of[int(r)]), dataset=str(ds_of[int(r)]),
                                    n=int(m.sum()), rmse=float(np.sqrt(np.mean(er ** 2))),
                                    share=float(np.sum(e[m] ** 2) / np.sum(e ** 2)))
        blk["per_record"] = per
        blk["horizon_rmse"] = [float(x) for x in np.sqrt(np.mean(np.sum(e ** 2, axis=2), axis=0)) * 100]
        blk["axis_rmse"] = [float(x) for x in np.sqrt(np.mean(e ** 2, axis=(0, 1))) * 100]
        out[f"L{L}"] = blk
        say(f"L={L}: quantile rmse3d={blk['rmse_3d']:.3f} hold={blk['hold_rmse_3d']:.2f} "
            f"oracle_gh={blk['oracle_global_h']:.3f} oracle_rb={blk['oracle_rec_bias']:.3f} "
            f"irreducible={blk['irreducible_rec_h']:.3f}")
        say("  per-record: " + " ".join(f"r{r}:{v['rmse']:.2f}" for r, v in per.items()))

    # constant-velocity baseline from the same windows
    from up_p2_quantile import Panel
    P = Panel()
    for L in LENS:
        W = P.windows("test", L, 400)
        ctx = W["ctx"].astype(np.float64)              # (N,10,3) raw wrist
        tgt = W["tgt"].astype(np.float64)
        v = ctx[:, -1] - ctx[:, -2]
        a = (ctx[:, -1] - 2 * ctx[:, -2] + ctx[:, -3])
        h = np.arange(1, L + 1)[None, :, None]
        cv = v[:, None, :] * h
        cva = v[:, None, :] * h + 0.5 * a[:, None, :] * h ** 2
        # least-squares velocity over the 10-frame window
        tt = np.arange(10)[None, :, None].astype(float)
        tm = tt - tt.mean()
        vls = (ctx * tm).sum(axis=1) / (tm ** 2).sum()
        cvl = vls[:, None, :] * h
        out.setdefault("cv_baseline", {})[str(L)] = dict(
            cv=rmse3(cv - tgt), cva=rmse3(cva - tgt), cv_ls10=rmse3(cvl - tgt),
            hold=rmse3(-tgt))
        say(f"CV L={L}: cv={out['cv_baseline'][str(L)]['cv']:.3f} "
            f"cva={out['cv_baseline'][str(L)]['cva']:.3f} "
            f"cv_ls10={out['cv_baseline'][str(L)]['cv_ls10']:.3f}")

    with open(os.path.join(DATA, "up2_p2_probe.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "up2_p2_probe.log"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("saved data/up2_p2_probe.json logs/up2_p2_probe.log")


if __name__ == "__main__":
    main()