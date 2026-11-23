#!/usr/bin/env python3

# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""P2 inside the official action space.

Why this file exists
--------------------
The paper's Part II study varies the *context* over {0.2, 0.5, 1.0, 2.0} s and
prices a look with a continuous cost c(T) = c0 + c1*T.  The released protocol
(`common_conditions.json`) fixes something else:

    observation.prefix_seconds = [0.2, 0.6, 1.0]
    observation.delay_s        = 1.0
    observation.cost           = 1.0
    observation.max_per_job    = 2

so a request buys *more prefix of the same recording*, arrives after a fixed
1.0 s, costs a fixed 1.0 and can be made at most twice.  The 1 s delay is the
part that matters: it eats the lead time available to the decision, so a
request bought at a 3 s deadline leaves 2 s, then 1 s of lead.

What is measured
----------------
  * error of the frozen ridge recipe over context c in {6, 18, 30} frames
    (0.2 / 0.6 / 1.0 s, the official set) and lead h in {30, 60, 90} frames;
  * the three protocol-conformant decision options at a 3 s deadline:
        A  no request          c=6  lead=90   requests 0
        B  one request         c=18 lead=60   requests 1
        C  two requests        c=30 lead=30   requests 2
  * the two derived quantities that decide the comparison:
        prefix gain   = e(c=6,h) - e(c=30,h)      (what a longer prefix buys)
        delay penalty = e(c,h)   - e(c,h-30)      (what one second of waiting costs)

No cost-to-centimetre conversion is invented: the statement does not fix one, so
the deliverable is the (error, requests) frontier and the two deltas above.

Output: data/p2_official.json  (nothing existing is overwritten)
"""
import json
import os
import time

import numpy as np

import p2_predict as P
from common import DATA

CTXS = [6, 18, 30]           # official prefix set, in frames at 30 fps
LEADS = [30, 60, 90]         # leads used by the three decision options
OPTIONS = [("A_no_request", 6, 90, 0),
           ("B_one_request", 18, 60, 1),
           ("C_two_requests", 30, 30, 2)]


def evaluate(ctx_frames, lead):
    """Fit the frozen ridge recipe at this (context, lead) and evaluate on test."""
    P.CTX = ctx_frames
    tr = {lead: P.windows("train", lead)}
    sc, mdl = P.train_ridge(tr, lead)
    Eva = []
    for ctx, tgt, _, _ in P.windows("validation", lead):
        pr = P.ridge_predict(sc, mdl, ctx, lead)
        Eva.append(np.linalg.norm(pr - tgt, axis=1))
    Eva = np.array(Eva)
    q90 = float(np.quantile(Eva.ravel(), 0.90))

    Ete = []
    for ctx, tgt, _, _ in P.windows("test", lead):
        pr = P.ridge_predict(sc, mdl, ctx, lead)
        Ete.append(np.linalg.norm(pr - tgt, axis=1))
    Ete = np.array(Ete)
    rmse3 = float(np.sqrt((Ete ** 2).mean()))
    return dict(ctx_frames=ctx_frames, ctx_s=round(ctx_frames / 30.0, 2),
                lead_frames=lead, lead_s=round(lead / 30.0, 2),
                rmse_cm=round(rmse3 * 100, 3),
                rmse_coord_cm=round(rmse3 * 100 / np.sqrt(3), 3),
                end_rmse_cm=round(float(np.sqrt((Ete[:, -1] ** 2).mean())) * 100, 3),
                median_end_cm=round(float(np.median(Ete[:, -1])) * 100, 3),
                q90_m=round(q90, 4),
                coverage_test=round(float((Ete.ravel() <= q90).mean()), 4),
                within_2cm=round(float((Ete[:, -1] < 0.02).mean()), 4),
                n_val=int(Eva.shape[0]), n_test=int(Ete.shape[0]))


def main():
    t0 = time.time()
    out = {"_meta": {
        "script": "p2_official.py",
        "protocol": "common_conditions.json -> observation: prefix_seconds [0.2,0.6,1.0], "
                    "delay_s 1.0, cost 1.0, max_per_job 2",
        "predictor": "ridge alpha=10 on rel/vel/acc of the last c frames (recipe of p2_predict.py), "
                     "fitted per (c, lead) on train, evaluated once on test",
        "deadline_s": 3.0,
        "note": "no cost-to-centimetre conversion is assumed; the output is the "
                "(error, requests) frontier plus prefix gain and delay penalty",
        "answers": ["\\slotPOfficialA", "\\slotPOfficialB", "\\slotPOfficialC",
                    "\\slotPPrefixGain", "\\slotPDelayPenalty"],
    }, "grid": [], "options": [], "derived": {}, "created": ""}
    out["created"] = time.strftime("%Y-%m-%d %H:%M:%S")

    by = {}
    for c in CTXS:
        for h in LEADS:
            row = evaluate(c, h)
            out["grid"].append(row)
            by[(c, h)] = row
            print("c=%2d h=%2d  rmse=%6.2f cm  coord=%5.2f  end=%6.2f  cov=%.3f (%.0fs)"
                  % (c, h, row["rmse_cm"], row["rmse_coord_cm"], row["end_rmse_cm"],
                     row["coverage_test"], time.time() - t0), flush=True)

    for name, c, h, req in OPTIONS:
        r = dict(options=name, ctx_frames=c, ctx_s=round(c / 30.0, 2),
                 usable_lead_frames=h, usable_lead_s=round(h / 30.0, 2),
                 requests=req, cost_units=req * 1.0,
                 rmse_cm=by[(c, h)]["rmse_cm"],
                 rmse_coord_cm=by[(c, h)]["rmse_coord_cm"],
                 end_rmse_cm=by[(c, h)]["end_rmse_cm"])
        out["options"].append(r)
        print("option %-14s req=%d  rmse=%6.2f cm" % (name, req, r["rmse_cm"]), flush=True)

    # prefix gain at a fixed lead, and the penalty of one second of waiting
    gain = {str(h): round(by[(6, h)]["rmse_cm"] - by[(30, h)]["rmse_cm"], 3) for h in LEADS}
    penalty = {str(c): round(by[(c, 60)]["rmse_cm"] - by[(c, 30)]["rmse_cm"], 3) for c in CTXS}
    out["derived"] = {
        "prefix_gain_cm_by_lead": gain,
        "delay_penalty_cm_by_ctx": penalty,
        "option_B_vs_A_cm": round(by[(18, 60)]["rmse_cm"] - by[(6, 90)]["rmse_cm"], 3),
        "option_C_vs_B_cm": round(by[(30, 30)]["rmse_cm"] - by[(18, 60)]["rmse_cm"], 3),
        "delay_exceeds_gain": bool(max(penalty.values()) > max(gain.values())),
        "seconds": round(time.time() - t0, 1),
    }
    print("prefix gain", gain, "delay penalty", penalty)
    print("B vs A", out["derived"]["option_B_vs_A_cm"],
          "C vs B", out["derived"]["option_C_vs_B_cm"],
          "delay_exceeds_gain", out["derived"]["delay_exceeds_gain"])

    with open(os.path.join(DATA, "p2_official.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", os.path.join(DATA, "p2_official.json"), flush=True)


if __name__ == "__main__":
    main()