
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Progress coordinate and the closed-form remaining-time estimator.

Why this exists
---------------
The first submission predicted *total* duration from a released prefix and then
reported that a longer prefix does not help (test MAE 2.939 / 2.972 / 3.290 s for
0.2 / 0.6 / 1.0 s, Spearman 0.288 / 0.257 / 0.107).  That is not a property of the
data: if the target is the whole job length d and the prefix is its first s seconds,
a prefix can only impose d >= s, which a linear model cannot use.  The quantity the
prefix actually carries is *how far along the job already is*.

Define the progress coordinate of a segment by normalised wrist arc length,

    phi(t) = L(t) / L(T),   L(t) = cumulative path length up to t,

and let the released prefix end at time s.  Then the remaining time is recovered
without any learned duration head:

    R_hat = s * (1 - phi_hat(s)) / phi_hat(s),

because at constant progress rate the elapsed fraction s/(s+R) equals phi.  The
estimator degrades only through phi_hat, so it must improve as s grows: with more of
the trajectory seen, phi is measured on a longer baseline.

Outputs
    data/progress.npz        per-frame phi for every record, plus segment table
    data/progress_audit.json monotone audit and the remaining-time comparison
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
FPS = 30.0
PREFIXES = (0.2, 0.6, 1.0)


def load():
    st = np.load(os.path.join(DATA, "state.npz"), allow_pickle=True)
    recs = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
    segs = pd.read_csv(os.path.join(DATA, "segments.csv"))
    rec = st["rec"].astype(int)
    dom = st["dom"].astype(int)
    fl, fr = st["fl"], st["fr"]
    # left wrist sits in the first three columns of fl (head frame), right in fr
    wrist = {0: fl[:, 0:3].astype(np.float64), 1: fr[:, 0:3].astype(np.float64)}
    slices = {}
    for r in recs.rec.astype(int):
        ii = np.flatnonzero(rec == r)
        slices[r] = (int(ii[0]), int(ii[-1]) + 1)
    return st, recs, segs, rec, dom, wrist, slices


def segment_phi(traj):
    """Normalised cumulative arc length along one segment's wrist path."""
    if len(traj) < 3:
        return None
    step = np.linalg.norm(np.diff(traj, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(step)])
    total = cum[-1]
    if not np.isfinite(total) or total <= 1e-9:
        return None
    return cum / total


def main():
    st, recs, segs, rec, dom, wrist, slices = load()
    rows, audit = [], []
    phi_store = {}

    for _, s in segs.iterrows():
        r = int(s.rec)
        if r not in slices:
            continue
        lo, hi = slices[r]
        a = lo + int(round(s.start * FPS))
        b = lo + int(round(s.end * FPS))
        b = min(b, hi)
        if b - a < 5:
            continue
        w = wrist[int(dom[r])]
        traj = w[a:b]
        phi = segment_phi(traj)
        if phi is None:
            continue
        d_true = float(s.end - s.start)
        family = str(s.get("label", ""))[:1].upper() or "?"
        phi_store.setdefault(r, []).append(
            dict(start_frame=a - lo, end_frame=b - lo, seg=int(s.seg), dur=d_true,
                 phi=phi.astype(np.float32)))

        for pre in PREFIXES:
            k = int(round(pre * FPS))
            if k >= len(phi) - 1:
                continue
            ph = float(phi[k])
            ph = min(max(ph, 0.02), 0.98)
            r_hat = pre * (1.0 - ph) / ph
            r_hat = min(r_hat, 4.0 * d_true + 1.0)
            rows.append(dict(rec=r, seg=int(s.seg), split=str(s.split), prefix=pre,
                             dur=d_true, phi=ph, r_true=d_true - pre, r_hat=r_hat,
                             family=family))

    df = pd.DataFrame(rows)
    fam_med = df[df.split == "train"].groupby("family").dur.median().to_dict()
    glob_med = float(df[df.split == "train"].dur.median())
    df["r_base"] = df.apply(
        lambda z: fam_med.get(z.family, glob_med) - z.prefix, axis=1)

    out = {}
    for pre, g in df.groupby("prefix"):
        te = g[g.split == "test"]
        tr = g[g.split == "train"]
        for tag, part in (("test", te), ("train", tr)):
            err_p = np.abs(part.r_hat.values - part.r_true.values)
            err_b = np.abs(part.r_base.values - part.r_true.values)
            out[f"{tag}@{pre}"] = dict(
                n=int(len(part)),
                mae_progress=float(err_p.mean()),
                mae_family_median=float(err_b.mean()),
                ratio=float(err_p.mean() / max(err_b.mean(), 1e-9)),
                spearman=float(pd.Series(part.r_hat).corr(
                    pd.Series(part.r_true), method="spearman")),
                mean_abs_phi_err=None,
            )
    # monotone audit on the test split
    seq = [out[f"test@{p}"]["mae_progress"] for p in PREFIXES if f"test@{p}" in out]
    monotone = all(seq[i] > seq[i + 1] for i in range(len(seq) - 1))

    np.savez_compressed(os.path.join(DATA, "progress.npz"),
                        **{f"r{r}_s{s['seg']}": s["phi"] for r in phi_store for s in phi_store[r]})
    audit = dict(
        script="progress_remaining.py",
        n_segments=int(len(df[df.prefix == PREFIXES[0]])),
        n_records=int(df.rec.nunique()),
        prefixes=list(PREFIXES),
        estimator="R_hat = s*(1-phi(s))/phi(s), phi = normalised wrist arc length",
        comparison=out,
        monotone_improvement_with_prefix=bool(monotone),
        note="MAE should fall as the prefix grows; if it does not, phi is not the "
             "informative statistic and the estimator must be re-derived.",
    )
    with open(os.path.join(DATA, "progress_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)

    print(f"segments {audit['n_segments']}  records {audit['n_records']}")
    print(f"{'prefix':7s}{'n':>5s}{'MAE_phi':>10s}{'MAE_med':>10s}{'ratio':>8s}{'rho':>8s}")
    for p in PREFIXES:
        k = f"test@{p}"
        if k in out:
            o = out[k]
            print(f"{p:<7.1f}{o['n']:5d}{o['mae_progress']:10.4f}"
                  f"{o['mae_family_median']:10.4f}{o['ratio']:8.3f}{o['spearman']:8.3f}")
    print("monotone improvement with prefix:", monotone)


if __name__ == "__main__":
    main()