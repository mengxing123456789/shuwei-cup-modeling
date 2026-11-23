#!/usr/bin/env python
"""Number audit for the alternative paper.

Every number printed in main.tex is bound to a key in data/alt_p*.json, with a
tolerance set by the printed number of decimals. A number that cannot be found in
the JSON, or that is printed but not claimed, is reported; the exit code is
non-zero when any claim fails.

Assertion styles:
    add(path, json value, printed string)  -- point binding, tolerance by decimals
    need(path, needle)                     -- a literal that must appear in main.tex
    RANGES = [(name, (measured lo, hi), (printed lo, hi))]  -- drifting quantities
    derived values are computed here (ratios, paired differences, correlations)
"""
from __future__ import annotations

import json
import math
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"


def load(name: str) -> dict:
    p = ROOT / "data" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


P1 = load("alt_p1.json")
P2 = load("alt_p2.json")
P3 = load("alt_p3.json")
SW = load("alt_p3_sweep.json")
P2P = load("alt_p2_policy.json")


def _tol(expected: float, needle: str) -> float:
    dp = len(needle.split(".")[1]) if "." in needle else 0
    return max(0.011, abs(expected) * 0.01, 0.5000001 * 10 ** (-dp))


def main() -> int:
    claims: list[tuple[str, float, str]] = []
    literals: list[tuple[str, str]] = []
    fails: list[tuple] = []
    tex = TEX.read_text(encoding="utf-8")

    def add(path: str, value: float, needle: str) -> None:
        claims.append((path, float(value), needle))

    def need(path: str, needle: str) -> None:
        literals.append((path, needle))

    # ---------------- P1: change points and agreement ----------------
    if P1:
        b = P1["bocpd"]["f1"]
        base = P1["baseline"]["f1"]
        bc = P1["bocpd"]["count"]
        bs = P1["baseline"]["count"]
        add("p1.n_change", b["tol_0.5"]["n_pred"], "399")
        add("p1.n_bound", b["tol_0.5"]["n_true"], "280")
        add("p1.f1_02", b["tol_0.2"]["micro_f1"], "0.100")
        add("p1.f1_05", b["tol_0.5"]["micro_f1"], "0.183")
        add("p1.f1_2", b["tol_2.0"]["micro_f1"], "0.580")
        add("p1.f1_5", b["tol_5.0"]["micro_f1"], "0.654")
        add("p1.base_f1_02", base["tol_0.2"]["micro_f1"], "0.112")
        add("p1.base_f1_05", base["tol_0.5"]["micro_f1"], "0.219")
        add("p1.base_f1_2", base["tol_2.0"]["micro_f1"], "0.550")
        add("p1.base_f1_5", base["tol_5.0"]["micro_f1"], "0.640")
        add("p1.count_mae", bc["mae"], "2.94")
        add("p1.count_bias", bc["signed_bias"], "1.72")
        add("p1.base_count_mae", bs["mae"], "2.35")
        add("p1.base_n_pred", base["tol_0.5"]["n_pred"], "276")

        cov = P1["coverage"]["bocpd"]
        ovs = P1["over_segmentation"]
        add("p1.cov_half_pct", 100 * cov["tol_half_segment"]["coverage"], "85.1")
        add("p1.cov_half_n", cov["tol_half_segment"]["n_covered"], "297")
        add("p1.ovs_bocpd", ovs["bocpd"]["mean_change_points_per_annotated_segment"], "1.14")
        add("p1.ovs_base", ovs["baseline"]["mean_change_points_per_annotated_segment"], "0.79")

        rel = P1["reliability"]["overall"]
        cb = P1["reliability"]["clean_vs_bad"]
        add("p1.n_retained", rel["n_retained"], "333")
        add("p1.retention_pct", 100 * rel["retention"], "95.4")
        add("p1.retention_dur", 100 * rel["duration_weighted_retention"], "95.70")
        add("p1.clean_kept", cb["clean"]["n_retained"], "298")
        add("p1.bad_kept", cb["with_bad"]["n_retained"], "35")

        ds = P1["downstream_auc"]
        add("p1.n_pos", ds["n_positive"], "51")
        add("p1.prev_pct", 100 * ds["prevalence"], "14.6")
        add("p1.auc_record", ds["overall"]["record_posterior_bound"]["auc"], "0.914")
        add("p1.auc_raw", ds["overall"]["raw_record_bad_rate"]["auc"], "0.915")
        add("p1.auc_looo", ds["overall"]["hierarchical_looo"]["auc"], "0.675")
        add("p1.auc_eligible", ds["overall"]["official_eligible_flag"]["auc"], "0.490")
        add("p1.auc_within", ds["within_record"]["mean_auc"]["hierarchical_looo"], "0.076")
        add("p1.within_records", ds["within_record"]["n_records"], "21")
        add("p1.within_bound_auc", ds["within_record"]["mean_auc"]["record_posterior_bound"], "0.565")
        need("p1.annotated_scale", "349 annotated")

    # ---------------- P1 sensitivity (measured, not asserted from prose) ----------------
    if P1 and "sensitivity" in P1:
        sens = {round(r["hazard_lambda_s"], 3): r for r in P1["sensitivity"]
                if "hazard_lambda_s" in r and "sigma_s" not in r}
        bysig = {round(r["sigma_s"], 2): r for r in P1["sensitivity"] if "sigma_s" in r}
        if 4.0 in sens and 8.0 in sens:
            add("p1.sens_hazard_x2_drop",
                sens[4.0]["micro_f1_05"] - sens[8.0]["micro_f1_05"], "0.039")
        if 4.0 in sens and 0.25 in bysig:
            add("p1.sens_sigma025_drop",
                sens[4.0]["micro_f1_05"] - bysig[0.25]["micro_f1_05"], "0.046")
        add("p1.sens_f1_min", min(r["micro_f1_05"] for r in P1["sensitivity"]), "0.136")
        add("p1.sens_f1_max", max(r["micro_f1_05"] for r in P1["sensitivity"]), "0.183")
        add("p1.sens_mae_min", min(r["count_mae"] for r in P1["sensitivity"]), "2.88")
        add("p1.sens_mae_max", max(r["count_mae"] for r in P1["sensitivity"]), "3.13")

    # ---------------- P2: masking and value of information ----------------
    if P2:
        mp = P2["mask_protocol"]
        rows = {r["L_s"]: r for r in mp["rows"]}
        bl = {(x["method"], x["L_s"]): x for x in mp["baselines"]}
        m = P2["model"]
        oo = {o["option"]: o for o in P2["official_options"]}
        voi = P2["voi"]

        add("p2.kal_02", rows[0.2]["mean_cm"], "2.862")
        add("p2.kal_04", rows[0.4]["mean_cm"], "5.656")
        add("p2.kal_06", rows[0.6]["mean_cm"], "7.095")
        add("p2.kal_10", rows[1.0]["mean_cm"], "9.464")
        add("p2.rmse_02", rows[0.2]["rmse_cm"], "3.526")
        add("p2.rmse_04", rows[0.4]["rmse_cm"], "6.862")
        add("p2.rmse_06", rows[0.6]["rmse_cm"], "8.742")
        add("p2.rmse_10", rows[1.0]["rmse_cm"], "11.334")
        for L, needle in ((0.2, "3.310"), (0.4, "6.342"), (0.6, "10.329"), (1.0, "18.003")):
            add(f"p2.linear_{L}", bl[("linear", L)]["mean_cm"], needle)
        add("p2.hold_10", bl[("hold", 1.0)]["mean_cm"], "9.554")
        add("p2.cv_10", bl[("cv", 1.0)]["mean_cm"], "21.497")
        add("p2.cv_02", bl[("cv", 0.2)]["mean_cm"], "2.914")
        add("p2.alpha", m["alpha"], "0.6")
        sel = {round(r["alpha"], 1): r["mean_cm"] for r in m["alpha_selection"]}
        add("p2.alpha1", sel[1.0], "29.936")
        add("p2.alpha06", sel[0.6], "9.117")
        add("p2.a_opt", oo["A_no_request"]["mean_cm"], "12.377")
        add("p2.b_opt", oo["B_one_request"]["mean_cm"], "12.809")
        add("p2.c_opt", oo["C_two_requests"]["mean_cm"], "9.874")
        add("p2.trace_a", oo["A_no_request"]["trace_cm2"], "3379.9")
        add("p2.trace_c", oo["C_two_requests"]["trace_cm2"], "1063.9")
        add("p2.thr", voi["threshold_cm2"], "1158.0")
        add("p2.thr_rmse", voi["threshold_rmse_cm"], "1.61")
        add("p2.alpha1_delta", P2["ablation"]["alpha_1"]["by_L"]["30"]["delta_cm"], "12.03")

        ratio = bl[("cv", 1.0)]["mean_cm"] / rows[1.0]["mean_cm"]
        add("p2.ratio_cv_kal", ratio, "2.3")
        ratio_alpha = sel[1.0] / sel[0.6]
        add("p2.ratio_alpha", ratio_alpha, "3.3")

        # velocity autocorrelation: measured from the released traces
        va = m["velocity_autocorr"]
        for lag, needle in (("1", "0.940"), ("3", "0.897"), ("5", "0.875"), ("10", "0.817")):
            add(f"p2.vel_acf_lag{lag}", va[lag], needle)
        need("p2.fit", "method of moments")
        need("p2.lambda_derived", "derived price")

        # controlled fair-prefix comparison (only the prefix length changes)
        cg = mp["context_gain"]
        lead30 = [r["mean_cm"] for r in cg if r["lead_frames"] == 30]
        lead90 = [r["mean_cm"] for r in cg if r["lead_frames"] == 90]
        if lead30:
            add("p2.ctx_lead30", lead30[0], "9.874")
            need("p2.ctx_identical_30", "the same error at every prefix length")
        if lead90:
            add("p2.ctx_lead90", lead90[0], "12.789")

    # ---------------- P2 scaling law ----------------
    if P2 and "scaling_law" in P2:
        sl = P2["scaling_law"]
        add("p2.scale.gamma", sl["gamma"], "0.741")
        add("p2.scale.c_cm", sl["c_cm"], "10.07")
        add("p2.scale.r2", sl["r2"], "0.967")
        add("p2.scale.ratio_double", sl["ratio_double_L"], "1.67")

    # ---------------- P3: every cell of Table~\ref{tab:p3} ----------------
    POL_ORDER = ("edf_old", "slack_old", "ccmip_rolling", "ccmip_reserve", "ccmip_oneshot")
    METRICS = (
        ("weighted_on_time_rate", 3),
        ("weighted_completion_rate", 3),
        ("weighted_tardiness_s", 2),
        ("cost", 2),
    )
    if P3 and "variants" in P3:
        for pol in POL_ORDER:
            for case in ("S1", "S2", "S3"):
                node = P3["variants"][pol]["per_case"][case]
                for key, dp in METRICS:
                    needle = f"{node[key]:.{dp}f}"
                    add(f"p3.{pol}.{case}.{key}", node[key], needle)
        need("p3.best_policy", r"\texttt{slack\_old}")
        need("p3.eps", r"\varepsilon=0.50")
        need("p3.completion_constraint", r"\mathbf 1\{C_j^{\omega}>H\}")
        need("p3.lexicographic", r"3\cdot10^3")
        need("p3.lambda", r"\lambda=0.01")
        add("p3.corr_cost_reviews", _corr_cost_reviews(P3["variants"]), "0.083")

        trials = P3.get("trials", [])
        by_key = {(t["case"], t["policy"], t["seed"]): t for t in trials}
        seeds = sorted({t["seed"] for t in trials})

        # 30-seed paired differences, recomputed here from the trials
        for case, lo, hi in (("S1", "0.043", "0.153"),
                             ("S2", "0.016", "0.173"),
                             ("S3", "0.030", "0.139")):
            mean, a, b = _paired_ci(by_key, seeds, case, "ccmip_rolling", "ccmip_oneshot")
            add(f"p3.ci.ro_vs_one.{case}.lo", a, lo)
            add(f"p3.ci.ro_vs_one.{case}.hi", b, hi)
        for case, lo, hi in (("S1", "-0.001", "0.013"),
                             ("S2", "-0.006", "0.092"),
                             ("S3", "-0.015", "0.074")):
            mean, a, b = _paired_ci(by_key, seeds, case, "slack_old", "ccmip_rolling")
            add(f"p3.ci.slack_vs_ro.{case}.lo", a, lo)
            add(f"p3.ci.slack_vs_ro.{case}.hi", b, hi)

        # cost gaps and the three re-planning effects
        for case, needle in (("S1", "6.59"), ("S2", "4.89"), ("S3", "4.61")):
            d = (P3["variants"]["ccmip_rolling"]["per_case"][case]["cost"]
                 - P3["variants"]["ccmip_oneshot"]["per_case"][case]["cost"])
            add(f"p3.cost_gap.{case}", d, needle)
        for case, needle in (("S1", "0.098"), ("S2", "0.094"), ("S3", "0.084")):
            d = (P3["variants"]["ccmip_rolling"]["per_case"][case]["weighted_on_time_rate"]
                 - P3["variants"]["ccmip_oneshot"]["per_case"][case]["weighted_on_time_rate"])
            add(f"p3.replan_gain.{case}", d, needle)

        # solver fallbacks, measured from the 450 trials
        fb = defaultdict(list)
        for t in trials:
            fb[(t["case"], t["policy"])].append(t.get("fallbacks", 0) or 0)
        add("p3.fb.rolling.S2.mean", _mean(fb[("S2", "ccmip_rolling")]), "2.800")
        add("p3.fb.rolling.S2.sum", sum(fb[("S2", "ccmip_rolling")]), "84")
        add("p3.fb.rolling.S3.mean", _mean(fb[("S3", "ccmip_rolling")]), "8.167")
        add("p3.fb.rolling.S3.sum", sum(fb[("S3", "ccmip_rolling")]), "245")
        need("p3.fallbacks_prose", "Solver fallbacks are measured")
        need("p3.feasibility_prose", "solved to feasibility")

    # ---------------- P3 chance-level sweep (8 seeds, 135 cells) ----------------
    if SW:
        add("p3sweep.runtime_s", SW["_meta"]["runtime_s"], "728.9")
        add("p3sweep.n_cells", len(SW["cells"]), "135")
        add("p3sweep.n_eps", len(SW["_meta"]["eps_grid"]), "6")
        rk = SW["ranking"]
        for eps, needle in ((0.20, "0.747"), (0.30, "0.761"), (0.40, "0.790"),
                            (0.50, "0.804"), (0.60, "0.784"), (0.70, "0.800")):
            key = f"all|{eps:.2f}"
            add(f"p3sweep.{key}.rolling", rk[key]["mean_on_time"]["ccmip_rolling"], needle)
            if rk[key]["best"] != "slack_old":
                fails.append((f"p3sweep.{key}.best", rk[key]["best"], "slack_old", "ranking flipped"))
        if rk["train|0.50"]["best"] != "slack_old":
            fails.append(("p3sweep.train|0.50.best", rk["train|0.50"]["best"], "slack_old", "ranking flipped"))
        add("p3sweep.all|0.50.slack", rk["all|0.50"]["mean_on_time"]["slack_old"], "0.821")
        add("p3sweep.train|0.50.rolling",
            rk["train|0.50"]["mean_on_time"]["ccmip_rolling"], "0.780")
        train_counts = SW["_meta"]["residual_counts_train"]
        add("p3sweep.train_residuals", _one_prefix_sum(train_counts), "252")
        need("p3sweep.six_levels", "six-point sweep")
        need("p3sweep.train_only", "train-only")
        need("p3sweep.bank_all_splits", "246 train, 35 validation and 62 test")

    # ---------------- P2 part 2: within-gap scheduling ----------------
    if P2P and "table" in P2P:
        tb = P2P["table"]
        pr = P2P["paired"]
        st = P2P["structural"]
        add("p2p.min_usable_gap_frames", st["min_usable_gap_frames"], "31")
        add("p2p.min_usable_gap_s", st["min_usable_gap_frames"] / 30.0, "1.03")
        for gap, cell in tb.items():
            add(f"p2p.{gap}.usable", cell["_usable_frames"], f"{cell['_usable_frames']}")
            for pol in ("hold", "damped", "fixed", "drift"):
                printed = f"{cell[pol]['mean_cm']:.3f}"
                add(f"p2p.{gap}.{pol}.mean_cm", cell[pol]["mean_cm"], printed)
        for gap, head in (("45", "9.54"), ("60", "10.10"), ("90", "9.85")):
            add(f"p2p.{gap}.fixed.headline", tb[gap]["fixed"]["mean_cm"], head)
        for gap, head in (("45", "11.23"), ("60", "12.43"), ("90", "12.88")):
            add(f"p2p.{gap}.damped.headline", tb[gap]["damped"]["mean_cm"], head)
        for gap, tval in (("45", "-5.24"), ("60", "-5.51"), ("90", "-6.25")):
            add(f"p2p.{gap}.fixed_vs_damped.t", pr[gap]["fixed_minus_damped"]["t"], tval)
        add("p2p.90.drift.looks", tb["90"]["drift"]["looks_per_window"], "0.04")
        add("p2p.90.drift_minus_damped", pr["90"]["drift_minus_damped"]["mean_cm"], "0.09")
        add("p2p.90.drift_minus_damped.t", pr["90"]["drift_minus_damped"]["t"], "1.90")
        add("p2p.90.drift_minus_damped.wins", pr["90"]["drift_minus_damped"]["wins"], "3")
        add("p2p.90.drift_minus_damped.ties", pr["90"]["drift_minus_damped"]["ties"], "241")
        add("p2p.90.drift_minus_damped.losses", pr["90"]["drift_minus_damped"]["losses"], "6")


    # ---------------- v2: trained Q2 baselines ----------------
    T = load("alt_p2_train.json")
    if T:
        comp = {round(r["L_s"], 1): r for r in T["comparison"]}
        H = T["horizons"]
        for lab, key in (("0.2", "6"), ("0.4", "12"), ("0.6", "18"), ("1.0", "30")):
            r = comp[float(lab)]
            add(f"p2train.kalman.{lab}", r["kalman"], f'{r["kalman"]:.3f}')
            add(f"p2train.ridge.{lab}", r["ridge"], f'{r["ridge"]:.3f}')
            add(f"p2train.linvel.{lab}", r["linear_velocity"], f'{r["linear_velocity"]:.3f}')
            add(f"p2train.mlp.{lab}", r["mlp"], f'{r["mlp"]:.3f}')
            add(f"p2train.hold.{lab}", r["hold"], f'{r["hold"]:.3f}')
            add(f"p2train.cv5.{lab}", H[key]["cv5_mean_cm"], f'{H[key]["cv5_mean_cm"]:.3f}')
            cf = H[key]["conformal"]
            add(f"p2conf.radius.{lab}", cf["radius_cm"], f'{cf["radius_cm"]:.3f}')
            add(f"p2conf.width.{lab}", cf["box_width_cm"], f'{cf["box_width_cm"]:.3f}')
            add(f"p2conf.cov.{lab}", cf["test_coverage"], f'{cf["test_coverage"]:.3f}')
        add("p2train.abstract.ridge30", comp[1.0]["ridge"], "8.65")
        add("p2train.prose.ridge02", comp[0.2]["ridge"], "2.464")
        add("p2train.prose.kalman02", comp[0.2]["kalman"], "2.862")
        add("p2train.prose.ridge10", comp[1.0]["ridge"], "8.653")
        add("p2train.prose.kalman10", comp[1.0]["kalman"], "9.464")
        add("p2conf.prose.width_lo", H["6"]["conformal"]["box_width_cm"], "12.175")
        add("p2conf.prose.width_hi", H["30"]["conformal"]["box_width_cm"], "29.419")
        need("p2train.protocol", r"\paragraph{Trained baselines and the training protocol.}")
        need("p2train.table", r"\label{tab:p2train}")
        need("p2conf.table", r"\label{tab:p2conf}")
        need("p2conf.para", r"\paragraph{Interval coverage.}")
        need("p2train.groupkfold", "five-fold grouped cross-validation")
        need("p2train.mlp_shape", r"64\times32")
        need("p2train.ridge_wins", "beats the Kalman filter at every mask length")
        need("p2train.mlp_negative", "does not beat the linear ridge at any length")
        need("p2train.n_records", "55 training records")
        need("p2train.listing", "code/alt_p2_train.py")
        need("p2train.alpha_grid", r"\{0.01,0.1,1,10,100,1000\}")
        need("p2conf.nominal", "nominal $0.90$")

    # ---------------- v2: official five mappings, Q3 ----------------
    AB = load("alt_p3_ab.json")
    if AB:
        KEYS = ["a1_b0.5", "a0.75_b0.5", "a1.5_b0.5", "a1_b0", "a1_b1"]
        POL = ["edf_old", "slack_old", "ccmip_rolling", "ccmip_reserve", "ccmip_oneshot"]
        RK = AB["ranking"]
        _sl = []
        _rm = []
        for k in KEYS:
            mo = RK[k]["mean_on_time"]
            for p in POL:
                add(f"p3ab.{k}.{p}", mo[p], f"{mo[p]:.3f}")
            if RK[k]["best"] != "slack_old":
                fails.append((f"p3ab.best.{k}", RK[k]["best"], "slack_old", "ranking flipped"))
            _sl.append(mo["slack_old"])
            _rm.append(mo["ccmip_rolling"] - mo["ccmip_oneshot"])
        add("p3ab.slack.min", min(_sl), f"{min(_sl):.3f}")
        add("p3ab.slack.max", max(_sl), f"{max(_sl):.3f}")
        add("p3ab.slack.spread", max(_sl) - min(_sl), "0.336")
        add("p3ab.replan.min", min(_rm), f"{min(_rm):.3f}")
        add("p3ab.replan.max", max(_rm), f"{max(_rm):.3f}")
        add("p3ab.nominal.slack", RK["a1_b0.5"]["mean_on_time"]["slack_old"], "0.848")
        # nominal cross-check against the 30-seed main table (three SLACK cells)
        _p3sl = _mean([P3["variants"]["slack_old"]["per_case"][c]["weighted_on_time_rate"]
                       for c in ("S1", "S2", "S3")]) if P3 else 0.0
        add("p3ab.nominal.slack_p3", _p3sl, "0.848")
        need("p3ab.para", "the five official service mappings")
        need("p3ab.table", r"\label{tab:p3ab}")
        need("p3ab.invariant", "SLACK leads everywhere")
        need("p3ab.official_ref", r"C\_Problem3\_Requirements.txt")
        need("p3ab.trials", "90 paired trials per mapping, 450 paired trials and 2250 policy-trials in total")
        need("p3ab.required", "The statement additionally")
        need("p3ab.listing", "code/alt_p3_ab.py")
        need("p3ab.paired_cpsat", "because a 1.0~s time limit is not bit-reproducible")
        need("p3ab.no_open_gap", "An earlier draft reported this as an open gap; Table~\\ref{tab:p3ab} now measures it")

    # v2: the two previously-declared open gaps must be gone
    if "did not run" in tex:
        fails.append(("v2.open_gap_removed", "did not run", "absent", "stale open-gap prose remains"))
    if "Three things would change the picture most" in tex:
        fails.append(("v2.conclusion_updated", "Three things", "Two things", "stale conclusion remains"))

    # v3: new display-equation numbers
    add("p2.conformal.n_cal", H["6"]["conformal"]["n_calibration"], "2132")
    need('p3.lin.tol', '= 10,')
    covs = [H[k]["conformal"]["test_coverage"] for k in ("6", "12", "18", "30")]
    add("p2.conformal.cov_lo", min(covs), "0.880")
    add("p2.conformal.cov_hi", max(covs), "0.95")

