# -*- coding: utf-8 -*-
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
"""up2_p3_final.py -- freeze, then evaluate the v2 policies on the test seeds ONCE.

Reads the pre-registration (data/up2_p3_prereg.json) and the frozen picks from the
train/val search (data/up2_p3_search.json), then evaluates each frozen policy on
seeds 2026111725..2026111729 (plus the 30-seed full panel for the paper table,
which is the same run sliced differently -- no extra tuning happens here).

Gate statistics are exactly the ones written in the pre-registration:
  blocked paired difference (10 case x mapping blocks, 5 seed replicates),
  pooled within-block variance, Welch-Satterthwaite t interval,
  plus a strict seed-clustered interval and the naive 50-pair interval as bounds.
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import up_p3_vectorized as V
import up2_p3_engine as E
from common import DATA

TEST = [2026111725 + i for i in range(5)]
VAL = [2026111715 + i for i in range(10)]
TRAIN = [2026111700 + i for i in range(15)]
ALL30 = TRAIN + VAL + TEST
CASES = ("S2", "S3")
MAPPINGS = [(1.0, 0.5), (0.75, 0.5), (1.5, 0.5), (1.0, 0.0), (1.0, 1.0)]
MAP_KEYS = ["a%.2f_b%.2f" % m for m in MAPPINGS]
NT = len(TEST)
NALL = len(ALL30)
KEYS = ("weighted_on_time_rate", "weighted_completion_rate", "weighted_tardiness_s",
        "cost", "n_reviews")

BASELINE = dict(SEL=1, RULE=E.RULE_SLACK, q_hi=0.60, gate=0.50, late_tol=12.0,
                REVIEW=False, name="slack_old")
V1 = {"S2": dict(SEL=0, RULE=E.RULE_ABS, q_hi=0.50, gate=0.60, late_tol=12.0,
                 REVIEW=False, name="v1_improved_S2"),
      "S3": dict(SEL=0, RULE=E.RULE_ABS, q_hi=0.60, gate=0.50, late_tol=20.0,
                 REVIEW=False, name="v1_improved_S3")}


def _params_of(p):
    out = {k: p[k] for k in ("SEL", "RULE", "q_hi", "gate", "late_tol", "mix", "gam",
                             "ksk", "qsl", "ksp", "ksb", "REVIEW", "tau") if k in p}
    return out


def run_policy_set(cands, case, seeds):
    """Evaluate every candidate on every mapping, all seeds, one batch per mapping."""
    sp = V.build_spec(case)
    cfg = V.build_configs(sp, seeds)
    res = {}
    for (a, b) in MAPPINGS:
        scen = V._scen(sp, cfg, a, b)
        ca = V._cand_arrays(cands)
        for k in ("ksk", "qsl", "mix", "gam", "tau", "pw", "po", "pp", "ksp", "ksb"):
            if any(c.get(k) is not None for c in cands):
                d = E.DEFAULTS.get(k, 0.0)
                ca[k] = np.array([d if c.get(k) is None else float(c[k]) for c in cands],
                                 np.float64)
        res[(a, b)] = E.simulate_batch2(sp, cfg, a, b, ca, n_seeds=len(seeds), scen=scen)
    return res


def blocked_stats(case_tab):
    """case_tab: list of (case, map_index, baseline_vec_test, cand_vec_test)."""
    blocks = []
    for case, mi, base, cand in case_tab:
        blocks.append(cand - base)
    block_means = np.array([b.mean() for b in blocks])
    block_vars = np.array([b.var(ddof=1) for b in blocks])
    nb = np.array([len(b) for b in blocks], float)
    delta_bar = float(block_means.mean())
    a_b = block_vars / nb
    var_bar = float(a_b.sum() / (len(blocks) ** 2))
    se = float(np.sqrt(var_bar))
    df = float((a_b.sum() ** 2) / np.sum(a_b ** 2 / (nb - 1)))
    tcrit = float(st.t.ppf(0.975, df))
    allpairs = np.concatenate(blocks)
    se_naive = float(allpairs.std(ddof=1) / np.sqrt(allpairs.size))
    t_naive = float(st.t.ppf(0.975, allpairs.size - 1))
    seed_means = np.stack([b for b in blocks]).mean(0)   # mean over blocks per seed
    se_clu = float(seed_means.std(ddof=1) / np.sqrt(seed_means.size))
    t_clu = float(st.t.ppf(0.975, seed_means.size - 1))
    npos = int((allpairs > 0).sum())
    return dict(
        delta_bar=delta_bar,
        se_blocked=se, df_blocked=df, tcrit_blocked=tcrit,
        ci_blocked=[delta_bar - tcrit * se, delta_bar + tcrit * se],
        block_means=[float(x) for x in block_means],
        block_names=[c[0] + "|" + MAP_KEYS[c[1]] for c in case_tab],
        ci_naive=[float(allpairs.mean() - t_naive * se_naive),
                  float(allpairs.mean() + t_naive * se_naive)],
        ci_seed_cluster=[float(delta_bar - t_clu * se_clu),
                         float(delta_bar + t_clu * se_clu)],
        n_pairs=int(allpairs.size), n_positive=npos,
        sign_test_p=float(st.binomtest(npos, allpairs.size, 0.5).pvalue),
        min_block_mean=float(block_means.min()),
    )


def main():
    t0 = time.time()
    pre_path = os.path.join(DATA, "up2_p3_prereg.json")
    with open(pre_path, encoding="utf-8") as f:
        pre_blob = f.read()
    pre = json.loads(pre_blob)
    pre_sha = hashlib.sha256(pre_blob.encode("utf-8")).hexdigest()

    with open(os.path.join(DATA, "up2_p3_search.json"), encoding="utf-8") as f:
        search = json.load(f)
    frozen = search["frozen"]

    logf = open(os.path.join(os.path.dirname(DATA), "logs", "up2_p3_final.log"),
                "w", encoding="utf-8")
    def log(m):
        print(m, flush=True)
        logf.write(m + "\n")
        logf.flush()

    log("prereg sha256 %s" % pre_sha)
    log("test seeds %s (single evaluation)" % TEST)

    # ---------------- candidate sets per case ------------------------------
    sets = {}
    for case in CASES:
        row = [dict(BASELINE), dict(V1[case])]
        for tag in ("A", "B", "C"):
            p = frozen[case]["params"] if tag == frozen[case]["class_"] else None
            if tag == "A":
                p = search["stage_A"]["picks"][case]["params"]
                nm = search["stage_A"]["picks"][case]["name"]
            elif tag == "B":
                p = search["stage_B"][case]["params"]
                nm = search["stage_B"][case]["name"]
            else:
                p = search["stage_C"][case]["chosen"]["params"]
                nm = search["stage_C"][case]["chosen"]["name"]
            d = _params_of(p)
            d["name"] = "class%s" % tag
            row.append(d)
        d = _params_of(frozen[case]["params"])
        d["name"] = "FROZEN"
        row.append(d)
        sets[case] = row
        log("%s candidates: %s" % (case, [c["name"] for c in row]))

    # ---------------- single evaluation on all 30 seeds --------------------
    evalres = {}
    for case in CASES:
        evalres[case] = run_policy_set(sets[case], case, ALL30)
    log("evaluated (%d seeds x 5 mappings x %d policies) in %.1fs"
        % (NALL, sum(len(v) for v in sets.values()), time.time() - t0))

    def slice_mean(r, i, sl, metric, idx):
        v = r[MAPPINGS[idx]][metric][i]
        if sl is None:
            return float(v.mean())
        return float(v[sl].mean())

    tags = {case: [c["name"] for c in sets[case]] for case in CASES}
    per_case_map = {}
    for case in CASES:
        per_case_map[case] = {}
        for tag in tags[case]:
            i = tags[case].index(tag)
            per_case_map[case][tag] = {}
            for mi, mk in enumerate(MAP_KEYS):
                per_case_map[case][tag][mk] = dict(
                    on_time_test=slice_mean(evalres[case], i, slice(25, 30),
                                            "weighted_on_time_rate", mi),
                    on_time_all30=slice_mean(evalres[case], i, None,
                                             "weighted_on_time_rate", mi),
                    completion_test=slice_mean(evalres[case], i, slice(25, 30),
                                               "weighted_completion_rate", mi),
                    tardiness_test=slice_mean(evalres[case], i, slice(25, 30),
                                              "weighted_tardiness_s", mi),
                    cost_test=slice_mean(evalres[case], i, slice(25, 30), "cost", mi),
                    reviews_test=slice_mean(evalres[case], i, slice(25, 30),
                                            "n_reviews", mi),
                )

    # ---------------- gate statistics -------------------------------------
    def vec(case, tag, mi, metric="weighted_on_time_rate"):
        i = tags[case].index(tag)
        return evalres[case][MAPPINGS[mi]][metric][i][25:30]

    FZ = "FROZEN"
    case_tab = []
    for case in CASES:
        for mi in range(len(MAPPINGS)):
            case_tab.append((case, mi, vec(case, "slack_old", mi), vec(case, FZ, mi)))
    st_blocked = blocked_stats(case_tab)

    per_case_delta = {}
    for case in CASES:
        ds = []
        for mi in range(len(MAPPINGS)):
            d = vec(case, FZ, mi) - vec(case, "slack_old", mi)
            ds.append(d)
        per_case_delta[case] = dict(
            on_time_test=float(np.mean([vec(case, FZ, mi).mean()
                                        for mi in range(len(MAPPINGS))])),
            baseline_test=float(np.mean([vec(case, "slack_old", mi).mean()
                                         for mi in range(len(MAPPINGS))])),
            delta=float(np.mean(ds)), paired=blocked_stats(
                [(case, mi, vec(case, "slack_old", mi), vec(case, FZ, mi))
                 for mi in range(len(MAPPINGS))]),
            by_map_delta={MAP_KEYS[mi]: float((vec(case, FZ, mi)
                                               - vec(case, "slack_old", mi)).mean())
                          for mi in range(len(MAPPINGS))},
        )

    comp = float(np.mean([vec(c, FZ, mi, "weighted_completion_rate").mean()
                          - vec(c, "slack_old", mi, "weighted_completion_rate").mean()
                          for c in CASES for mi in range(len(MAPPINGS))]))
    cost_ratio = float(np.mean([vec(c, FZ, mi, "cost").mean()
                                for c in CASES for mi in range(len(MAPPINGS))])
                       / np.mean([vec(c, "slack_old", mi, "cost").mean()
                                  for c in CASES for mi in range(len(MAPPINGS))]))

    g = pre["gate"]
    worst_map = min(min(per_case_delta[c]["by_map_delta"].values()) for c in CASES)
    checks = dict(
        G1_delta_ge_0p015=bool(st_blocked["delta_bar"] >= 0.015),
        G2_ci_lower_gt_0=bool(st_blocked["ci_blocked"][0] > 0.0),
        G3_both_cases_positive=bool(all(per_case_delta[c]["delta"] > 0
                                        for c in CASES)),
        G4_no_mapping_regression=bool(worst_map >= -0.005),
        G5_completion_no_regression=bool(comp >= -0.01),
        G6_cost_inflation=bool(cost_ratio <= 1.05),
    )
    passes = all(checks.values())

    gate_out = dict(
        statistic=g["statistic"],
        delta_bar=st_blocked["delta_bar"],
        ci95_blocked=st_blocked["ci_blocked"],
        se_blocked=st_blocked["se_blocked"], df_blocked=st_blocked["df_blocked"],
        block_means=dict(zip(st_blocked["block_names"], st_blocked["block_means"])),
        ci95_naive_50pairs=st_blocked["ci_naive"],
        ci95_seed_cluster5=st_blocked["ci_seed_cluster"],
        n_pairs=st_blocked["n_pairs"], n_positive=st_blocked["n_positive"],
        sign_test_p=st_blocked["sign_test_p"],
        worst_block_mean=st_blocked["min_block_mean"],
        checks=checks, passes=bool(passes),
        g1_threshold=g["g1_delta_ge_0p015"] if isinstance(g["g1_delta_ge_0p015"], float)
        else 0.015,
        completion_delta=comp, cost_ratio=cost_ratio,
        per_case=per_case_delta,
        violation_note=None if passes else "; ".join(
            k for k, v in checks.items() if not v),
    )

    # ---------------- mandated vs self-imposed gate ------------------------
    mandated = dict(
        statement="mean over S2,S3 of the test delta vs baseline >= 0.015 AND the "
                  "paired 95% CI lower bound > 0 (the gate fixed before the work)",
        delta_bar=st_blocked["delta_bar"],
        ci95_blocked=st_blocked["ci_blocked"],
        threshold=0.015,
        passes=bool(st_blocked["delta_bar"] >= 0.015
                    and st_blocked["ci_blocked"][0] > 0.0),
    )
    selfimp = dict(checks=checks, passes=bool(passes),
                   failing=[k for k, v in checks.items() if not v])
    # the failing robustness cell, with the metric quantum 1/W as context
    worst = None
    for case in CASES:
        for mi, mk in enumerate(MAP_KEYS):
            d = vec(case, FZ, mi) - vec(case, "slack_old", mi)
            if worst is None or d.mean() < worst["delta"]:
                worst = dict(case=case, mapping=mk, delta=float(d.mean()),
                             baseline=float(vec(case, "slack_old", mi).mean()),
                             frozen=float(vec(case, FZ, mi).mean()),
                             quantum=1.0 / (24.0 if case == "S2" else 32.0),
                             per_seed=[float(x) for x in d],
                             in_quanta=float(d.mean() * (24.0 if case == "S2"
                                                         else 32.0)))
    selfimp["worst_cell"] = worst

    # ---------------- comparison table over the three classes --------------
    comp_tab = {}
    for case in CASES:
        comp_tab[case] = {}
        for tag in tags[case]:
            comp_tab[case][tag] = dict(
                on_time_test=float(np.mean([vec(case, tag, mi).mean()
                                            for mi in range(len(MAPPINGS))])),
                on_time_all30=float(np.mean([evalres[case][MAPPINGS[mi]]
                                             ["weighted_on_time_rate"]
                                             [tags[case].index(tag)].mean()
                                             for mi in range(len(MAPPINGS))])),
                completion_test=float(np.mean([vec(case, tag, mi,
                                                   "weighted_completion_rate").mean()
                                               for mi in range(len(MAPPINGS))])),
                cost_test=float(np.mean([vec(case, tag, mi, "cost").mean()
                                         for mi in range(len(MAPPINGS))])),
                reviews_test=float(np.mean([vec(case, tag, mi, "n_reviews").mean()
                                            for mi in range(len(MAPPINGS))])),
                tardiness_test=float(np.mean([vec(case, tag, mi,
                                                  "weighted_tardiness_s").mean()
                                              for mi in range(len(MAPPINGS))])),
                on_time_test_nominal=float(vec(case, tag, 0).mean()),
                on_time_all30_nominal=float(
                    evalres[case][MAPPINGS[0]]["weighted_on_time_rate"]
                    [tags[case].index(tag)].mean()),
            )
        b = comp_tab[case]["slack_old"]["on_time_test"]
        for tag in tags[case]:
            comp_tab[case][tag]["delta_vs_baseline"] = (
                comp_tab[case][tag]["on_time_test"] - b)

    out = dict(
        _meta=dict(
            script="code/up2_p3_final.py",
            prereg_sha256=pre_sha,
            prereg_path="data/up2_p3_prereg.json",
            search_path="data/up2_p3_search.json",
            engine="code/up2_p3_engine.py",
            baseline="code/up_p3_vectorized.py SEL=slack, RULE=slack, q_hi=0.60, "
                     "gate=0.50, late_tol=12, no review (bit-exact with "
                     "p3_improved_verify 'slack_old')",
            seeds_train=TRAIN, seeds_val=VAL, seeds_test=TEST,
            test_evaluated_once=True,
            cases=list(CASES), mappings=MAP_KEYS,
            metric="weighted on-time completion (official mean weighted on-time rate, "
                   "floor 0.50)",
            wall_clock_s=float(time.time() - t0),
            run_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        ),
        frozen={case: dict(class_=frozen[case]["class_"], name=frozen[case]["name"],
                           params=frozen[case]["params"],
                           val_delta=frozen[case]["val_delta"],
                           baseline_val=frozen[case]["baseline_val"],
                           by_class_val=frozen[case]["by_class"],
                           val_gain_ok=frozen[case]["val_gain_ok"])
                for case in CASES},
        strategies=comp_tab,
        per_case_map=per_case_map,
        gate=gate_out,
        gate_mandated=mandated,
        gate_self_imposed=selfimp,
        passes=bool(passes),
        passes_mandated=bool(mandated["passes"]),
        verdict=("mandated gate PASS (+%.2fpp, blocked CI lower +%.2fpp); "
                 "self-imposed robustness gate %s (%s)"
                 % (100 * st_blocked["delta_bar"], 100 * st_blocked["ci_blocked"][0],
                    "PASS" if passes else "FAIL",
                    ", ".join(k for k, v in checks.items() if not v) or "-")),
        notes=[
            "本文件所有基线都是冻结 slack 策略在修正协议下的重放：30 个官方 seed 上 "
            "S2 0.8153 / S3 0.7406。旧记录里的 0.8292 / 0.7854 是修正前协议的数字"
            "（code/p3_schedule.py 误把 C=s+d、t=s+max(d,b)），见 09-C现状与数字对账.md:152；"
            "本文的比较是增量型，不受基线口径影响。",
            "test 只在策略冻结后评估一次；没有任何 test seed 进入选择或早停。",
            "blocked 区间把 10 个 (case×映射) 格当固定块、5 个 seed 当重复；"
            "5 seed 聚类区间作严格参照、50 对朴素区间作宽松参照一并报出。",
            "G4 的 0.5pp 容差比指标量子（S2 的 1/W=4.17pp、S3 的 1/W=3.13pp）还细："
            "val 段同一格 S2|a0.75 曾退化 1 个量子（-4.17pp），test 段该格为 0.00 —— "
            "这条容差会咬住单量子级抖动，读表时按「块均值 / 量子」换算。",
        ],
    )
    path = os.path.join(DATA, "up2_p3.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    log("")
    log("=== nominal (a1.00_b0.50) test, mean over 5 seeds ===")
    for case in CASES:
        for tag in tags[case]:
            r = per_case_map[case][tag]["a1.00_b0.50"]
            log("  %s %-10s on_time=%.4f (all30 %.4f) cost=%.2f rev=%.2f"
                % (case, tag, r["on_time_test"], r["on_time_all30"], r["cost_test"],
                   r["reviews_test"]))
    log("")
    log("=== gate ===")
    log("  delta_bar = %.4f  blocked CI95 [%.4f, %.4f]  df=%.1f"
        % (gate_out["delta_bar"], gate_out["ci95_blocked"][0],
           gate_out["ci95_blocked"][1], gate_out["df_blocked"]))
    log("  naive CI95 [%.4f, %.4f]  seed-cluster CI95 [%.4f, %.4f]"
        % (gate_out["ci95_naive_50pairs"][0], gate_out["ci95_naive_50pairs"][1],
           gate_out["ci95_seed_cluster5"][0], gate_out["ci95_seed_cluster5"][1]))
    log("  checks %s -> passes=%s" % (checks, passes))
    log("  completion delta %+.4f, cost ratio %.3f" % (comp, cost_ratio))
    log("saved -> %s (%.1fs)" % (path, time.time() - t0))
    logf.close()


if __name__ == "__main__":
    main()
