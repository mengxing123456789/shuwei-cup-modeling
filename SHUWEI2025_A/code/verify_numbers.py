#!/usr/bin/env python
"""对账：正文里印出来的每个数，都要能回到 data/*.json 里的一个键。

跑法：`python code/verify_numbers.py`，退出码 0 = 全部对得上。

三种断言：add(键名, json 值, 正文里印的字符串)；RANGES 绑会漂的量；
派生量就在下面现算（worse_by、百分比、差值）。

注意：本文件里的 needle 必须与 `main.tex` 印刷形式**逐字**一致，包括 `\\,`
千位分隔符。改正文数字后先跑一遍，FAIL 会指出哪一条还对不上。
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "main.tex"


def _tol(expected: float, needle: str) -> float:
    """容差按**印刷的小数位**定：印 3.1 就容 0.05，印 96.4 就容 0.964。"""
    dp = len(needle.split(".")[1]) if "." in needle else 0
    return max(0.011, abs(expected) * 0.01, 0.5000001 * 10 ** (-dp))


def main() -> int:
    claims: list[tuple[str, float, str]] = []
    fails: list[tuple] = []
    tex = TEX.read_text(encoding="utf-8")

    def add(path: str, value: float, needle: str) -> None:
        claims.append((path, float(value), needle))

    q1 = json.loads((ROOT / "data" / "q1.json").read_text(encoding="utf-8"))
    q2 = json.loads((ROOT / "data" / "q2.json").read_text(encoding="utf-8"))
    q3 = json.loads((ROOT / "data" / "q3.json").read_text(encoding="utf-8"))
    CONV_P = ROOT / "data" / "convention.json"
    CONV = json.loads(CONV_P.read_text(encoding="utf-8")) if CONV_P.exists() else None

    # ---- 系统参数与自然频率（Section 2）----
    add("q1.natural_hz", q1["natural_hz"], "8.0847")
    add("q1.zeta", q1["zeta"], "0.01266")
    add("q1.decay_tau_s", q1["decay_tau_s"], "1.56")
    add("q2.wd_rad_s", q2["wd_hz"] * 2 * math.pi, "50.7939")

    # ---- Question 1 ----
    add("q1.I_off", q1["I_off"], "43.702")
    add("q1.I_on", q1["I_on"], "189.293")
    add("q1.worse_by", q1["worse_by"], "4.33")
    add("q1.I_on_negative_sign", q1["I_on_negative_sign"], "156.901")
    add("q1.I_on_corotating", q1["I_on_corotating"], "342.712")
    add("q1.y_pp_off_mm", q1["y_pp_off_mm"], "20.22")
    add("q1.a_pp_off", q1["a_pp_off"], "49.57")
    add("q1.a_pp_on", q1["a_pp_on"], "77.5")
    add("q1.f_act_max_kN", q1["f_act_max_kN"], "109.86")
    add("q1.f_act_rms_kN", q1["f_act_rms_kN"], "16.82")
    add("q1.f_dist_rms_kN", q1["f_dist_rms_kN"], "5.97")
    add("q1.omega_raw_max", q1["omega_raw_max"], "39.07")
    add("q1.alpha_max", q1["alpha_max"], "2\\,462")

    # ---- Question 2 ----
    add("q2.I_uncontrolled", q2["I_uncontrolled"], "13\\,148.921")
    add("q2.a_pp_uncontrolled", q2["a_pp_uncontrolled"], "362.3")
    add("q2.y_pp_uncontrolled_mm", q2["y_pp_uncontrolled_mm"], "145.2")
    add("q2.A.I", q2["A"]["I"], "71.053")
    add("q2.A.reduction_pct", q2["A"]["reduction_pct"], "99.46")
    add("q2.D.I", q2["D"]["I"], "11.778")
    add("q2.D.reduction_pct", q2["D"]["reduction_pct"], "99.91")
    add("q2.D.omega_max", q2["D"]["omega_max"], "58.2")
    add("q2.D.alpha_max", q2["D"]["alpha_max"], "936.8")
    add("q2.D.f_max_kN", q2["D"]["f_max_kN"], "38.19")
    add("q2.D.a_pp", q2["D"]["a_pp"], "46.6")
    add("q2.D.y_pp_mm", q2["D"]["y_pp_mm"], "17.01")
    add("q2.lines.8.amp", q2["lines"]["8.0"]["amp"] / 1e3, "16.788")
    add("q2.lines.5.amp", q2["lines"]["5.0"]["amp"] / 1e3, "7.760")
    add("q2.lines.3.amp", q2["lines"]["3.0"]["amp"] / 1e3, "3.111")
    add("q2.I_ref_line8", q2["I_ref_line8"], "71.053")
    add("q2.I_D_on_removed_line", q2["I_D_on_removed_line"], "13\\,763.28")
    add("q2.sens.0", next(s["I"] for s in q2["sensitivity"]
                          if abs(s["scale"] - 1.0) < 1e-9 and abs(s["dphi_deg"]) < 1e-9), "11.778")
    add("q2.sens.6p", next(s["I"] for s in q2["sensitivity"]
                           if abs(s["scale"] - 1.0) < 1e-9 and abs(s["dphi_deg"] - 6.0) < 0.6), "128.98")
    add("q2.sens.neg11", next(s["I"] for s in q2["sensitivity"]
                              if abs(s["scale"] - 1.0) < 1e-9 and abs(s["dphi_deg"] + 11.0) < 0.6), "564.12")
    add("q2.win_0.15", next(s["I"] for s in q2["window_sweep"]
                            if abs(s["win_s"] - 0.15) < 1e-6), "60.23")
    add("q2.win_0.20", next(s["I"] for s in q2["window_sweep"]
                            if abs(s["win_s"] - 0.20) < 1e-6), "16.79")
    add("q2.win_0.40", next(s["I"] for s in q2["window_sweep"]
                            if abs(s["win_s"] - 0.40) < 1e-6), "53.00")
    add("q2.win_1.00", next(s["I"] for s in q2["window_sweep"]
                            if abs(s["win_s"] - 1.00) < 1e-6), "479.55")

    # ---- rejected split designs and the eccentric-mass convention ----
    add("q2.F.I", q2["F"]["I"], "12.517")
    add("q2.F.reduction_pct", q2["F"]["reduction_pct"], "99.90")
    add("q2.F.kappa_a_deg", q2["F"]["kappa_a_deg"], "85.21")
    add("q2.G.I", q2["G"]["I"], "2\\,718.336")
    add("q2.G.reduction_pct", q2["G"]["reduction_pct"], "79.33")
    add("q2.N.I", q2["N"]["I"], "253.08")
    if CONV is not None:
        add("conv.ring_2800_Hz", CONV["rows"][0]["wn_hz"], "8.08")
        add("conv.ring_2000_Hz", CONV["rows"][3]["wn_hz"], "9.57")
        add("conv.I2_2c0", CONV["rows"][1]["I_scen2"], "4\\,897.25")
        add("conv.I2_4c0", CONV["rows"][2]["I_scen2"], "1\\,446.99")
        add("conv.I1_2000", CONV["rows"][3]["I_scen1"], "94.237")
        add("conv.I2_2000", CONV["rows"][3]["I_scen2"], "209.650")
        add("conv.replay_A_2000", CONV["replay"]["A"]["M2000"], "29.936")
        add("conv.replay_F_2000", CONV["replay"]["F"]["M2000"], "38.537")
        add("conv.replay_D_2000", CONV["replay"]["D"]["M2000"], "44.365")
        add("conv.replay_D_pct_2000",
            100 * (1 - CONV["replay"]["D"]["M2000"] / CONV["rows"][3]["I_scen2"]), "79.61")

    # ---- the reference-axis table (published convention, reproduced) ----
    ALT_P = ROOT / "data" / "q1_alt.json"
    if ALT_P.exists():
        alt = json.loads(ALT_P.read_text(encoding="utf-8"))
        add("alt.ours.Q1_on_sin", alt["ours_2800_3600"]["Q1_on_sin"], "30.517")
        add("alt.ours.Q1_pct_sin", alt["ours_2800_3600"]["Q1_pct_sin"], "30.2")
        add("alt.pub3600.Q1_off", alt["theirs_2000_3600"]["Q1_off"], "94.237")
        add("alt.pub3600.Q1_on_sin", alt["theirs_2000_3600"]["Q1_on_sin"], "56.843")
        add("alt.pub3600.Q1_pct_sin", alt["theirs_2000_3600"]["Q1_pct_sin"], "39.7")
        add("alt.pub3500.Q1_off", alt["theirs_2000_3500"]["Q1_off"], "95.480")
        add("alt.pub3500.Q1_on_sin", alt["theirs_2000_3500"]["Q1_on_sin"], "57.910")
        add("alt.pub3500.Q1_pct_sin", alt["theirs_2000_3500"]["Q1_pct_sin"], "39.4")
        add("alt.pub3500.Q2_off", alt["theirs_2000_3500"]["Q2_off"], "210.756")

    # ---- Question 3 ----
    add("q3.best_mu", next(m["mu"] for m in q3["mu"]
                           if abs(m["I_steady"] - q3["Q3"]["I_steady"]) < 1e-6), "0.2")
    add("q3.Q3.I_steady", q3["Q3"]["I_steady"], "2\\,418.9")
    add("q3.Q3.I_full", q3["Q3"]["I_full"], "2\\,359.9")
    add("q3.Q3.reduction_pct_steady", q3["Q3"]["reduction_pct_steady"], "81.6")
    add("q3.Q3.f_max_kN", q3["Q3"]["f_max_kN"], "21.27")
    add("q3.Q3.y_pp_mm", q3["Q3"]["y_pp_mm"], "94.0")
    add("q3.Q3.a_pp", q3["Q3"]["a_pp"], "237.1")
    add("q3.mu_0.10", q3["mu"][0]["I_steady"], "2\\,802.1")
    add("q3.mu_0.80", q3["mu"][-1]["I_steady"], "130\\,234.1")
    add("q3.param.k_plus", q3["param_error"][0]["I_steady"], "458.6")
    add("q3.param.c_minus", next(p["I_steady"] for p in q3["param_error"]
                                 if p["case"].startswith("c-")), "13\\,601")
    add("q3.noise_10", next(p["I_steady"] for p in q3["noise"]
                            if abs(p["sigma"] - 10.0) < 1e-9), "2\\,533.3")

    # ---- transport delay of the command (Section 7.2) ----
    DLY_P = ROOT / "data" / "q3_delay.json"
    if DLY_P.exists():
        dly = json.loads(DLY_P.read_text(encoding="utf-8"))
        rows = {r["delay_ms"]: r["I"] for r in dly["rows"]}
        add("delay.10ms", rows[10], "3\\,323.5")
        add("delay.20ms", rows[20], "12\\,296.5")
        add("delay.30ms", rows[30], "24\\,704.8")

    # ---- model verification (Section 2.5) ----
    VER_P = ROOT / "data" / "verify.json"
    if VER_P.exists():
        ver = json.loads(VER_P.read_text(encoding="utf-8"))
        add("verify.decay.rate_coarse", ver["decay"]["rate_coarse"], "0.6413")
        add("verify.decay.rate_analytic", ver["decay"]["rate_analytic"], "0.6429")
        add("verify.transfer.amp_meas", ver["transfer"]["amp_meas"], "10.47")
        add("verify.transfer.amp_th", ver["transfer"]["amp_th"], "10.73")
        add("verify.transfer.phase_meas", ver["transfer"]["phase_meas"], "131.99")
        add("verify.transfer.phase_th", ver["transfer"]["phase_th"], "129.78")
        add("verify.transfer.amp_err_pct", -ver["transfer"]["amp_err_pct"], "2.5")
        add("verify.transfer.phase_err_deg", ver["transfer"]["phase_err_deg"], "2.2")

    # ---- the trained forecaster (Section 6) ----
    LEAD_P = ROOT / "data" / "lead.json"
    if LEAD_P.exists():
        lead = json.loads(LEAD_P.read_text(encoding="utf-8"))
        add("lead.corpus.n", lead["corpus"]["n"], "208")
        add("lead.corpus.train", lead["corpus"]["train"], "160")
        add("lead.corpus.val", lead["corpus"]["val"], "24")
        add("lead.history.best_epoch", lead["history"]["best_epoch"], "59")
        add("lead.history.final_val", lead["history"]["val"][-1], "0.202")
        add("lead.phase.mlp_median", lead["phase_error"]["mlp_median_deg"], "3.39")
        add("lead.phase.mlp_p95", lead["phase_error"]["mlp_p95_deg"], "12.52")
        add("lead.phase.linear_median", lead["phase_error"]["linear_median_deg"], "13.36")
        add("lead.phase.off_causal", lead["phase_error"]["official_causal_median_deg"], "11.29")
        add("lead.phase.off_learned", lead["phase_error"]["official_learned_median_deg"], "1.83")
        add("lead.phase.off_l3", lead["phase_error"]["official_l3_median_deg"], "7.22")
        add("lead.L2.I", lead["L2"]["I"], "9.211")
        add("lead.L2.reduction_pct", lead["L2"]["reduction_pct"], "99.93")
        add("lead.L2.f_max_kN", lead["L2"]["f_max_kN"], "23.90")
        add("lead.L2.omega_max", lead["L2"]["omega_max"], "65.85")
        add("lead.L2.alpha_max", lead["L2"]["alpha_max"], "2\\,129.9")
        for k, needle in (("0", "18.172"), ("6", "21\\,500.9"), ("9", "10.008"),
                          ("12", "9.211"), ("15", "7.561"), ("18", "15.281")):
            add(f"lead.sweep.{k}", lead["lead_sweep"][k]["I"], needle)
        add("lead.L3.iter1", lead["L3"]["I_by_iteration"]["1"], "3\\,694.2")
        add("lead.L3.iter2", lead["L3"]["I_by_iteration"]["2"], "13\\,037.8")
        add("lead.L3.iter3", lead["L3"]["I_by_iteration"]["3"], "12\\,882.4")
        add("lead.L3.dagger1", lead["L3"]["dagger"]["1"]["I"], "25.423")
        add("lead.L3.dagger1_f", lead["L3"]["dagger"]["1"]["f_max_kN"], "18.99")
        for k, needle in (("2", "64.393"), ("3", "82.822"), ("4", "161.872")):
            add(f"lead.L3.dagger{k}", lead["L3"]["dagger"][k]["I"], needle)
        for c, needle in (("nominal", "25.423"), ("k+10%", "1\\,527.8"), ("k-10%", "2\\,731.1"),
                          ("c+50%", "565.4"), ("c-50%", "9\\,964.7"), ("M+10%", "2\\,903.4"),
                          ("M-10%", "1\\,670.0")):
            add(f"lead.L3.rob.{c}", lead["L3"]["robustness"][c]["I"], needle)
        for c, needle in (("0.5", "25.44"), ("2.0", "25.69"), ("5.0", "27.00")):
            add(f"lead.L3.noise{c}", lead["L3"]["robustness"][f"noise{c}"]["I"], needle)
        for c, needle in (("nominal", "108.97"), ("k+10%", "7\\,988.1"), ("k-10%", "1\\,714.3"),
                          ("c+50%", "43.68"), ("c-50%", "1\\,345.2"), ("M+10%", "1\\,916.7"),
                          ("M-10%", "5\\,442.0")):
            add(f"lead.hybrid.{c}", lead["L3"]["hybrid"][c]["I"], needle)

    RANGES: list[tuple[str, tuple[float, float], tuple[str, str]]] = [
        ("q2.window_sweep.band",
         (min(s["I"] for s in q2["window_sweep"]), max(s["I"] for s in q2["window_sweep"])),
         ("11.7", "480")),
        ("q3.grid.band",
         (min(min(r["I"]) for r in q3["grid"]["rows"]),
          max(max(r["I"]) for r in q3["grid"]["rows"])),
         ("2124", "39292")),
        ("q3.param_error.band",
         (min(p["I_steady"] for p in q3["param_error"]),
          max(p["I_steady"] for p in q3["param_error"])),
         ("456", "13601")),
    ]

    print(f"{len(claims)} claims, {len(RANGES)} ranges")
    for path, value, needle in claims:
        printed = re.search(r"(?<![\d.])" + re.escape(needle) + r"(?![\d])", tex)
        if not printed:
            fails.append((path, value, needle, "not printed"))
            continue
        shown = float(printed.group(0).replace("\\\\", "").replace("\\,", "").replace("\\", ""))
        if abs(shown - value) > _tol(value, needle):
            fails.append((path, value, needle, f"printed {shown} differs by {abs(shown-value):.3f}"))
    for path, (lo_m, hi_m), (lo_p, hi_p) in RANGES:
        if float(lo_p) > lo_m + 1e-9 or float(hi_p) < hi_m - 1e-9:
            fails.append((path, (lo_m, hi_m), (lo_p, hi_p), "printed band too narrow"))
    for f in fails:
        print("  FAIL", f)
    print(f"{len(claims) - len([1 for f in fails if f[0] in {c[0] for c in claims}])} of "
          f"{len(claims)} claims match")
    print("PASS" if not fails else "FAIL")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
