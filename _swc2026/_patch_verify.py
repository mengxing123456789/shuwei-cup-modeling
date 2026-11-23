#!/usr/bin/env python
"""Insert v2 experiment bindings into code/verify_numbers.py (idempotent)."""
from pathlib import Path

P = Path(r"E:\数学建模\_swc2026\SWC2026_C_ALT_BACKUP\code\verify_numbers.py")
text = P.read_text(encoding="utf-8")
MARK = "    # ---------------- ranges ----------------"
assert text.count(MARK) == 1, text.count(MARK)
assert "p2train.ridge.0.2" not in text, "already patched"

BLOCK = r'''
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
        add("p2conf.prose.width_lo", H["6"]["conformal"]["box_width_cm"], "12.18")
        add("p2conf.prose.width_hi", H["30"]["conformal"]["box_width_cm"], "29.42")
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

'''

text = text.replace(MARK, BLOCK + MARK)
P.write_bytes(text.encode("utf-8"))
print("patched", P.stat().st_size, "bytes")
