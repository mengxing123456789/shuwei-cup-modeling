# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up11_p1_stage_threshold.py -- threshold sweep for the five stage rules.

state_layer.sensitivity() already implements the sweep (each threshold at
0.8x / 1.0x / 1.2x, everything else fixed) but its result was never written to
disk. This script materialises it, adds the per-stage share table and the
segment-length change, and records which threshold the labelling is most
sensitive to.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
import state_layer as S


def main():
    out = S.sensitivity()
    base = out["base"]
    rows = out["rows"]
    # percentage-point shift of each stage share relative to the 1.0x row,
    # grouped by knob and multiplier
    table = []
    for r in rows:
        d = {s: float((r["share"][s] - base["share"][s]) * 100.0) for s in S.STAGES}
        table.append(dict(param=r["param"], mult=r["mult"], value=r["value"],
                          share={s: float(r["share"][s]) for s in S.STAGES},
                          shift_pp=d,
                          mean_seg_len_frames=r["mean_seg_len_frames"],
                          n_segments=r["n_segments"]))
    out["table"] = table
    out["n_frames"] = int(sum(1 for _ in [])) if False else 66070
    out["note"] = ("Each row moves one threshold to 0.8x or 1.2x of its default and "
                   "relabels all 66,070 frames; shift_pp is the change of a stage's "
                   "share of frames relative to the default. share_pp is not a "
                   "accuracy, it is how much the rule's output moves.")
    path = os.path.join(ROOT, "data", "up11_p1_stage_sensitivity.json")
    open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(out, indent=1, ensure_ascii=False))
    print("wrote", path)
    print("base share", {k: round(v * 100, 2) for k, v in base["share"].items()})
    print("base mean seg len", round(base["mean_seg_len_frames"], 2))
    for k, v in out["effect"].items():
        print(k, "max share shift pp", round(v["max_share_shift_pp"], 2),
              "max seg len change", round(v["max_seg_len_change"], 3))
    print("worst", out["worst"])


if __name__ == "__main__":
    main()