# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Add derived summaries to data/up15_p1a_final_repeats.json.

The repeat runner stores per-run rows; the paper also needs the mean boundary
error and the range of decoding heights the validation grid picked.  Those are
computed here rather than in the runner so the raw run rows stay untouched.
"""
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "data"
P = D / "up15_p1a_final_repeats.json"

d = json.loads(P.read_text(encoding="utf-8"))
runs = [r for r in d["runs"] if r.get("ok")]
if not runs:
    raise SystemExit("no successful runs in up15")

bmae = [r["bmae"] for r in runs]
heights = [r["height"] for r in runs]
dists = [r["distance"] for r in runs]
vals = [r["val_ari"] for r in runs]

d["bmae_mean"] = sum(bmae) / len(bmae)
d["bmae_min"] = min(bmae)
d["bmae_max"] = max(bmae)
d["height_min"] = min(heights)
d["height_max"] = max(heights)
d["distance_used"] = max(set(dists), key=dists.count)
d["val_ari_min"] = min(vals)
d["val_ari_max"] = max(vals)
d["derived_from"] = "runs[]"

P.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
print("bmae_mean %.4f  heights %.2f-%.2f  distance %d  val %.4f-%.4f"
      % (d["bmae_mean"], d["height_min"], d["height_max"], d["distance_used"],
         d["val_ari_min"], d["val_ari_max"]))
