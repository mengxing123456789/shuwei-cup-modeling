
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""学习率敏感性：C0 与 C3-A 在 1.0 s / 2.0 s 两档，lr ∈ {5e-4, 1.5e-3, 3e-3}。

seed 固定 20261120（与主实验同种子，便于同表对照）。
落下 data/pre_p2_lr.json，不覆盖任何现有 json。
"""
import json
import os

from common import DATA
from pre_common import build_cache
from pre_downstream import train_arm

OUT = os.path.join(DATA, "pre_p2_lr.json")
LRs = [5e-4, 1.5e-3, 3e-3]
SEED = 20261120


def main():
    cache = build_cache()
    runs = []
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            runs = json.load(f).get("runs", [])
    done = {(r["lr"], r["arm"], r["L"]) for r in runs}
    for lr in LRs:
        for arm, task in (("C0", "A"), ("C3", "A")):
            for L in (30, 60):
                if (lr, arm, L) in done:
                    continue
                r = train_arm(cache, arm, task, SEED, L, lr=lr)
                runs.append(dict(lr=lr, arm=arm, task=task, L=L,
                                 rmse_cm=r["rmse_cm"],
                                 endpoint_rmse_cm=r["endpoint_rmse_cm"],
                                 median_cm=r["median_cm"], q90_cm=r["q90_cm"],
                                 best_epoch=r["best_epoch"],
                                 epochs_run=r["epochs_run"],
                                 val_rmse_cm=r["val_rmse_cm"],
                                 seconds=r["seconds"],
                                 curve=[dict(epoch=c["epoch"],
                                             train=c["train_rmse_cm"],
                                             val=c["val_rmse_cm"]) for c in r["curve"]]))
                with open(OUT, "w", encoding="utf-8", newline="\n") as f:
                    json.dump({"_meta": dict(seed=SEED, LRs=LRs, epochs=25,
                                             note="C0 从零 / C3-A 掩码重构预训练微调；只跑 L30/L60"),
                               "runs": runs}, f, ensure_ascii=False, indent=1)
                print(f"lr={lr:g} {arm} L{L} rmse={r['rmse_cm']:.3f} "
                      f"best_ep={r['best_epoch']} {r['seconds']}s", flush=True)

    # 汇总成一行一 (lr, arm)
    rows = []
    for lr in LRs:
        for arm in ("C0", "C3"):
            d = dict(lr=lr, arm=arm)
            for L in (30, 60):
                m = [x for x in runs if x["lr"] == lr and x["arm"] == arm and x["L"] == L]
                if m:
                    d[f"rmse_L{L}"] = m[0]["rmse_cm"]
                    d[f"best_ep_L{L}"] = m[0]["best_epoch"]
            rows.append(d)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"_meta": dict(seed=SEED, LRs=LRs, epochs=25,
                                 note="C0 从零 / C3-A 掩码重构预训练微调；只跑 L30/L60"),
                   "runs": runs, "rows": rows}, f, ensure_ascii=False, indent=1)
    print(json.dumps(rows, ensure_ascii=False))
    print("->", OUT)


if __name__ == "__main__":
    main()