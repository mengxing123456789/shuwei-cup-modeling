"""P2 crossover probe: hold-last vs constant-velocity error vs mask length.
Same test-split windows and context as p2_predict.py; median and mean are both reported
because the median is what a single request experiences, the mean is what the cost model uses.
"""

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import DATA, FIG, write_json
import p2_predict as P

LENS = [3, 6, 8, 10, 12, 15, 18, 20, 24, 30]
rows = []
for L in LENS:
    W = P.windows("test", L, cap=300)
    eh, ec, eh_end, ec_end = [], [], [], []
    for ctx, tgt, post, r in W:
        v = ctx[-1] - ctx[-2]
        hold = np.repeat(ctx[-1][None], L, axis=0)
        cv = ctx[-1][None] + v[None] * np.arange(1, L + 1)[:, None]
        dh = np.linalg.norm(hold - tgt, axis=1)
        dc = np.linalg.norm(cv - tgt, axis=1)
        eh.extend(dh); ec.extend(dc)
        eh_end.append(dh[-1]); ec_end.append(dc[-1])
    eh, ec = np.array(eh), np.array(ec)
    rows.append(dict(L_frames=L, L_s=round(L / 30, 3), n_windows=len(W),
                     hold_rmse_m=float(np.sqrt((eh ** 2).mean())),
                     cv_rmse_m=float(np.sqrt((ec ** 2).mean())),
                     hold_median_m=float(np.median(eh)), cv_median_m=float(np.median(ec)),
                     cv_gain_mean_pct=float(100 * (1 - np.sqrt((ec ** 2).mean()) / np.sqrt((eh ** 2).mean()))),
                     cv_gain_median_pct=float(100 * (1 - np.median(ec) / np.median(eh))),
                     hold_endpoint_rmse_m=float(np.sqrt(np.mean(np.square(eh_end)))),
                     cv_endpoint_rmse_m=float(np.sqrt(np.mean(np.square(ec_end))))))
    print(rows[-1])
# first L where CV mean error exceeds hold
cross = next((r["L_s"] for r in rows if r["cv_rmse_m"] > r["hold_rmse_m"]), None)
out = dict(_meta=dict(source="data/panel.npz test split", context_frames=P.CTX, cap=300,
                      convention="same windows as p2_predict; wrist position of dominant hand"),
           rows=rows, crossover_s=cross,
           crossover_s_median=next((r["L_s"] for r in rows if r["cv_median_m"] > r["hold_median_m"]), None))
write_json("p2_crossover.json", out)
fig, ax = plt.subplots(figsize=(5.6, 3.4))
x = [r["L_s"] for r in rows]
ax.plot(x, [r["hold_median_m"] * 100 for r in rows], "o-", label="hold-last")
ax.plot(x, [r["cv_median_m"] * 100 for r in rows], "s-", label="constant velocity")
ax.axvline(0.3, color="grey", ls=":", lw=.8)
ax.set_xlabel("mask length (s)"); ax.set_ylabel("median position error (cm)")
ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig8_p2_crossover.png"), dpi=180)
print("crossover", cross)