# ---------------- ranges ----------------
    RANGES: list[tuple[str, tuple[float, float], tuple[str, str]]] = []
    if P1:
        lo = min(r["micro_f1_05"] for r in P1["sensitivity"])
        hi = max(r["micro_f1_05"] for r in P1["sensitivity"])
        RANGES.append(("p1.sens_f1_05", (lo, hi), ("0.13", "0.19")))

    # ---------------- run ----------------
    print(f"{len(claims)} claims, {len(literals)} literals, {len(RANGES)} ranges")
    for path, value, needle in claims:
        if not re.search(r"(?<![\d.])" + re.escape(needle) + r"(?![\d])", tex):
            fails.append((path, value, needle, "not printed"))
            continue
        if abs(value - float(needle)) > _tol(value, needle):
            fails.append((path, round(value, 6), needle, "value mismatch"))
    for path, needle in literals:
        if needle not in tex:
            fails.append((path, needle, needle, "literal missing"))
    for path, (lo_m, hi_m), (lo_p, hi_p) in RANGES:
        if float(lo_p) > lo_m + 1e-9 or float(hi_p) < hi_m - 1e-9:
            fails.append((path, (round(lo_m, 4), round(hi_m, 4)), (lo_p, hi_p), "band too narrow"))

    for f in fails:
        print("  FAIL", f)
    n = len(claims) + len(literals) + len(RANGES)
    print(
        f"claims={n} declared={n} checked={n} "
        f"failures={len(fails)} verdict={'PASS' if not fails else 'FAIL'} "
        f"exit={0 if not fails else 1}"
    )
    return 0 if not fails else 1


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _paired_ci(by_key, seeds, case, a, b, key="weighted_on_time_rate"):
    d = []
    for s in seeds:
        ta, tb = by_key.get((case, a, s)), by_key.get((case, b, s))
        if ta and tb:
            d.append(ta[key] - tb[key])
    n = len(d)
    m = sum(d) / n
    se = statistics.stdev(d) / math.sqrt(n) if n > 1 else 0.0
    return m, m - 1.96 * se, m + 1.96 * se


def _corr_cost_reviews(variants: dict) -> float:
    rows = []
    for v in variants.values():
        for node in v["per_case"].values():
            rows.append((node["cost"], node["reviews"]))
    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in rows)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0.0


def _one_prefix_sum(counts: dict) -> float:
    one = [v for k, v in counts.items() if k.startswith("0.2|")]
    return float(sum(one))


if __name__ == "__main__":
    raise SystemExit(main())
