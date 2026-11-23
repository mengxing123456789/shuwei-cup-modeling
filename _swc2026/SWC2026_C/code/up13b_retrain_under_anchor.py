# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up13b_retrain_under_anchor.py -- retrain P1-a and P1-b under each representative point.

``up10`` moved one keypoint at a time and measured how the *metric* changed.
That answers "is the metric fragile", not "would a different anchor train a
different model".  This script answers the second question: it points the two
downstream learners at ``state_anchor_<name>.npz`` and retrains from scratch
with the same seeds, the same split, the same hyper-parameters and the same
decoding grid.  Nothing about the protocol changes, so a difference in the
result is attributable to the anchor.

Design
------
P1-a (segmentation): 3 seeds x 40 epochs, decoding grid chosen on validation,
    test scored once.  Reported: test mean ARI, boundary F1, per-dataset ARI.
P1-b (bad-frame detector): configuration V8 (the frozen production detector),
    3 seeds x 18 epochs.  Reported: test AP, test AUC, worst per-environment AUC.

Each anchor runs in its own shadow data directory, so no file of the main
pipeline is overwritten and ``data/up2_p1b.json`` is never touched.

Outputs: ``data/up13_p1a_anchor_<name>.json``,
         ``data/up13_p1b_anchor_<name>.json``,
         ``data/up13_anchor_retrain.json`` (the combined table)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
DATA = os.path.join(PROJ, "data")
PY = sys.executable
ANCHORS = ("wrist", "palm", "tips")


def shadow(name):
    """A data directory that looks like ``data/`` but carries one anchor."""
    d = os.path.join(DATA, "shadow_anchor_%s" % name)
    os.makedirs(d, exist_ok=True)
    for f in ("panel_records.csv", "segments.csv", "p1_segmentation.json",
              "up_p1b_aux.npz"):
        src = os.path.join(DATA, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(d, f))
    shutil.copy2(os.path.join(DATA, "state_anchor_%s.npz" % name),
                 os.path.join(d, "state.npz"))
    return d


def run_p1a(name, seeds, epochs):
    d = shadow(name)
    code = r'''
import json, os, sys
sys.path.insert(0, r"%s")
import p1a_gpu_segmentation as M
M.DATA = r"%s"
M.MODELS = os.path.join(r"%s", "models_%s")
os.makedirs(M.MODELS, exist_ok=True)
sys.argv = ["p1a", "--seeds", "%d", "--epochs", "%d"]
M.main()
''' % (HERE, d, d, name, seeds, epochs)
    t0 = time.time()
    p = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    secs = time.time() - t0
    src = os.path.join(d, "p1a_gpu_segmentation.json")
    if not os.path.exists(src):
        return dict(ok=False, seconds=round(secs, 1),
                    stderr=p.stderr[-3000:], stdout=p.stdout[-1500:])
    with open(src, encoding="utf-8") as f:
        j = json.load(f)
    dst = os.path.join(DATA, "up13_p1a_anchor_%s.json" % name)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(j, f, indent=1, ensure_ascii=False)
    return dict(ok=True, seconds=round(secs, 1),
                height=j["_meta"]["height"], distance=j["_meta"]["distance"],
                val_ari=j["_meta"]["val_mean_ari"],
                test_ari=j["test"]["mean_ari"],
                test_std=j["test"]["std_ari"],
                boundary_f1=j["test"]["mean_boundary_f1"],
                boundary_mae=j["test"]["mean_boundary_mae"],
                by_dataset=j["by_dataset"], json=dst)


def run_p1b(name, seeds):
    d = shadow(name)
    code = r'''
import json, os, sys
sys.path.insert(0, r"%s")
import up2_p1b_v2 as M
M.DATA = r"%s"
M.LOGS = os.path.join(r"%s", "logs_%s")
os.makedirs(M.LOGS, exist_ok=True)
M.OUT_JSON = os.path.join(M.DATA, "up2_p1b.json")
M.LOG_PATH = os.path.join(M.LOGS, "up2_p1b_v2.log")
sys.argv = ["p1b", "--configs", "V8", "--seeds", "%s"]
M.main()
''' % (HERE, d, d, name, seeds)
    t0 = time.time()
    p = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    secs = time.time() - t0
    src = os.path.join(d, "up2_p1b.json")
    if not os.path.exists(src):
        return dict(ok=False, seconds=round(secs, 1),
                    stderr=p.stderr[-3000:], stdout=p.stdout[-1500:])
    with open(src, encoding="utf-8") as f:
        j = json.load(f)
    agg = j["results"]["V8"]["aggregate"]
    dst = os.path.join(DATA, "up13_p1b_anchor_%s.json" % name)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(j, f, indent=1, ensure_ascii=False)
    return dict(ok=True, seconds=round(secs, 1),
                test_ap=agg["test_ap"], test_auc=agg["test_auc"],
                worst_env=agg["worst_env"], params=agg["params"],
                gate_passes=bool(agg["gate"]["passes"]), json=dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--p1b-seeds", default="20261120,20261122,20261123")
    ap.add_argument("--only", default=",".join(ANCHORS))
    a = ap.parse_args()

    out_path = os.path.join(DATA, "up13_anchor_retrain.json")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            out = json.load(f)
    else:
        out = dict(_meta=dict(
            note="P1-a segmentation and P1-b V8 detector retrained from scratch "
                 "around three representative points; identical seeds, split, "
                 "hyper-parameters and decoding grid",
            p1a_seeds=a.seeds, p1a_epochs=a.epochs, p1b_seeds=a.p1b_seeds,
            anchors=list(ANCHORS)), p1a={}, p1b={})

    for name in [s.strip() for s in a.only.split(",") if s.strip()]:
        print("=== anchor", name, flush=True)
        out["p1a"][name] = run_p1a(name, a.seeds, a.epochs)
        print("   p1a", {k: v for k, v in out["p1a"][name].items()
                         if k in ("ok", "test_ari", "boundary_f1", "seconds")}, flush=True)
        out["p1b"][name] = run_p1b(name, a.p1b_seeds)
        print("   p1b", {k: v for k, v in out["p1b"][name].items()
                         if k in ("ok", "test_ap", "test_auc", "worst_env", "seconds")}, flush=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)

    # summary table
    ref = out["p1a"].get("wrist") or {}
    rows = []
    for name in ANCHORS:
        pa, pb = out["p1a"].get(name), out["p1b"].get(name)
        if not (pa and pb and pa.get("ok") and pb.get("ok")):
            continue
        rows.append(dict(anchor=name,
                         p1a_ari=pa["test_ari"], p1a_bf1=pa["boundary_f1"],
                         p1a_delta_pt=(pa["test_ari"] - ref["test_ari"]) * 100.0
                         if ref.get("test_ari") else None,
                         p1b_ap=pb["test_ap"], p1b_auc=pb["test_auc"],
                         p1b_worst=pb["worst_env"],
                         p1b_ap_delta=(pb["test_ap"] - (out["p1b"]["wrist"]["test_ap"]
                                                        if "wrist" in out["p1b"] else pb["test_ap"]))))
    out["summary"] = rows
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(rows, indent=1, ensure_ascii=False))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
