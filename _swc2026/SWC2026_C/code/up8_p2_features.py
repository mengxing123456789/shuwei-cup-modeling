# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""P2 feature-subset ablation at L=1.0 s and context 10 frames.

Variants:
  full     relative context + last velocity + last acceleration + horizon ratio
  no-acc   relative context + last velocity + horizon ratio
  rel      relative context only + horizon ratio
  no-hor   full feature map without the two horizon columns

Same records, same windows, same ridge penalty. Test is read once per variant. This
answers the second row the ablation register marks as not isolated.
"""
import json
import numpy as np
import p2_predict as P
from common import DATA, write_json


def feature(ctx, kind):
    rel = (ctx - ctx[-1]).ravel()
    vel = np.diff(ctx, axis=0)[-1]
    acc = np.diff(ctx, n=2, axis=0)[-1]
    if kind == "full":
        return np.concatenate([rel, vel, acc])
    if kind == "no-acc":
        return np.concatenate([rel, vel])
    if kind == "rel":
        return rel
    if kind == "no-hor":
        return np.concatenate([rel, vel, acc])
    raise ValueError(kind)


def design(ctx, tgt, L, kind):
    f = feature(ctx, kind)
    X, Y = [], []
    for h in range(L):
        row = list(f)
        if kind != "no-hor":
            row += [(h + 1) / L, L / 30.0]
        X.append(row)
        Y.append(tgt[h] - ctx[-1])
    return np.array(X), np.array(Y)


def main():
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    train = P.windows("train", 30)
    test = P.windows("test", 30)
    rows = []
    for kind in ("full", "no-acc", "rel", "no-hor"):
        X, Y = [], []
        for c, t, _, _ in train:
            x, y = design(c, t, 30, kind)
            X.append(x); Y.append(y)
        X = np.vstack(X); Y = np.concatenate(Y)
        sc = StandardScaler().fit(X)
        mdl = Ridge(alpha=10.0).fit(sc.transform(X), Y)
        errs = []
        for c, t, _, _ in test:
            x, _ = design(c, t, 30, kind)
            pred = mdl.predict(sc.transform(x)) + c[-1]
            errs.append(np.linalg.norm(pred - t, axis=1).ravel())
        e = np.concatenate(errs)
        rows.append({"variant": kind, "n_features": int(X.shape[1]),
                     "n_train_windows": len(train), "n_test_windows": len(test),
                     "rmse_3d_cm": float(np.sqrt(np.mean(e ** 2)) * 100.0),
                     "mae_3d_cm": float(np.mean(e) * 100.0)})
        print(kind, rows[-1])
    write_json("up8_p2_features.json", {
        "_meta": {"script": "up8_p2_features.py", "mask_frames": 30, "mask_s": 1.0,
                  "context_frames": 10, "ridge_alpha": 10.0,
                  "protocol": "same windows; only the feature subset changes; test read once"},
        "rows": rows,
    })


if __name__ == "__main__":
    main()