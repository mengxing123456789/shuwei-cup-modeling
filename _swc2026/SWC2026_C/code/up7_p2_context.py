# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 context-length ablation: the paper fixed CTX=10 frames; this script re-runs the
ridge predictor at four context lengths on the same mask length (L=30 frames, 1.0 s)
and reports the three-dimensional RMSE.  It does not change any paper number; it answers
the one factor the ablation register marks as not isolated.

Protocol: same train/test records, same L, same ridge penalty, same feature map.  Only
the number of frames in the context changes.  Test is read once per context length.
"""
import json
import numpy as np
import p2_predict as P
from common import DATA, write_json


def main():
    rows = []
    for ctx in (5, 10, 20, 40):
        P.CTX = ctx
        train = P.windows("train", 30)
        test = P.windows("test", 30)
        if not train or not test:
            rows.append({"ctx_frames": ctx, "n_train": len(train), "n_test": len(test),
                         "rmse_3d_cm": None, "note": "insufficient windows"})
            continue
        sc, mdl = P.train_ridge({30: train}, 30)
        errs = []
        for c, tgt, _, _ in test:
            pred = P.ridge_predict(sc, mdl, c, 30)
            errs.append(np.linalg.norm(pred - tgt, axis=1).ravel())
        e = np.concatenate(errs)
        rows.append({"ctx_frames": ctx, "n_train": len(train), "n_test": len(test),
                     "rmse_3d_cm": float(np.sqrt(np.mean(e ** 2)) * 100.0),
                     "mae_3d_cm": float(np.mean(e) * 100.0)})
        print(ctx, rows[-1])
    write_json("up7_p2_context.json", {
        "_meta": {"script": "up7_p2_context.py", "mask_frames": 30, "mask_s": 1.0,
                  "protocol": "same records, same L, same ridge penalty, only context length varies",
                  "note": "test read once per context length; no hyperparameter selection on test"},
        "rows": rows,
    })


if __name__ == "__main__":
    main()