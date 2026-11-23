# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p1b_final_verify.py -- 独立复算 data/up_p1b_final.json，逐条对账。

不经 up_p1b_final.py 的函数：只读原始 seed JSON 与 npz，自己重算一遍，
然后与 final.json 比。任何一条对不上就打印 FAIL 并以非零退出。
"""
import io
import json
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
FINAL = os.path.join(DATA, "up_p1b_final.json")
SEEDS = [20261120, 20261122, 20261123]
EXTRA = [20261121]
SRC = {
    20261120: ("up_p1b_dual.json", "up_p1b_probs.npz"),
    20261121: ("up_p1b_seed20261121.json", "up_p1b_probs_s20261121.npz"),
    20261122: ("up_p1b_seed20261122.json", "up_p1b_probs_s20261122.npz"),
    20261123: ("up_p1b_seed20261123.json", "up_p1b_probs_s20261123.npz"),
}
ARM = {"A": "A_baseline_replica", "C": "C_dual_plus_multitask"}
BASELINE_WORST = 0.7646370912154993
BASELINE_AP = 0.06755601550659424

fails, checks = [], 0


def ck(name, cond, detail=""):
    global checks
    checks += 1
    if not cond:
        fails.append(f"{name} :: {detail}")
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")


def close(a, b, tol=1e-12):
    return abs(float(a) - float(b)) <= tol


def main():
    F = json.load(open(FINAL, encoding="utf-8"))
    raw = {}
    for s in SEEDS + EXTRA:
        d = json.load(open(os.path.join(DATA, SRC[s][0]), encoding="utf-8"))
        ck(f"seed {s} _meta.seed", int(d["_meta"]["seed"]) == s)
        raw[s] = d

    # 1) per_seed 逐字段复算
    for s in SEEDS + EXTRA:
        d = raw[s]
        for a, k in ARM.items():
            arm = d["arms"][k]
            got = F["per_seed"][str(s)][a]
            ck(f"{s} {a} test_ap", close(got["test_ap"], arm["test_ap"]), f"{got['test_ap']:.12f}")
            ck(f"{s} {a} test_auc", close(got["test_auc"], arm["test_auc"]))
            ck(f"{s} {a} val_ap", close(got["val_ap"], arm["val_ap"]))
            ck(f"{s} {a} val_auc", close(got["val_auc"], arm["val_auc"]))
            ck(f"{s} {a} worst_env", close(got["worst_env"], min(e["auc_bad"] for e in arm["per_env"])))

    # 2) aggregate 复算（三个指定 seed）
    for a, k in ARM.items():
        rows = [raw[s]["arms"][k] for s in SEEDS]
        ck(f"agg {a} test_ap", close(F["aggregate"][a]["test_ap"],
                                     np.mean([r["test_ap"] for r in rows])))
        ck(f"agg {a} test_auc", close(F["aggregate"][a]["test_auc"],
                                      np.mean([r["test_auc"] for r in rows])))
        ck(f"agg {a} val_ap", close(F["aggregate"][a]["val_ap"],
                                    np.mean([r["val_ap"] for r in rows])))
        ck(f"agg {a} worst_env", close(F["aggregate"][a]["worst_env"],
                                       np.mean([min(e["auc_bad"] for e in r["per_env"]) for r in rows])))
    c_ap = np.mean([raw[s]["arms"][ARM["C"]]["test_ap"] for s in SEEDS])
    a_ap = np.mean([raw[s]["arms"][ARM["A"]]["test_ap"] for s in SEEDS])
    ck("agg ap_gain_pct(vs pre-reg baseline)", close(F["aggregate"]["ap_gain_pct"],
                                                     (c_ap / BASELINE_AP - 1.0) * 100.0))
    ck("agg ap_gain_pct_seed_matched", close(F["aggregate"]["ap_gain_pct_seed_matched"],
                                             (c_ap / a_ap - 1.0) * 100.0))
    c_worst = np.mean([min(e["auc_bad"] for e in raw[s]["arms"][ARM["C"]]["per_env"]) for s in SEEDS])
    a_worst = np.mean([min(e["auc_bad"] for e in raw[s]["arms"][ARM["A"]]["per_env"]) for s in SEEDS])
    ck("agg worst_env_delta", close(F["aggregate"]["worst_env_delta"], c_worst - BASELINE_WORST))
    ck("agg worst_env_delta_vs_A", close(F["aggregate"]["worst_env_delta_vs_A"], c_worst - a_worst))

    # 3) 判决三项复算
    ap_ok = min((c_ap / BASELINE_AP - 1.0) * 100.0, (c_ap / a_ap - 1.0) * 100.0) >= 15.0
    floor_ok = all(raw[s]["arms"][ARM["C"]]["test_ap"] >= 0.09 for s in SEEDS)
    worst_ok = (c_worst - BASELINE_WORST >= 0.0) and (c_worst - a_worst >= 0.0)
    ck("verdict.passes", F["verdict"]["passes"] == bool(ap_ok and floor_ok and worst_ok),
       f"recomputed={bool(ap_ok and floor_ok and worst_ok)}")
    ck("verdict denom: mean C AP", close(F["aggregate"]["C"]["test_ap"], c_ap))

    # 4) 决策层复算（C, seed 20261120）+ 各 seed yte 一致
    y_ref = None
    for s in SEEDS:
        z = np.load(os.path.join(DATA, SRC[s][1]))
        y = z["yte"]
        ck(f"seed {s} yte n=12143 / pos=231", len(y) == 12143 and int((y > 0.5).sum()) == 231,
           f"n={len(y)} pos={int((y > 0.5).sum())}")
        if y_ref is None:
            y_ref = y
        else:
            ck(f"seed {s} yte identical to 20261120", bool(np.array_equal(y_ref, y)))
    z = np.load(os.path.join(DATA, SRC[20261120][1]))
    y, p = z["yte"], z["pt_C"]
    drop, bad = p >= 0.5, y > 0.5
    tp, fp = int((drop & bad).sum()), int((drop & ~bad).sum())
    prec, rec = tp / (tp + fp), tp / int(bad.sum())
    good_rate = fp / int((~bad).sum())
    ck("decision precision_at_half", close(F["decision_layer"]["precision_at_half"], prec),
       f"{prec:.6f}")
    ck("decision recall_at_half", close(F["decision_layer"]["recall_at_half"], rec), f"{rec:.6f}")
    ck("decision good_dropped_rate", close(F["decision_layer"]["good_dropped_rate"], good_rate),
       f"{good_rate:.6f}")
    ck("decision drop_rate", close(F["decision_layer"]["drop_rate"], float(drop.mean())))
    print(f"    误丢好帧 {fp}/{int((~bad).sum())} = {good_rate:.2%}；"
          f"丢掉的帧里真坏帧占比 {prec:.2%}；坏帧召回 {rec:.2%}")

    print(f"\n{checks - len(fails)}/{checks} PASS")
    if fails:
        print("FAILED:")
        for f in fails:
            print("  -", f)
        raise SystemExit(1)
    print("VERIFY OK")


if __name__ == "__main__":
    main()