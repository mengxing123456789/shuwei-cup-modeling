# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""Run-to-run distribution of the *shipped* Part I protocol.

Two different decoding protocols exist in this project and they are not
comparable:

  A. ``p1a_gpu_segmentation.py``  -- grid over (height, distance), both picked
     on validation ARI.  This is what the anchor study repeats, giving wrist
     ARI 0.4765 / 0.5327 / 0.5445.
  B. ``p1a_final_decode.py``      -- distance frozen at the training label
     prior (10th percentile of annotated subtask duration, 54 frames), height
     the only free scalar, selected on validation.  This is the protocol the
     paper's Part I table quotes.

The number quoted for protocol B (test ARI 0.5487) came from weights that were
later overwritten in ``models/``.  Decoding the *current* weights under the same
protocol gives 0.4902.  Since the training loop is not bit-reproducible
(chunk offsets from ``np.random.randint`` plus cuDNN autotuning), a single
number is not a defensible headline.  This driver retrains protocol B end to
end ``--repeats`` times and reports mean / sd / min / max, so the paper can
quote a distribution and test the Ward gap against it.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
PY = sys.executable

TRAIN = r'''
import json, os, sys
sys.path.insert(0, r"%(here)s")
import p1a_gpu_segmentation as M
M.DATA = r"%(d)s"
M.MODELS = r"%(m)s"
os.makedirs(M.MODELS, exist_ok=True)
sys.argv = ["p1a", "--seeds", "3", "--epochs", "40"]
M.main()
print("TRAINED")
'''

DECODE = r'''
import json, os, sys
sys.path.insert(0, r"%(here)s")
import p1a_gpu_segmentation as M
import p1a_final_decode as D
M.DATA = r"%(d)s"
M.MODELS = r"%(m)s"
D.DATA = r"%(d)s"
D.MODELS = r"%(m)s"
D.main()
j = json.load(open(os.path.join(r"%(d)s", "p1a_gpu_segmentation_final.json"), encoding="utf-8"))
print("ROW " + json.dumps(dict(
    height=j["_meta"]["height"], distance=j["_meta"]["distance"],
    val_ari=j["_meta"]["val_ari"], val_bf1=j["_meta"]["val_bf1"],
    ari=j["test"]["mean_ari"], std=j["test"]["std_ari"],
    f1=j["test"]["mean_f1"], bf1=j["test"]["mean_boundary_f1"],
    bmae=j["test"]["mean_boundary_mae"])))
'''

KEEP = ("panel_records.csv", "segments.csv", "p1_segmentation.json", "up_p1b_aux.npz")


def shadow(tag):
    d = os.path.join(DATA, "finalrep_%s" % tag)
    m = os.path.join(d, "models")
    os.makedirs(m, exist_ok=True)
    for f in KEEP:
        src = os.path.join(DATA, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(d, f))
    shutil.copy2(os.path.join(DATA, "state.npz"), os.path.join(d, "state.npz"))
    return d, m


def run(code, d, m):
    p = subprocess.run([PY, "-c", code % dict(here=HERE, d=d, m=m)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p


def one(tag):
    d, m = shadow(tag)
    t0 = time.time()
    tr = run(TRAIN, d, m)
    if "TRAINED" not in tr.stdout:
        return dict(ok=False, stage="train", seconds=round(time.time() - t0, 1),
                    stderr=tr.stderr[-1500:], stdout=tr.stdout[-800:])
    de = run(DECODE, d, m)
    secs = round(time.time() - t0, 1)
    row = None
    for line in de.stdout.splitlines():
        if line.startswith("ROW "):
            row = json.loads(line[4:])
    if row is None:
        return dict(ok=False, stage="decode", seconds=secs,
                    stderr=de.stderr[-1500:], stdout=de.stdout[-800:])
    row.update(ok=True, seconds=secs)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    out_path = os.path.join(DATA, "up15_p1a_final_repeats.json")
    out = dict(runs=[], protocol="distance = round(10th pct of training segment duration); height on validation ARI")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            out = json.load(f)
    start = len(out["runs"])
    for i in range(a.repeats):
        tag = "r%d" % (start + i + 1)
        print("=== %s" % tag, flush=True)
        row = one(tag)
        print("   ", row, flush=True)
        out["runs"].append(row)
        ok = [r for r in out["runs"] if r.get("ok")]
        if ok:
            ari = [r["ari"] for r in ok]
            bf1 = [r["bf1"] for r in ok]
            mu = sum(ari) / len(ari)
            out["n"] = len(ari)
            out["ari_mean"] = mu
            out["ari_sd"] = ((sum((x - mu) ** 2 for x in ari) / (len(ari) - 1)) ** 0.5
                             if len(ari) > 1 else 0.0)
            out["ari_min"] = min(ari)
            out["ari_max"] = max(ari)
            out["bf1_mean"] = sum(bf1) / len(bf1)
            out["bf1_max"] = max(bf1)
            out["ward_ari"] = 0.4138
            out["gap_vs_ward_pt"] = (mu - 0.4138) * 100.0
            out["old_single_run_ari"] = 0.5487
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", out_path)
    print("n=%s ari=%.4f+-%.4f [%.4f,%.4f] bf1=%.4f gap_vs_ward=%.2f pt" % (
        out.get("n"), out.get("ari_mean", 0), out.get("ari_sd", 0),
        out.get("ari_min", 0), out.get("ari_max", 0),
        out.get("bf1_mean", 0), out.get("gap_vs_ward_pt", 0)))


if __name__ == "__main__":
    main()
