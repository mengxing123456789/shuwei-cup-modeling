# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Fold the run-to-run repeats into the anchor table.

``up13_anchor_retrain.json`` holds one run per anchor; ``up13_repeat_spread.json``
holds two more runs per anchor.  A single run of Part I carries a spread of a
few ARI points, so the anchor comparison has to be reported as a distribution
(mean +- sd over runs), not as a difference of two single runs.  This script
merges both sources and adds a paired statement: the anchor effect against the
within-anchor spread.
"""
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


base = load("up13_anchor_retrain.json")
spread = load("up13_repeat_spread.json")

rows = []
for r in base["summary"]:
    a = r["anchor"]
    ari = [r["p1a_ari"]]
    bf1 = [r["p1a_bf1"]]
    ap = [r["p1b_ap"]]
    auc = [r["p1b_auc"]]
    worst = [r["p1b_worst"]]
    for run in spread.get(a, {}).get("runs", []):
        if run.get("ok"):
            ari.append(run["ari"])
            bf1.append(run["bf1"])
    rows.append(dict(
        anchor=a,
        p1a_n=len(ari),
        p1a_ari_mean=st.mean(ari),
        p1a_ari_sd=st.stdev(ari) if len(ari) > 1 else 0.0,
        p1a_ari_min=min(ari),
        p1a_ari_max=max(ari),
        p1a_bf1_mean=st.mean(bf1),
        p1a_bf1_sd=st.stdev(bf1) if len(bf1) > 1 else 0.0,
        p1a_ari_runs=[round(x, 6) for x in ari],
        p1b_ap=ap[0],
        p1b_auc=auc[0],
        p1b_worst=worst[0],
    ))

by = {r["anchor"]: r for r in rows}
w, p, t = by["wrist"], by["palm"], by["tips"]

# The anchor contrast is only interesting if it clears the run-to-run noise.
pooled_sd = st.mean([r["p1a_ari_sd"] for r in rows])
gap = t["p1a_ari_mean"] - w["p1a_ari_mean"]
se = (t["p1a_ari_sd"] ** 2 / t["p1a_n"] + w["p1a_ari_sd"] ** 2 / w["p1a_n"]) ** 0.5
verdict = "clears the noise" if abs(gap) > 2 * se else "inside the noise"

out = dict(
    anchors=rows,
    pooled_within_anchor_sd=pooled_sd,
    tips_minus_wrist_pt=gap * 100.0,
    se_pt=se * 100.0,
    verdict=verdict,
    note=("Part I is not bit-reproducible: identical inputs (state_anchor_wrist.npz is "
          "bit-identical to state.npz) give different results across runs, because the "
          "chunked sampler, AdamW and the early-stopping checkpoint are all order- and "
          "timing-dependent.  The anchor rows are therefore reported as mean +- sd over "
          "repeated runs, and the anchor contrast is compared against that spread."),
)
dst = os.path.join(DATA, "up13_anchor_summary.json")
with open(dst, "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)

for r in rows:
    print("%-6s n=%d ARI %.4f +- %.4f [%.4f, %.4f]  bF1 %.4f  AP %.4f  AUC %.4f  worst %.4f"
          % (r["anchor"], r["p1a_n"], r["p1a_ari_mean"], r["p1a_ari_sd"],
             r["p1a_ari_min"], r["p1a_ari_max"], r["p1a_bf1_mean"],
             r["p1b_ap"], r["p1b_auc"], r["p1b_worst"]))
print("pooled within-anchor sd %.4f | tips - wrist %+.2f pt (se %.2f) -> %s"
      % (pooled_sd, gap * 100, se * 100, verdict))
print("wrote", dst)
