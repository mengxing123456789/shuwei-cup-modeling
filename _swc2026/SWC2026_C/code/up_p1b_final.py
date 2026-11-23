# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up_p1b_final.py -- P1-b 收口：多 seed 判决 + 决策层阈值指标。

只读已有 data/*.json 与 data/up_p1b_probs*.npz；缺的 seed 由 up_p1b_dual.py 补跑
（--arms A,C，其余协议与预注册完全一致）。只写 data/up_p1b_final.json。

判决（任务书给定）：
  PASS =  三 seed 平均 test AP 相对基线提升 >= 15%
       AND 三个 seed 的 C 臂 test AP 都 >= 0.09
       AND worst per-env AUC 均值不降（相对预注册基线 0.7646，且相对 A 臂不降）

决策层：把 C 臂 test 概率按 0.5 阈值当坏帧丢弃，复用 p1b_cost_threshold.json 的
per-frame 口径，报 precision_at_half / recall_at_half 与误丢好帧率。
"""
import io
import json
import os
import subprocess
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PY = os.environ.get("MM_PYTHON") or sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
DUAL = os.path.join(HERE, "up_p1b_dual.py")
OUT = os.path.join(DATA, "up_p1b_final.json")

BASELINE_WORST = 0.7646370912154993
BASELINE_TEST_AP = 0.06755601550659424
BAR = dict(
    primary="test AUC >= 0.85 OR test AP >= 0.09",
    secondary=("if primary fails: AP relative gain >= 15% AND val same direction "
               "AND worst per-env AUC drop <= 0.02 vs baseline 0.7646370912154993"),
    worst_env_baseline=BASELINE_WORST,
)

DESIGNATED = [20261120, 20261122, 20261123]   # 判决用的三个 seed
EXTRA = [20261121]                            # 已存在的有效额外 seed（不进判决，仅作稳健性旁证）
FILES = {
    20261120: ("up_p1b_dual.json", "up_p1b_probs.npz"),
    20261121: ("up_p1b_seed20261121.json", "up_p1b_probs_s20261121.npz"),
    20261122: ("up_p1b_seed20261122.json", "up_p1b_probs_s20261122.npz"),
    20261123: ("up_p1b_seed20261123.json", "up_p1b_probs_s20261123.npz"),
}
ARM_KEY = {"A": "A_baseline_replica", "C": "C_dual_plus_multitask"}
RUNS = {}


def arm_summary(arm):
    worst = min(e["auc_bad"] for e in arm["per_env"])
    worst_env = [e["env"] for e in arm["per_env"] if e["auc_bad"] == worst][0]
    return dict(
        val_auc=arm["val_auc"], val_ap=arm["val_ap"],
        test_auc=arm["test_auc"], test_ap=arm["test_ap"],
        best_epoch=arm["best_epoch"], params=arm["params"], seconds=arm["seconds"],
        worst_env=worst, worst_env_name=worst_env,
        per_env={e["env"]: dict(n=e["n"], positives=e["positives"], auc_bad=e["auc_bad"])
                 for e in arm["per_env"]},
    )


def ensure_seed(seed):
    """缺什么补什么；已有 JSON 且含 A/C 两臂就直接复用（不重跑）。"""
    jname, nname = FILES[seed]
    jpath = os.path.join(DATA, jname)
    if os.path.exists(jpath):
        d = json.load(open(jpath, encoding="utf-8"))
        if all(k in d.get("arms", {}) for k in ARM_KEY.values()):
            assert int(d["_meta"]["seed"]) == seed, (seed, d["_meta"]["seed"])
            print(f"[reuse] seed {seed} <- {jname}")
            return d
    print(f"[run] seed {seed} arms A,C -> {jname} (this takes ~80 s)")
    cmd = [PY, DUAL, "--arms", "A,C", "--seed", str(seed),
           "--out", jpath, "--outnpz", os.path.join(DATA, nname)]
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        raise SystemExit(f"up_p1b_dual.py failed for seed {seed} (exit {r.returncode})")
    d = json.load(open(jpath, encoding="utf-8"))
    assert int(d["_meta"]["seed"]) == seed
    return d


def collect():
    per_seed = {}
    for seed in DESIGNATED + EXTRA:
        d = ensure_seed(seed)
        per_seed[str(seed)] = {a: arm_summary(d["arms"][k]) for a, k in ARM_KEY.items()}
        RUNS[str(seed)] = dict(seconds=d["_meta"]["seconds"], arms_run=d["_meta"]["arms_run"])
        write_final(per_seed, final=False)          # 每跑完一个 seed 立即落盘中间结果
    return per_seed


def agg(per_seed, seeds):
    out = {}
    for a in ("A", "C"):
        rows = [per_seed[str(s)][a] for s in seeds]
        out[a] = dict(
            n_seeds=len(seeds),
            val_auc=float(np.mean([r["val_auc"] for r in rows])),
            val_ap=float(np.mean([r["val_ap"] for r in rows])),
            test_auc=float(np.mean([r["test_auc"] for r in rows])),
            test_ap=float(np.mean([r["test_ap"] for r in rows])),
            test_auc_std=float(np.std([r["test_auc"] for r in rows], ddof=1)) if len(rows) > 1 else 0.0,
            test_ap_std=float(np.std([r["test_ap"] for r in rows], ddof=1)) if len(rows) > 1 else 0.0,
            test_ap_min=float(min(r["test_ap"] for r in rows)),
            test_ap_max=float(max(r["test_ap"] for r in rows)),
            worst_env=float(np.mean([r["worst_env"] for r in rows])),
            worst_env_per_seed={str(s): per_seed[str(s)][a]["worst_env"] for s in seeds},
        )
    # ap_gain_pct = 相对预注册基线（_meta.bar.baseline_repro.test_ap）的倍数，与 bar 同口径
    out["ap_gain_pct"] = float((out["C"]["test_ap"] / BASELINE_TEST_AP - 1.0) * 100.0)
    # 更保守的配对口径：同 seed 的 A 臂三 seed 均值
    out["ap_gain_pct_seed_matched"] = float((out["C"]["test_ap"] / out["A"]["test_ap"] - 1.0) * 100.0)
    out["baseline_reference"] = dict(test_ap=BASELINE_TEST_AP, worst_env=BASELINE_WORST,
                                     source="data/p1b_gpu.json (production, seed 20261120)")
    out["worst_env_delta"] = float(out["C"]["worst_env"] - BASELINE_WORST)
    out["worst_env_delta_vs_A"] = float(out["C"]["worst_env"] - out["A"]["worst_env"])
    return out


def decision_layer(per_seed, seeds):
    """坏帧 = 正类；p>=0.5 → 判为坏帧丢弃。报丢弃决策的 precision/recall（per-frame）。"""
    per = {}
    for s in seeds:
        zp = os.path.join(DATA, FILES[s][1])
        z = np.load(zp)
        y = z["yte"]
        p = z["pt_C"]
        drop = p >= 0.5
        bad = y > 0.5
        tp = int(np.sum(drop & bad))
        fp = int(np.sum(drop & ~bad))
        fn = int(np.sum(~drop & bad))
        n_bad, n_good = int(bad.sum()), int((~bad).sum())
        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else None
        rec = float(tp / n_bad) if n_bad > 0 else None
        per[str(s)] = dict(
            n_test=int(len(y)), positives=n_bad, drop_rate=float(drop.mean()),
            dropped=int(drop.sum()), tp=tp, fp=fp, fn=fn,
            precision_at_half=prec, recall_at_half=rec,
            good_dropped=fp, good_dropped_rate=float(fp / n_good) if n_good else None,
            good_kept_rate=float(1.0 - fp / n_good) if n_good else None,
        )
    head = per[str(seeds[0])]
    return dict(
        arm="C_dual_plus_multitask", seed=int(seeds[0]),
        threshold=0.5,
        definition=("bad frame = positive; drop iff p_bad >= 0.5. precision_at_half = "
                    "P(bad | dropped); recall_at_half = P(dropped | bad); good_dropped_rate = "
                    "share of good frames lost (= 1 - good_kept, the p1b_cost_threshold ratio convention)"),
        precision_at_half=head["precision_at_half"],
        recall_at_half=head["recall_at_half"],
        drop_rate=head["drop_rate"],
        good_dropped=head["good_dropped"],
        good_dropped_rate=head["good_dropped_rate"],
        good_kept_rate=head["good_kept_rate"],
        per_seed=per,
    )


def write_final(per_seed, final=True):
    seeds = [s for s in DESIGNATED if str(s) in per_seed]
    a = agg(per_seed, seeds) if len(seeds) == len(DESIGNATED) else None
    a4 = agg(per_seed, DESIGNATED + EXTRA) if len(per_seed) == len(DESIGNATED) + len(EXTRA) else None
    dl = decision_layer(per_seed, [s for s in DESIGNATED if str(s) in per_seed]) if seeds else None

    verdict = dict(passes=False, reason="incomplete: not all seeds collected yet")
    if a is not None:
        c_aps = [per_seed[str(s)]["C"]["test_ap"] for s in DESIGNATED]
        c_aucs = [per_seed[str(s)]["C"]["test_auc"] for s in DESIGNATED]
        ok_gain = min(a["ap_gain_pct"], a["ap_gain_pct_seed_matched"]) >= 15.0
        ok_floor = all(v >= 0.09 for v in c_aps)
        ok_worst_base = a["worst_env_delta"] >= 0.0
        ok_worst_a = a["worst_env_delta_vs_A"] >= 0.0
        ok_worst = ok_worst_base and ok_worst_a
        ok_drop_tol = a["worst_env_delta"] >= -0.02
        primary_seed = [bool(u >= 0.85 or p >= 0.09) for u, p in zip(c_aucs, c_aps)]
        val_same_dir = a["C"]["val_ap"] > a["A"]["val_ap"]
        verdict = dict(
            passes=bool(ok_gain and ok_floor and ok_worst),
            reason=(
                f"三 seed (20261120/20261122/20261123) C 臂: "
                f"AP gain {a['ap_gain_pct']:+.2f}% vs 预注册基线 0.067556 "
                f"({a['ap_gain_pct_seed_matched']:+.2f}% 配对 vs 同 seed A 均值) — >=15%: "
                f"{'yes' if ok_gain else 'no'}; "
                f"C test AP min {min(c_aps):.6f} (三个都 >=0.09: {'yes' if ok_floor else 'no'}); "
                f"worst per-env AUC 均值 {a['C']['worst_env']:.6f} vs 基线 {BASELINE_WORST:.6f} "
                f"(delta {a['worst_env_delta']:+.6f}, 不降: {'yes' if ok_worst_base else 'no'}; "
                f"恰好超出 0.02 容差 {abs(a['worst_env_delta']) - 0.02:+.2e}); "
                f"vs A 臂均值 {a['A']['worst_env']:.6f} (delta {a['worst_env_delta_vs_A']:+.6f}, "
                f"不降: {'yes' if ok_worst_a else 'no'}). "
                f"结论: 单 seed (20261120) 三项全达标但不稳 —— 20261122/20261123 的 worst per-env AUC "
                f"分别 {per_seed['20261122']['C']['worst_env']:.4f} / {per_seed['20261123']['C']['worst_env']:.4f}，"
                f"均低于基线；AP 提升由三 seed 一致给出，AUC 侧反而略降。"),
            checks=dict(
                ap_gain_ge_15pct=bool(ok_gain),
                all_seed_ap_ge_0_09=bool(ok_floor),
                primary_bar_met_per_seed=primary_seed,
                secondary_ap_gain_ge_15pct=bool(ok_gain),
                secondary_val_same_direction=bool(val_same_dir),
                secondary_worst_drop_le_0_02=bool(ok_drop_tol),
                worst_env_not_lower_vs_baseline=bool(ok_worst_base),
                worst_env_not_lower_vs_A=bool(ok_worst_a),
                worst_env_delta_over_tolerance_by=float(abs(a["worst_env_delta"]) - 0.02),
            ),
            c_test_ap_per_seed={str(s): per_seed[str(s)]["C"]["test_ap"] for s in DESIGNATED},
            c_test_auc_per_seed={str(s): per_seed[str(s)]["C"]["test_auc"] for s in DESIGNATED},
            c_worst_env_per_seed={str(s): per_seed[str(s)]["C"]["worst_env"] for s in DESIGNATED},
        )

    payload = dict(
        _meta=dict(
            script="up_p1b_final.py",
            source_script="up_p1b_dual.py",
            seeds=DESIGNATED,
            extra_seeds=EXTRA,
            bar=BAR,
            baseline=dict(source="data/p1b_gpu.json (production train_gpu_p1b.py)",
                          test_auc=0.8220322044197129, test_ap=0.06755601550659424,
                          val_auc=0.8852539948743638, worst_env=BASELINE_WORST),
            note=("seed 20261121 and 20261122 pre-existed in data/ and are genuinely distinct runs "
                  "(seeds verified in _meta), so they were reused, not re-run. The three seeds that "
                  "enter the verdict are 20261120 / 20261122 / 20261123 per the task; 20261121 is "
                  "carried as an extra robustness seed and is included in aggregate_4seed. "
                  "worst per-env AUC is strongly seed-sensitive: the A arm itself averages 0.7393 over "
                  "the three seeds, i.e. -0.0253 below its own seed-20261120 value 0.7646, so the "
                  "criterion 'not lower than 0.7646' is stricter than a seed-matched control. Against "
                  "the seed-matched A mean C is +0.0053; against the single-seed production baseline C "
                  "is -0.0200 (4.2e-5 beyond the pre-registered 0.02 tolerance). The verdict applies the "
                  "stricter reading; both deltas are in aggregate."),
            run_seconds=dict(RUNS),
            status="final" if final else "intermediate (a seed is still running)",
            generated_by=os.path.basename(__file__),
            aggregates_use=DESIGNATED,
        ),
        per_seed=per_seed,
        aggregate=a if a is not None else {"note": "pending"},
        aggregate_4seed=a4 if a4 is not None else None,
        decision_layer=dl if dl is not None else {"note": "pending"},
        verdict=verdict,
    )
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)
    return payload


def main():
    print(f"device check: numpy {np.__version__}")
    per_seed = collect()
    payload = write_final(per_seed, final=True)
    a = payload["aggregate"]
    v = payload["verdict"]
    dl = payload["decision_layer"]
    print("\n=== per-seed C ===")
    for s in DESIGNATED:
        c = per_seed[str(s)]["C"]
        print(f"{s}  testAUC={c['test_auc']:.6f} testAP={c['test_ap']:.6f} "
              f"worst={c['worst_env']:.6f} valAUC={c['val_auc']:.6f} valAP={c['val_ap']:.6f}")
    print("=== per-seed A ===")
    for s in DESIGNATED:
        aa = per_seed[str(s)]["A"]
        print(f"{s}  testAUC={aa['test_auc']:.6f} testAP={aa['test_ap']:.6f} "
              f"worst={aa['worst_env']:.6f}")
    print("=== decision layer (C, seed %d) ===" % dl["seed"])
    print(f"precision_at_half={dl['precision_at_half']:.4f} recall_at_half={dl['recall_at_half']:.4f} "
          f"drop_rate={dl['drop_rate']:.4f} good_dropped_rate={dl['good_dropped_rate']:.4f}")
    print("\nsaved ->", OUT)
    print(f"P1BFINAL {str(v['passes']).lower()} ap_gain={a['ap_gain_pct']:.2f}pct "
          f"worst_env_delta={a['worst_env_delta']:+.4f}")
    print(f"[detail] ap_gain_seed_matched={a['ap_gain_pct_seed_matched']:+.2f}pct "
          f"worst_env_delta_vs_A={a['worst_env_delta_vs_A']:+.4f} "
          f"checks={v['checks']}")


if __name__ == "__main__":
    main()