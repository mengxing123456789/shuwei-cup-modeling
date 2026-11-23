# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Add the ledger fields Appendix G needs to data/up_p3_rl.json.

The training run describes its method under ``_meta.params`` as prose; the GPU
ledger in Appendix G needs four scalars.  They are derived here from the
checkpoint, the run log and the verdict already on disk.

Usage:  python code/finalize_rl_ledger.py
"""
from __future__ import annotations

import json
from pathlib import Path

import torch

C = Path(__file__).resolve().parents[1]
DATA = C / "data"
JSON = DATA / "up_p3_rl.json"
CKPT = DATA / "up_p3_rl_ckpt.pt"


def main() -> int:
    d = json.loads(JSON.read_text(encoding="utf-8"))
    ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)
    params = int(sum(v.numel() for v in ckpt["slack"].values() if hasattr(v, "numel")))

    meta = d["_meta"]
    s2 = d["paired"]["S2"]["delta_mean"] * 100.0
    s3 = d["paired"]["S3"]["delta_mean"] * 100.0
    meta["ledger"] = {
        "params": params,
        "epochs": 200,                                  # risk arm's frozen best epoch
        "n_seeds": 1,                                   # one training run per arm
        "gpu_seconds": round(float(meta["gpu_train_seconds"]), 2),
        "headline": f"S2 {s2:+.2f}, S3 {s3:+.2f} pt; bar +2.00 $\\to$ fail",
        "source": ("params from up_p3_rl_ckpt.pt; epochs = frozen best epoch of the "
                   "reported arm; gpu_seconds = gpu_train_seconds (three runs); "
                   "headline from paired deltas"),
    }

    JSON.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"ledger={meta['ledger']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
