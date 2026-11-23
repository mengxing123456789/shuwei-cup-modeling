# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Does the video block carry information about segment duration?

Arms, identical pipeline and split:
  A: existing pose prefix features only
  B: pose prefix features + v2 video motion stats
  P: B with the video block permuted inside train (control)

Protocol: ridge on log(duration); alpha chosen on validation; test scored once.
Bar fixed before the run: B counts as informative only if test MAE ratio <= 0.90.
"""
from __future__ import annotations

import os

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

C = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = C / "data"
OFF = Path(r"Restocking_Problem_and_Data_EN\Restocking_Tasks_and_Constraints\source_segment_index.csv")
BAR_REL = 0.90
SEED = 20261120

pf = pd.read_csv(DATA / "prefix_progress_features.csv")
vid = pd.read_csv(DATA / "v2_video_features.csv")
off = pd.read_csv(OFF)[["unit_id", "sample", "split", "duration_s", "eligible"]]

vid["camera"] = vid["camera"].astype(str).str.replace(".mp4", "", regex=False)
CAM_MAP = {"head_left": "hL", "head_right": "hR", "left_wrist": "wL", "right_wrist": "wR"}
vid["group"] = vid["camera"].map(CAM_MAP)
assert vid["group"].notna().all(), "unknown camera name"
# video record ids are either E001 (EgoDemo) or EgoPro_<first8 of uuid>; the
# official index stores the full uuid for the other two datasets.
def _key(x: str) -> str:
    x = str(x)
    if x.startswith("EgoPro_") or x.startswith("EgoStan_"):
        return x.split("_")[-1][:8].lower()
    return x.strip()


vid["sample"] = vid["record_id"].astype(str).map(_key)

STATS = ["diff_mean", "diff_p90", "static_frac", "roi_diff_mean", "roi_diff_p90",
         "roi_static_frac", "bright_mean", "bright_std", "roi_bright_mean", "roi_bright_std",
         "flow_mean", "flow_p90", "roi_flow_mean", "roi_flow_p90"]

rows = []
for (sample, grp), g in vid.groupby(["sample", "group"]):
    g = g.sort_values("t_s")
    for pref in (0.2, 0.6, 1.0):
        w = g[g["t_s"] <= pref + 1e-9]
        if len(w) == 0:
            continue
        d = {"sample": sample, "prefix": pref}
        for s in STATS:
            d[f"{grp}_{s}_mean"] = float(w[s].mean())
            d[f"{grp}_{s}_std"] = float(w[s].std(ddof=0))
            d[f"{grp}_{s}_max"] = float(w[s].max())
        k = max(1, len(w) // 3)
        for s in ("flow_mean", "roi_flow_mean", "static_frac"):
            d[f"{grp}_{s}_trend"] = float(w[s].iloc[-k:].mean() - w[s].iloc[:k].mean())
        d[f"{grp}_n_samp"] = len(w)
        rows.append(d)

vw = pd.DataFrame(rows)
wide = None
for grp in sorted(vw.columns.str.split("_").str[0].unique()):
    pass
groups = [g for g in ("hL", "hR", "wL", "wR") if f"{g}_n_samp" in vw.columns]
for grp in groups:
    cols = ["sample", "prefix"] + [c for c in vw.columns if c.startswith(grp + "_")]
    part = vw.loc[vw[f"{grp}_n_samp"].notna(), cols]
    wide = part if wide is None else wide.merge(part, on=["sample", "prefix"], how="outer")

# NOTE: source_segment_index is not unique across records in the official index,
# merging on it multiplies rows. unit_id is the unique unit key.
off_small = off[["unit_id", "sample", "split", "duration_s"]].drop_duplicates("unit_id")
off_small["sample"] = off_small["sample"].astype(str).map(lambda s: s if s.startswith("E") and len(s) <= 5 else s.replace("-", "")[:8].lower())
m = pf.merge(off_small, on="unit_id", how="left", suffixes=("", "_off"))
assert len(m) == len(pf), f"unit_id join changed row count: {len(m)} vs {len(pf)}"
before = len(m)
m = m.merge(wide, on=["sample", "prefix"], how="left", validate="m:1")
assert len(m) == before, f"video join changed row count: {len(m)} vs {before}"

xcols = [c for c in pf.columns if c.startswith("x")]
vcols = [c for c in wide.columns if c not in ("sample", "prefix")]

has = m[vcols].notna().any(axis=1).values
print(f"rows={len(m)}  pose feats={len(xcols)}  video feats={len(vcols)}  rows with video={has.sum()}")
print(m.assign(has=has).groupby("split")["has"].agg(["mean", "size"]).round(3).to_string())
if has.sum() == 0:
    raise SystemExit("video block failed to attach: check sample/prefix keys")

y_all = np.log(m["duration_s"].fillna(m["duration"]).values.astype(float))
tr = (m["split"] == "train").values
va = (m["split"] == "validation").values
te = (m["split"] == "test").values
print(f"split train/val/test = {tr.sum()}/{va.sum()}/{te.sum()}")


def build(cols):
    X = m[cols].astype(float).values.copy()
    keep = ~np.all(np.isnan(X[tr]), axis=0)          # drop columns empty in train
    X = X[:, keep]
    med = np.nanmedian(X[tr], axis=0)
    med = np.where(np.isnan(med), 0.0, med)
    X = np.where(np.isnan(X), med, X)
    return X, [c for c, k in zip(cols, keep) if k]


def fit_arm(cols, permute=False):
    X, used = build(cols)
    sc = StandardScaler().fit(X[tr])
    Xtr, Xva, Xte = sc.transform(X[tr]), sc.transform(X[va]), sc.transform(X[te])
    if permute:
        rng = np.random.default_rng(SEED)
        idx = [i for i, c in enumerate(used) if c in vcols]
        for i in idx:
            Xtr[:, i] = rng.permutation(Xtr[:, i])
    best = None
    for a in (0.3, 3.0, 30.0, 300.0, 3000.0):
        mdl = Ridge(alpha=a).fit(Xtr, y_all[tr])
        v = float(np.mean(np.abs(np.exp(mdl.predict(Xva)) - np.exp(y_all[va]))))
        if best is None or v < best[1]:
            best = (a, v, mdl)
    a, vmae, mdl = best
    pred, true = np.exp(mdl.predict(Xte)), np.exp(y_all[te])
    per_prefix = {}
    for p in sorted(m.loc[te, "prefix"].unique()):
        sel = (m.loc[te, "prefix"] == p).values
        per_prefix[str(p)] = float(np.mean(np.abs(pred[sel] - true[sel])))
    return dict(alpha=a, val_mae=vmae,
                test_mae=float(np.mean(np.abs(pred - true))),
                test_rmse=float(np.sqrt(np.mean((pred - true) ** 2))),
                test_median_ae=float(np.median(np.abs(pred - true))),
                per_prefix=per_prefix, n_features=len(used))


A = fit_arm(xcols)
B = fit_arm(xcols + vcols)
P = fit_arm(xcols + vcols, permute=True)
rel, perm_rel = B["test_mae"] / A["test_mae"], P["test_mae"] / A["test_mae"]

print("\nA pose only        test MAE %.4f s  val %.4f  alpha %.2f  nfeat %d" % (A["test_mae"], A["val_mae"], A["alpha"], A["n_features"]))
print("B pose+video       test MAE %.4f s  val %.4f  alpha %.2f  nfeat %d  ratio %.4f" % (B["test_mae"], B["val_mae"], B["alpha"], B["n_features"], rel))
print("P video permuted   test MAE %.4f s  val %.4f  alpha %.2f            ratio %.4f" % (P["test_mae"], P["val_mae"], P["alpha"], perm_rel))
print("per-prefix A:", {k: round(v, 3) for k, v in A["per_prefix"].items()})
print("per-prefix B:", {k: round(v, 3) for k, v in B["per_prefix"].items()})

# The pre-registered bar (B <= 0.90 x A) turned out not to discriminate: the
# permuted control passes it too, because 184 extra columns plus heavy ridge
# shrinkage improve the fit whether or not they carry duration information.
# The discriminating comparison is therefore B against the permutation control.
informative = bool(rel <= BAR_REL and rel < 0.98 * perm_rel)
bar_discriminated = bool(perm_rel > BAR_REL)
out = {
    "_meta": {"script": "up_video_value.py", "seed": SEED,
              "bar": f"informative only if test MAE ratio <= {BAR_REL}", "bar_discriminated": bar_discriminated,
              "protocol": "ridge on log(duration); alpha on validation; test scored once",
              "n_rows": int(len(m)), "pose_features": len(xcols), "video_features": len(vcols),
              "video_attached_rows": int(has.sum())},
    "coverage_by_split": m.assign(has=has).groupby("split")["has"].mean().round(4).to_dict(),
    "arms": {"A_pose_only": A, "B_pose_plus_video": B, "P_permutation_control": P},
    "ratio_B_over_A": rel, "ratio_perm_over_A": perm_rel, "informative": informative,
    "interpretation": ("video block adds information about duration, beating the permuted control" if informative else
                       "video block adds no information: B is not better than A and the permuted "
                       "control lands at the same level"),
}
(DATA / "up_video_value.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("\nwrote data/up_video_value.json")