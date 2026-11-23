"""P2 interval calibration: split-conformal 90% radius per mask length.
Calibrated on validation windows, evaluated on test windows. Uses the ridge predictor
already fixed in p2_predict.py (no test labels touched during calibration).

修订记录（2026-11-20 17:0x）：
  * **修 bug**：原版调用 `P.predict("ridge", ctx, L, mdl)`，但 `predict()` 只实现
    hold / cv / 二次外推三支，"ridge" 落到 else 分支 —— 于是 `p2_interval.json`
    里的半径其实是**二次外推基线**的误差分位，不是 ridge 的。改为直接调
    `P.ridge_predict(sc, mdl, ctx, L)`。
  * **补官方档**：`common_conditions.json` 的 observation.prefix_seconds 是
    [0.2, 0.6, 1.0]，0.6 s = 18 帧原先不在 `P.LENS`（{6,15,30,60}）里，现加入 GRID。
  * **补分环境覆盖率**：边际覆盖率不能替代条件覆盖率；对每个 test 记录按其 env 聚合。
原有 LENS 档位保留，保证与 `p2_predict.json` 可并列。
"""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import numpy as np
from common import DATA, write_json
import p2_predict as P
import pandas as pd, os

ALPHA = 0.10
GRID = [6, 15, 18, 30, 60]          # 原 LENS + 官方 0.6 s（18 帧）
RECS = pd.read_csv(os.path.join(DATA, "panel_records.csv"))
ENV = RECS.set_index("rec").env.to_dict()

out = []
cond = {}
for L in GRID:
    tr = P.windows("train", L, cap=150)
    va = P.windows("validation", L, cap=400)
    te = P.windows("test", L, cap=400)
    if not va or not te:
        continue
    sc, mdl = P.train_ridge({L: tr}, L)

    def errs(W):
        e, rr = [], []
        for ctx, tgt, post, r in W:
            pred = P.ridge_predict(sc, mdl, ctx, L)
            e.append(np.linalg.norm(pred - tgt, axis=1))
            rr.append(int(r))
        return np.concatenate(e), np.array(rr)

    ev, _ = errs(va)
    et, rt = errs(te)
    q = float(np.quantile(ev, 1 - ALPHA))
    row = dict(L_s=round(L / 30, 4), L_frames=L, n_val=int(len(ev)), n_test=int(len(et)),
               q90_m=q, coverage_test=float((et <= q).mean()),
               mean_radius_m=q, empirical_median_err_m=float(np.median(et)))
    out.append(row)
    print(row, flush=True)

    # 分环境条件覆盖率：把 (window,frame) 展平，按记录→环境聚合
    lab = np.repeat(rt, len(et) // len(rt))
    per = {}
    for r in sorted(set(rt.tolist())):
        m = lab == r
        per[str(r)] = dict(env=str(ENV.get(r, "?")), n_frames=int(m.sum()),
                           coverage=float((et[m] <= q).mean()))
    by_env = {}
    for v in per.values():
        by_env.setdefault(v["env"], []).append(v)
    env_rows = {}
    for e, vs in by_env.items():
        w = np.array([v["n_frames"] for v in vs], dtype=float)
        env_rows[e] = dict(n_records=len(vs), n_frames=int(w.sum()),
                           coverage=float(np.average([v["coverage"] for v in vs], weights=w)))
    cs = np.array([v["coverage"] for v in env_rows.values()])
    cond[str(L)] = dict(by_env=env_rows, per_record=per,
                        summary=dict(n_env=int(len(cs)), marginal=round(row["coverage_test"], 4),
                                     min=float(cs.min()), max=float(cs.max()),
                                     mean=float(cs.mean()), n_below_0p85=int((cs < 0.85).sum())))

write_json("p2_interval.json", dict(
    _meta=dict(method="split conformal, absolute 3D error radius, calibrated on validation, evaluated on test",
               alpha=ALPHA,
               predictor="ridge (alpha=10, context 10 frames) -- via P.ridge_predict",
               convention="same windows as p2_predict",
               revision="2026-11-20: predictor call fixed (was falling through to the quadratic branch); "
                        "L=18 (0.6 s) added to match the official prefix grid; per-environment coverage added"),
    by_length=out,
    summary=dict(mean_coverage=float(np.mean([r["coverage_test"] for r in out])),
                 mean_radius_m=float(np.mean([r["mean_radius_m"] for r in out]))),
    conditional=cond))