import os
# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Borrowed analyses from the ALT draft, computed on THIS paper's artefacts.

(1) Segment coverage: share of annotated segments that contain at least one
    detected change point, at three tolerances -- the ALT draft's argument that
    "landing in the right frame" is the wrong question.
(2) Scaling law: e(L) = a * L^b fitted in log-log over the four mask lengths,
    with R^2 -- the ALT draft's sub-linear growth claim, on our ridge numbers.
"""
import io, json, os
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(PROJ, "data")


# ---------------------------------------------------------------- (1) coverage
def coverage():
    import p1a_gpu_segmentation as M

    z, recs, segs, Xraw = M.load_arrays()
    te = list(recs[recs.split == "test"].rec)
    P = np.load(os.path.join(DATA, "p1a_gpu_segmentation_probs.npz"), allow_pickle=True)

    # the frozen decoding rule of the paper
    final = json.loads(io.open(os.path.join(DATA, "p1a_gpu_segmentation_final.json"),
                               encoding="utf-8").read())
    H = final["_meta"]["height"]
    D = final["_meta"]["distance"]
    print(f"frozen rule: height={H} distance={D} frames")

    tols = (0.2, 0.5, 2.0, 5.0)
    hit = {t: 0 for t in tols}
    det_tot = 0
    seg_tot = 0
    per_rec = []
    for r in te:
        sc = P[f"rec{int(r)}"]
        b, peaks = M.decode_scores(sc, H, D)
        ii = np.where(z["rec"] == r)[0]
        t = z["t"][ii]
        peaks_t = np.asarray(peaks, float) / 30.0
        det_tot += len(peaks_t)
        rec_hit = {t2: 0 for t2 in tols}
        sg = segs[segs.rec == r]
        for _, s in sg.iterrows():
            seg_tot += 1
            for tol in tols:
                lo, hi = s.start - tol, s.end + tol
                if np.any((peaks_t >= lo) & (peaks_t <= hi)):
                    hit[tol] += 1
                    rec_hit[tol] += 1
        per_rec.append(dict(rec=int(r), n_seg=int(len(sg)),
                            **{f"hit{t}": rec_hit[t] for t in tols}))

    out = dict(
        n_test_segments=int(seg_tot),
        n_test_records=int(len(te)),
        n_detections=int(det_tot),
        detections_per_segment=float(det_tot / seg_tot),
        coverage={f"tol_{t}s": dict(hits=int(hit[t]),
                                    share=float(hit[t] / seg_tot)) for t in tols},
        per_record=per_rec,
        rule=dict(height=H, distance=D, source="p1a_gpu_segmentation_final.json"),
    )
    return out


# ------------------------------------------------------------ (2) scaling law
def scaling():
    p = os.path.join(DATA, "p2_by_length.csv")
    df = pd.read_csv(p)
    r = df[df.method == "ridge"].sort_values("L_s")
    L = r.L_s.values.astype(float)
    e = r.rmse.values.astype(float) * 100.0  # cm
    b, loga = np.polyfit(np.log(L), np.log(e), 1)
    a = float(np.exp(loga))
    pred = a * L ** b
    ss_res = float(np.sum((np.log(e) - np.log(pred)) ** 2))
    ss_tot = float(np.sum((np.log(e) - np.log(e).mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    dbl = float(2.0 ** b)
    # constant-velocity column for the contrast the ALT draft draws
    cv = df[df.method == "cv"].sort_values("L_s")
    return dict(
        method="ridge", L_s=L.tolist(), rmse_cm=e.tolist(),
        a=a, b=float(b), r2=float(r2),
        doubling_factor=dbl,
        fit=f"e(L) = {a:.3f} L^{b:.3f}",
        constant_velocity_cm=(cv.rmse.values * 100.0).tolist() if len(cv) else [],
        n_windows=r.n_windows.tolist(),
    )


def main():
    cov = coverage()
    sc = scaling()
    out = dict(coverage=cov, scaling=sc)
    with io.open(os.path.join(DATA, "up19_borrowed_alt.json"), "w",
                 encoding="utf-8", newline="") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(dict(coverage=cov["coverage"],
                          det_per_seg=cov["detections_per_segment"],
                          n_seg=cov["n_test_segments"],
                          n_det=cov["n_detections"]), indent=1, ensure_ascii=False))
    print(json.dumps(sc, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()