# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Run-to-run spread of P1-a under each representative point.

The shipped ``p1a_gpu_segmentation.py`` is not bit-reproducible across runs:
two runs on identical inputs (``state_anchor_wrist.npz`` is bit-identical to
``state.npz``) gave test ARI 0.4765 and 0.4913.  Before any anchor effect can
be claimed, the noise band of a single run has to be measured, otherwise a
4-point "gain" may be nothing but a lucky draw.

This driver repeats the Part I training ``--repeats`` times per anchor and
writes mean / sd / min / max so the paper can quote a distribution instead of
one number.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
PY = sys.executable
ANCHORS = ("wrist", "palm", "tips")

CODE = r'''
import json, os, sys
sys.path.insert(0, r"%(here)s")
import p1a_gpu_segmentation as M
M.DATA = r"%(d)s"
M.MODELS = os.path.join(r"%(d)s", "models_rep%(tag)s")
os.makedirs(M.MODELS, exist_ok=True)
sys.argv = ["p1a", "--seeds", "3", "--epochs", "40"]
M.main()
j = json.load(open(os.path.join(M.DATA, "p1a_gpu_segmentation.json"), encoding="utf-8"))
print("ROW " + json.dumps(dict(
    height=j["_meta"]["height"], distance=j["_meta"]["distance"],
    val=j["_meta"]["val_mean_ari"],
    ari=j["test"]["mean_ari"], std=j["test"]["std_ari"],
    bf1=j["test"]["mean_boundary_f1"],
    bmae=j["test"]["mean_boundary_mae"])))
'''


def one(anchor, tag):
    d = os.path.join(DATA, "shadow_anchor_%s" % anchor)
    code = CODE % dict(here=HERE, d=d, tag=tag)
    t0 = time.time()
    p = subprocess.run([PY, "-c", code], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    secs = time.time() - t0
    row = None
    for line in p.stdout.splitlines():
        if line.startswith("ROW "):
            row = json.loads(line[4:])
    if row is None:
        return dict(ok=False, seconds=round(secs, 1),
                    stderr=p.stderr[-2000:], stdout=p.stdout[-1200:])
    row["ok"] = True
    row["seconds"] = round(secs, 1)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    anchors = [x for x in a.only.split(",") if x] or list(ANCHORS)
    out_path = os.path.join(DATA, "up13_repeat_spread.json")
    out = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            out = json.load(f)
    for anchor in anchors:
        runs = out.get(anchor, {}).get("runs", [])
        for i in range(a.repeats):
            tag = "r%d" % (len(runs) + 1)
            print("=== %s %s" % (anchor, tag), flush=True)
            row = one(anchor, tag)
            print("   ", row, flush=True)
            runs.append(row)
            ari = [r["ari"] for r in runs if r.get("ok")]
            bf1 = [r["bf1"] for r in runs if r.get("ok")]
            val = [r["val"] for r in runs if r.get("ok")]
            out[anchor] = dict(
                runs=runs,
                n=len(ari),
                ari_mean=sum(ari) / len(ari) if ari else None,
                ari_sd=(sum((x - sum(ari) / len(ari)) ** 2 for x in ari) / (len(ari) - 1)) ** 0.5
                if len(ari) > 1 else 0.0,
                ari_min=min(ari) if ari else None,
                ari_max=max(ari) if ari else None,
                bf1_mean=sum(bf1) / len(bf1) if bf1 else None,
                val_mean=sum(val) / len(val) if val else None,
            )
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", out_path)
    for k, v in out.items():
        print(k, "n=%d ari=%.4f+-%.4f [%.4f,%.4f]" % (
            v["n"], v["ari_mean"], v["ari_sd"], v["ari_min"], v["ari_max"]))


if __name__ == "__main__":
    main()
