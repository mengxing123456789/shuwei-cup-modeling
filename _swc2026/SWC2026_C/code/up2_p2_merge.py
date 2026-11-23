# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""Merge the three arm files into data/up2_p2.json and compare against v1.

Reads  data/up2_p2_arm{A,B,C}.json          (written by up2_p2_models.py)
       data/up_p2_final.json                (v1 3-seed baseline)
Writes data/up2_p2.json
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
LENS = [6, 18, 30, 60]
NAMES = dict(A="A_tcn_transformer", B="B_ridge_residual", C="C_aug_mtl")
GATE = dict(rmse_3d_max_cm=5.50, q90_max_cm=9.00, coverage_min=0.88, coverage_max=0.93,
            stat="L30 rmse_3d mean over 3 seeds")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    arms = {}
    for k in ("A", "B", "C"):
        p = os.path.join(DATA, f"up2_p2_arm{k}.json")
        if not os.path.exists(p):
            print(f"missing {p}")
            continue
        arms[k] = load(p)

    out = dict(_meta=dict(script="code/up2_p2_merge.py",
                          sources=[f"data/up2_p2_arm{k}.json" for k in arms] + ["data/up_p2_final.json"],
                          lens=LENS, gate=GATE,
                          protocol="same windows/split/conformal as p2_interval.py; "
                                   "hand channels canonicalised; epochs chosen on validation, "
                                   "test evaluated once per config",
                          note="each config is 3 seeds x 4 horizons; ridge_perh is the "
                               "deterministic per-horizon ridge backbone used by B",
                          generated_at="2026-11-21"),
               configs={}, reference={}, comparison={}, gate={}, passes_any=False,
               decision_layer={})

    best = None
    for k, st in arms.items():
        name = NAMES[k]
        agg = st["aggregate"]
        a = agg["L30"]
        out["configs"][name] = dict(
            family=name, arms_file=f"data/up2_p2_arm{k}.json",
            params=a["params"], train_seconds_per_lens=a["train_seconds_mean"],
            wall_seconds=st["_meta"]["seconds"], gpu_train_seconds=st["_meta"]["gpu_train_seconds"],
            gate=st["gate"], passes=st["passes"],
            aggregate={L: dict(
                rmse_3d_cm=agg[L]["rmse_3d_cm"], q90_cm=agg[L]["q90_cm"],
                coverage_test=agg[L]["coverage_test"],
                pinball_test_cm=agg[L]["pinball_test_cm"],
                train_seconds_mean=agg[L]["train_seconds_mean"], params=agg[L]["params"])
                for L in (f"L{x}" for x in LENS) if L in agg},
            per_seed={s: {L: {kk: v[L][kk] for kk in
                             ("rmse_3d_cm", "q90_cm", "coverage_test", "pinball_test_cm",
                              "best_epoch", "train_seconds", "val_rmse_3d_cm") if kk in v[L]}
                          for L in (f"L{x}" for x in LENS) if L in v}
                      for s, v in st["per_seed"].items()},
            per_horizon=st["per_horizon"], ensemble=st["ensemble"],
            decision_layer=st.get("decision_layer"),
            ridge_perh=st.get("ridge_perh"))
        if st["passes"] and (best is None or a["rmse_3d_cm"]["mean"] < best[1]):
            best = (name, a["rmse_3d_cm"]["mean"])

    # config D (validation-chosen ridge x TCN shrinkage; L30 only, one test read)
    tp = os.path.join(DATA, "up2_p2_tune.json")
    if os.path.exists(tp):
        t = load(tp)
        res = t["config_D"]
        out["configs"]["D_val_shrinkage"] = dict(
            family="D_val_shrinkage", arms_file="data/up2_p2_tune.json",
            params="ridge backbone (deterministic) + TCN A (177796)",
            train_seconds_per_lens=t["_meta"]["epochs"],
            wall_seconds=None, gpu_train_seconds=None,
            gate=t["gate"], passes=t["passes"],
            aggregate={"L30": dict(
                rmse_3d_cm=dict(mean=res["rmse_3d_cm"], sd=None, values=[res["rmse_3d_cm"]]),
                q90_cm=dict(mean=res["q90_cm"], sd=None, values=[res["q90_cm"]]),
                coverage_test=dict(mean=res["coverage_test"], sd=None, values=[res["coverage_test"]]),
                pinball_test_cm=dict(mean=None, values=[]),
                train_seconds_mean=None, params=None)},
            per_seed={"val_selected": {"L30": {"rmse_3d_cm": res["rmse_3d_cm"],
                                               "q90_cm": res["q90_cm"],
                                               "coverage_test": res["coverage_test"],
                                               "val_rmse_3d_cm": res["val_rmse_3d_cm"]}}},
            per_horizon={"L30": {"mean_over_seeds": res["per_horizon_rmse_3d_cm"]}},
            ensemble={}, decision_layer=None, ridge_perh=None,
            selection=t["chosen_backbone"] | {"w_ridge": t["chosen_blend"]["w_ridge"]},
            note="L=30 only; w(ridge)=0.70 and backbone cap=150/alpha=3000 chosen on validation")
        if t["passes"] and (best is None or res["rmse_3d_cm"] < best[1]):
            best = ("D_val_shrinkage", res["rmse_3d_cm"])

    # v1 baseline for the comparison table
    v1p = os.path.join(DATA, "up_p2_final.json")
    if os.path.exists(v1p):
        v1 = load(v1p)
        out["reference"]["v1_quantile"] = dict(
            source="data/up_p2_final.json",
            aggregate={L: dict(rmse_3d_cm=v1["aggregate"][L]["rmse_3d_cm"],
                               q90_cm=v1["aggregate"][L]["q90_cm"],
                               coverage_test=v1["aggregate"][L]["coverage_test"])
                       for L in v1["aggregate"] if L.startswith("L")},
            verdict=v1.get("verdict"), gate=v1.get("gate"))

    ridge = next((c["ridge_perh"] for c in out["configs"].values() if c.get("ridge_perh")), None)
    if ridge:
        out["reference"]["ridge_perh"] = dict(
            source="per-horizon ridge (alpha=3000, canonical, rel+hand features), same split",
            metrics={L: dict(rmse_3d_cm=ridge[L]["rmse_3d_cm"], q90_cm=ridge[L]["q90_cm"],
                             coverage_test=ridge[L]["coverage_test"],
                             pinball_test_cm=ridge[L].get("pinball_test_cm"),
                             train_seconds=ridge[L].get("train_seconds"))
                     for L in ridge})

    # L=30 comparison + deltas
    for L in [f"L{x}" for x in LENS]:
        row = {}
        for name, c in out["configs"].items():
            if L in c["aggregate"]:
                row[name] = dict(rmse_3d_cm=c["aggregate"][L]["rmse_3d_cm"]["mean"],
                                 q90_cm=c["aggregate"][L]["q90_cm"]["mean"],
                                 coverage=c["aggregate"][L]["coverage_test"]["mean"])
        if ridge and L in ridge:
            row["ridge_perh"] = dict(rmse_3d_cm=ridge[L]["rmse_3d_cm"],
                                     q90_cm=ridge[L]["q90_cm"],
                                     coverage=ridge[L]["coverage_test"])
        if "v1_quantile" in out["reference"] and L in out["reference"]["v1_quantile"]["aggregate"]:
            v = out["reference"]["v1_quantile"]["aggregate"][L]
            row["v1_quantile"] = dict(rmse_3d_cm=v["rmse_3d_cm"]["mean"],
                                      q90_cm=v["q90_cm"]["mean"], coverage=v["coverage_test"]["mean"])
        out["comparison"][L] = row

    out["gate"] = {name: dict(passes=c["passes"], detail=c["gate"]["detail"],
                              n_failed=c["gate"]["n_failed"])
                   for name, c in out["configs"].items()}
    out["passes_any"] = bool(best)
    out["best_config"] = dict(name=best[0], rmse_3d_cm_L30=best[1]) if best else None
    out["decision_layer"] = {name: c["decision_layer"] for name, c in out["configs"].items()
                             if c.get("decision_layer")}

    dst = os.path.join(DATA, "up2_p2.json")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"wrote {dst}")
    hdr = f"{'config':22s}" + "".join(f"{L:>18s}" for L in ["L6", "L18", "L30", "L60"])
    print(hdr)
    for name in list(out["configs"]) + ["ridge_perh", "v1_quantile"]:
        cells = []
        for L in ["L6", "L18", "L30", "L60"]:
            v = out["comparison"].get(L, {}).get(name)
            cells.append(f"{v['rmse_3d_cm']:7.3f}/{v['q90_cm']:5.2f}" if v else " " * 13)
        print(f"{name:22s}" + "".join(f"{c:>18s}" for c in cells))
    for name, g in out["gate"].items():
        print(f"[{name}] {'PASS' if g['passes'] else 'FAIL'}  {g['detail']}")
    print(f"passes_any={out['passes_any']} best={out['best_config']}")


if __name__ == "__main__":
    main()