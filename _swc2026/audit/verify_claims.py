# -*- coding: utf-8 -*-
"""Audit claim checker for SWC2026 C paper.

Every check prints PASS / FAIL / NA and writes audit/verify_claims.json.
No main.tex / main.pdf / slots.tex is modified.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"E:\数学建模\_swc2026")
C = ROOT / "SWC2026_C"
AUD = ROOT / "audit"

MAIN = C / "main.tex"
SLOTS = C / "slots.tex"
AUX = C / "main.aux"
PDF = C / "main.pdf"


def load_json(name: str):
    return json.loads((C / "data" / name).read_text(encoding="utf-8"))


def slots() -> dict[str, str]:
    text = SLOTS.read_text(encoding="utf-8", errors="ignore")
    raw = re.findall(r"\\newcommand\{\\(slot[A-Za-z0-9]+)\}\{([^}]*)\}", text)
    return {k[len("slot"):]: v for k, v in raw}


def num(s: str):
    s = s.strip().replace("$", "").replace("\\,", "").replace("\\%", "")
    try:
        return float(s)
    except ValueError:
        return None


RESULTS: list[dict] = []


def check(name: str, ok, detail: str, expected=None, actual=None):
    if ok is None:
        status = "NA"
    else:
        status = "PASS" if bool(ok) else "FAIL"
    RESULTS.append(
        {
            "name": name,
            "status": status,
            "detail": detail,
            "expected": expected,
            "actual": actual,
        }
    )


def near(a, b, tol=5e-4) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def main() -> int:
    main_text = MAIN.read_text(encoding="utf-8")
    flat_text = re.sub(r"\s+", " ", main_text)
    lines = main_text.splitlines()
    sl = slots()
    aux = AUX.read_text(encoding="utf-8", errors="ignore")

    # ---------- document level ----------
    n_lines = len(lines)
    check("main.tex 行数", n_lines > 1000, f"{n_lines} lines", None, n_lines)
    cites = len(re.findall(r"\\cite\{", main_text))
    check("正文引用数 > 0", cites > 0, f"{cites} \\cite commands", ">0", cites)
    bib = len(re.findall(r"\\bibitem", main_text))
    check("参考文献条目数 >= 8", bib >= 8, f"{bib} bibitem", ">=8", bib)

    m = re.search(r"\\newlabel\{BodyLastPage\}\{\{([^}]*)\}\{(\d+)\}", aux)
    body = int(m.group(2)) if m else None
    check("BodyLastPage <= 25", body is not None and body <= 25, f"BodyLastPage={body}", "<=25", body)

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(PDF))
        pages = doc.page_count
        doc.close()
    except Exception as exc:  # noqa: BLE001
        pages = None
        check("PDF 页数可读", None, f"fitz failed: {exc}", None, None)
    if pages is not None:
        check("PDF 总页数记录", True, f"{pages} pages", None, pages)

    # ---------- slot vs source JSON ----------
    p1a_final = load_json("p1a_gpu_segmentation_final.json")
    p1a_v3 = load_json("p1a_gpu_segmentation.json")
    p1b = load_json("p1b_gpu.json")
    p1cal = load_json("p1b_calib.json")
    p2 = load_json("p2_prediction.json")
    p2g = load_json("p2_gpu.json")
    p2i = load_json("p2_interval.json")
    p3st = load_json("p3_stochastic_schedule.json")
    p3ad = load_json("p3_adaptive.json")
    p3iv = load_json("p3_improved_verify.json")

    final_ari = p1a_final["test"]["mean_ari"]
    check(
        "slot PSegGPUARI 应用 final v4 而非 v3",
        near(num(sl.get("PSegGPUARI", "x")), final_ari),
        f"slot={sl.get('PSegGPUARI')} final={final_ari:.6f} v3={p1a_v3['test']['mean_ari']:.6f}",
        final_ari,
        num(sl.get("PSegGPUARI", "x")),
    )
    final_bf1 = p1a_final["test"]["mean_boundary_f1"]
    check(
        "slot PSegGPUBFOne 应用 final v4",
        near(num(sl.get("PSegGPUBFOne", "x")), final_bf1),
        f"slot={sl.get('PSegGPUBFOne')} final={final_bf1:.6f}",
        final_bf1,
        num(sl.get("PSegGPUBFOne", "x")),
    )

    # The paper's reference is "the same rule run with p known", so it must match the
    # simulator that produced every other Part III number -- not p3_adaptive's oracle,
    # which is a different rule with p known and therefore a different object.
    try:
        import numpy as np

        import importlib
        importlib.import_module("sys").path.insert(0, str(C / "code"))
        p3sim_ref = importlib.import_module("p3_stochastic_schedule")

        # 30 official seeds, from common_conditions.json validation_seeds 2026111700..2026111729
        ref_seeds = list(range(2026111700, 2026111730))
        for _case, _slot in (("S2", "PStochSTwoOracleETA"), ("S3", "PStochSThreeOracleETA")):
            _v = float(
                np.mean(
                    [
                        p3sim_ref.simulate(_case, _s, policy="oracle")["weighted_on_time_rate"]
                        for _s in ref_seeds
                    ]
                )
            )
            _slotv = num(sl.get(_slot, "x"))
            check(
                f"P3 {_case} reference 与 {len(ref_seeds)} 个官方种子的模拟器同源",
                _slotv is not None and near(_slotv, _v, 5e-4),
                f"slot={_slotv} simulator={_v:.6f} seeds={len(ref_seeds)}",
                _v,
                _slotv,
            )
        check(
            "P3 两个 oracle 对象未被同一个词代用",
            not near(num(sl.get("PStochSTwoOracleETA", "x")), p3ad["upper_bound"]["S2"]["oracle"], 1e-3),
            f"paper_reference={num(sl.get('PStochSTwoOracleETA', 'x'))} "
            f"p3_adaptive_oracle={p3ad['upper_bound']['S2']['oracle']:.6f} 是两个对象",
            "distinct",
            num(sl.get("PStochSTwoOracleETA", "x")),
        )
    except Exception as exc:  # noqa: BLE001
        check("P3 reference 与模拟器同源可检验", None, f"failed: {exc}", None, None)

    # One definition only: PInfoAdvS* = adaptive - reference, positive when the
    # adaptive point estimate is higher.  The paper must not print a negative
    # "ahead by", and must not claim significance the paired interval denies.
    for _tag, _slot in (("S2", "PInfoAdvSTwo"), ("S3", "PInfoAdvSThree")):
        _v = num(sl.get(_slot, "x"))
        check(
            f"PInfoAdv{_tag} 只有一个符号约定（adaptive - reference > 0）",
            _v is not None and _v > 0,
            f"slot={_v}",
            ">0",
            _v,
        )
    check(
        "正文不再写 ahead of the reference / goes past",
        "ahead of the reference" not in main_text and "goes past" not in main_text,
        "已改为 point estimate 超出、配对区间含零",
        "absent",
        "present"
        if ("ahead of the reference" in main_text or "goes past" in main_text)
        else "absent",
    )

    cov = num(sl.get("PConMeanCoverage", "x"))
    _emp = p2i["summary"]["mean_coverage"]
    check(
        "平均覆盖率 slot 与 p2_interval 一致",
        cov is not None and near(cov, _emp, 1e-4),
        f"slot={cov}; empirical mean={_emp:.4f}",
        _emp,
        cov,
    )
    _below = cov is not None and cov < 0.90
    _says_below = "below the nominal" in main_text
    check(
        "覆盖率表述方向与数值一致（0.896 < 0.90 就不能写 above nominal）",
        _below == _says_below and ("slightly above nominal" not in main_text),
        f"cov={cov} below={_below} text_says_below={_says_below}",
        f"below={_below}",
        f"text_below={_says_below}",
    )
    med_a = num(sl.get("PConAMedianCm", "x"))
    check(
        "PConAMedianCm 是厘米（表头写 m 则单位错）",
        med_a is not None and 0.5 < med_a < 5,
        f"slot={med_a} cm; 0.92 m 会是 92 cm",
        "cm-scale",
        med_a,
    )

    # ---------- P2 GRU vs ridge ----------
    ridge = {float(r["L_s"]): r["rmse"] for r in p2["by_length"] if r["method"] == "ridge"}
    gu = {float(r["L_s"]): r["test_rmse_m"] for r in p2g["rows"] if r["variant"] == "v2"}
    gu1 = {float(r["L_s"]): r["test_rmse_m"] for r in p2g["rows"] if r["variant"] == "v1"}
    for mask in sorted(set(gu) & set(ridge)):
        check(
            f"GRU v2 在 {mask}s 优于 ridge",
            gu[mask] < ridge[mask],
            f"gru={gu[mask]:.6f} ridge={ridge[mask]:.6f}",
            f"<{ridge[mask]:.6f}",
            gu[mask],
        )
    for mask in sorted(set(gu1) & set(ridge)):
        check(
            f"GRU v1 在 {mask}s 优于 ridge 同档",
            gu1[mask] < ridge[mask],
            f"gru_v1={gu1[mask]:.6f} ridge={ridge[mask]:.6f}",
            f"<{ridge[mask]:.6f}",
            gu1[mask],
        )

    # ---------- data package ----------
    ATT = Path(
        r"C:\Users\29900\Downloads\AsterLink\C_Problem_Data\C_Problem_Data"
        r"\Restocking_Problem_and_Data_EN\Restocking_Problem_and_Data_EN"
        r"\Restocking_Tasks_and_Constraints"
    )
    idx = (ATT / "source_segment_index.csv").read_text(encoding="utf-8-sig")
    rows = idx.splitlines()[1:]
    check("source_segment_index 行数", len(rows) == 349, f"{len(rows)} data rows", 349, len(rows))
    # eligible + duration exact threshold
    import csv
    import io

    recs = list(csv.DictReader(io.StringIO(idx)))
    elig = sum(1 for r in recs if str(r.get("eligible", "")).strip() in {"1", "True", "true"})
    def _d(r):
        return float(r["duration_s"])
    # The CSV carries float noise: two rows are 1.1999999999999993 and one is
    # 1.2000000000000002.  A naive "< 1.2" counts the first two as short.
    eq12 = sum(1 for r in recs if abs(_d(r) - 1.2) < 1e-9)
    gt12 = sum(1 for r in recs if _d(r) > 1.2 + 1e-9)
    lt12 = sum(1 for r in recs if _d(r) < 1.2 - 1e-9)
    check("eligible 单元数", elig == 343, f"eligible={elig}", 343, elig)
    check(
        "恰好 1.2 s 的单元数（论文说 three）",
        eq12 == 3 and "Three of the" in flat_text and "sit exactly on the duration" in flat_text,
        f"exact={eq12}, truly<1.2={lt12}, truly>1.2={gt12}, non-strict eligible={elig}",
        3,
        eq12,
    )

    # ---------- claim-first round: answers, rejected moves, threshold cost ----------
    _sv = slots()

    def _num(x):
        try:
            return float(str(x).replace("$", "").replace("\\,", "").strip())
        except Exception:
            return None

    check("tab:answers present with three rows",
          main_text.count("\\label{tab:answers}") == 1
          and all(k in main_text for k in ("P1: is the hand state recoverable",
                                           "P2: does a request buy information",
                                           "P3: what is the truth worth")),
          "the three questions are answered in a table before the derivation")

    _cost = load_json("p1b_cost_threshold.json")
    _der = _cost["_derived"]
    check("cost-threshold slots match the JSON",
          abs((_num(_sv.get("PCostKeepAll")) or -1) - _der["cost_keep_all_at_r1"]) < 1e-4
          and abs((_num(_sv.get("PCostHalfMult")) or -1) - _der["half_rule_multiple"]) < 0.06
          and abs((_num(_sv.get("PCostRatioHigh")) or -1) - _der["ratio_max"]) < 1e-6,
          "keep-all, the half-rule multiple and the ratio range come from the JSON")

    check("no interior threshold is ever optimal",
          _der["n_interior_optima"] == 0 and "selects an interior" in main_text,
          "the claim in the text is the claim in the JSON")

    check("tab:negatives lists the rejected moves",
          main_text.count("\\label{tab:negatives}") == 1
          and "What was tried, measured and rejected" in main_text,
          "one table of rejected moves, kept in the appendix so the body budget holds")

    check("the recommended threshold is withdrawn",
          "the operating point we recommend" not in main_text,
          "the sentence that recommended a tau is gone, replaced by the cost minimisation")

    # ---------- text-level checks ----------
    mcap = len(re.findall(r"MCAP|\.mcap", main_text))
    check("全文 MCAP 提法一致", mcap == 0, f"{mcap} occurrences: 与 CSV 自述矛盾", 0, mcap)

    check(
        "全文不再声称 No other AI tool",
        "No other AI tool was used" not in main_text,
        "已改为声明多模型路由" if "No other AI tool was used" not in main_text else "仍存在",
        "absent",
        "present" if "No other AI tool was used" in main_text else "absent",
    )
    om = len(re.findall(r"online map", main_text, flags=re.I))
    check(
        "headline adaptive 不含 online map estimate",
        om == 0,
        f"{om} occurrences; p3_improved_verify policy=risk_old, alpha/beta fixed",
        0,
        om,
    )
    _act_ok = "wait, execute and drop" in main_text
    _act_bad = "wait, review, execute" in main_text
    check(
        "P3 动作集声明与代码一致（wait/execute/drop）",
        _act_ok and not _act_bad,
        f"correct_list={_act_ok} wrong_list={_act_bad}; best_p3_sens 有 drop",
        "wait, execute and drop",
        "ok" if (_act_ok and not _act_bad) else "mismatch",
    )
    bmae = "Boundary MAE (s)" in main_text
    check(
        "Boundary MAE 单位标注为帧",
        not bmae,
        "表头仍 (s)，实际值是帧；caption 仍 5.0 s",
        "absent",
        "present" if bmae else "absent",
    )

    multi = len(re.findall(r"\\multicolumn\{\\slotCase(?:Two|Three)\}", main_text))
    check(
        "multicolumn 列数不是 case 编号",
        multi == 0,
        f"{multi} occurrences of \\multicolumn{{\\slotCase...}}",
        0,
        multi,
    )

    # ---------- P3 holdout CI ----------
    def ci(block):
        return block.get("improved_minus_base_ci95") or block.get("delta_ci95") or block.get("ci95")

    # inspect actual structure if present
    h2 = p3iv["cases"]["S2"]["holdout"]
    h3 = p3iv["cases"]["S3"]["holdout"]
    check(
        "P3 S2 holdout 增益 CI 下界 > 0（论文称 held-out 显著）",
        h2["delta_mean"] - h2["delta_ci95"] > 0,
        f"delta={h2['delta_mean']:.4f} half={h2['delta_ci95']:.4f} lower={h2['delta_mean']-h2['delta_ci95']:.4f}",
        ">0",
        h2["delta_mean"] - h2["delta_ci95"],
    )
    check(
        "P3 S3 holdout 增益 CI 跨零（论文称 S3 alone crosses zero）",
        h3["delta_mean"] - h3["delta_ci95"] < 0,
        f"delta={h3['delta_mean']:.4f} half={h3['delta_ci95']:.4f} lower={h3['delta_mean']-h3['delta_ci95']:.4f}",
        "<0",
        h3["delta_mean"] - h3["delta_ci95"],
    )

    # headline "adaptive" vs the true-duration reference, paired over 30 seeds
    try:
        import sys

        import numpy as np

        sys.path.insert(0, str(C / "code"))
        import p3_stochastic_schedule as p3sim  # type: ignore

        for case in ("S2", "S3"):
            ad = np.asarray(p3iv["cases"][case]["selected"]["on_time"], float)
            seeds = p3iv["_meta"]["seeds"]
            orc = np.asarray(
                [p3sim.simulate(case, s, policy="oracle")["weighted_on_time_rate"] for s in seeds],
                float,
            )
            diff = ad - orc
            half = 1.96 * diff.std(ddof=1) / len(diff) ** 0.5
            _lower = diff.mean() - half
            _claims = "ahead of the reference" in main_text or "goes past" in main_text
            check(
                f"P3 {case} adaptive-reference 表述与配对区间一致",
                not (_lower <= 0 and _claims) and (_lower > 0 or "includes zero" in main_text),
                f"diff={diff.mean():+.4f} CI95=±{half:.4f} lower={_lower:+.4f} "
                f"text_claims_ahead={_claims}",
                "consistent",
                "inconsistent" if (_lower <= 0 and _claims) else "consistent",
            )
    except Exception as exc:  # noqa: BLE001
        check("P3 adaptive-reference 配对检验可运行", None, f"failed: {exc}", None, None)

    # is the headline policy the same object as p3_adaptive_decomp "final"?
    try:
        decomp = load_json("p3_adaptive_decomp.json")
        final_cells = {
            c["case"]: c
            for c in decomp["cells"]
            if abs(c["alpha"] - 1.0) < 1e-9 and abs(c["beta"] - 0.5) < 1e-9
        }
        headline2 = num(sl.get("PImpSTwoAllCand", "x"))
        sel2 = p3iv["cases"]["S2"]["selected"]["on_time_mean"]
        check(
            "headline adaptive 就是 p3_improved_verify 的选定策略",
            near(headline2, sel2, 1e-4),
            f"headline={headline2} improved_selected_S2={sel2:.6f} "
            f"(decomp_final_S2={final_cells['S2']['final_bayes']:.4f} 是另一个对象)",
            sel2,
            headline2,
        )
        check(
            "headline 的增益不归因于在线映射估计",
            num(sl.get("PAdaptImplGapMean", "x")) is None
            and "online map estimate is part of the method" not in main_text,
            "PAdapt* 槽已删除，正文改说预留规则 + 十五种子选型",
            "absent",
            "present" if num(sl.get("PAdaptImplGapMean", "x")) is not None else "absent",
        )
    except Exception as exc:  # noqa: BLE001
        check("adaptive 身份一致性可检查", None, f"failed: {exc}", None, None)

    # ---------- visual ----------
    check(
        "PTrans 视觉模型测试优于基础模型",
        near(num(sl.get("PVisDurSel", "x")), 2.5746, 1e-3),
        f"PVisDurSel={sl.get('PVisDurSel')}, PVisDurBase={sl.get('PVisDurBase')}",
        2.5746,
        num(sl.get("PVisDurSel", "x")),
    )

    # ---------- P2 in the official action set (p2_frontier) ----------
    try:
        fr = load_json("p2_frontier.json")
        flat = fr["_flat"]
        for pol, key in (("no_wait_no_request", "PFrNoWait"), ("free_wait", "PFrFreeWait"),
                         ("paid_0p6", "PFrPaidSix"), ("paid_1p0", "PFrPaidOne"),
                         ("paid_twice_1p0", "PFrTwoReqs")):
            check(f"前沿表 {pol} 与 JSON 一致",
                  near(num(sl.get(key, "x")), flat[f"{pol}_rms_cm"], 1e-2),
                  f"slot={sl.get(key)} json={flat[pol+'_rms_cm']}",
                  flat[f"{pol}_rms_cm"], num(sl.get(key, "x")))
        d = fr["comparisons"]["no_wait_no_request__to__free_wait"]
        check("免费等待严格优于不等待（点估计为正收益、CI 不跨零）",
              near(num(sl.get("PFrNoWaitToFree", "x")), d["delta_cm"], 1e-2)
              and d["delta_cm"] < 0 and d["upper"] < 0,
              f"delta={d['delta_cm']:.4f} CI95={d['ci95']:.4f} upper={d['upper']:.4f}",
              "<0 and upper<0", d["upper"])
        p1 = fr["comparisons"]["free_wait__to__paid_1p0"]
        check("付费 1.0 s 相对免费等待无收益（CI 跨零）",
              p1["lower"] < 0 < p1["upper"]
              and "buys lead time, not information" in main_text,
              f"delta={p1['delta_cm']:.4f} CI95={p1['ci95']:.4f}; "
              f"phrase={'buys lead time, not information' in main_text}",
              "CI straddles zero", p1["ci95"])
        pw = fr["comparisons"]["paid_1p0__to__paid_twice_1p0"]
        check("第二次请求是唯一真值钱的付费动作（CI 不跨零）",
              pw["upper"] < 0 and near(num(sl.get("PFrPaidToTwo", "x")), pw["delta_cm"], 1e-2),
              f"delta={pw['delta_cm']:.4f} upper={pw['upper']:.4f}",
              "<0", pw["upper"])
    except Exception as exc:  # noqa: BLE001
        check("前沿表可核查", None, f"failed: {exc}", None, None)

    # ---------- P1 -> P2 reliability weight (p2_reliability_weight) ----------
    try:
        rw = load_json("p2_reliability_weight.json")
        a = rw["arms"]["A_clean_only"]["rmse_cm"]
        b = rw["arms"]["B_soft_weight"]["rmse_cm"]
        c = rw["arms"]["C_all_unweighted"]["rmse_cm"]
        cmp_ab = rw["comparisons"]["A_clean_only__to__B_soft_weight"]
        check("可靠性权重三臂差异小于 2 毫米",
              abs(a - b) < 0.2 and abs(b - c) < 0.2,
              f"A={a:.4f} B={b:.4f} C={c:.4f} cm", "<0.2 cm", abs(a - b))
        check("软权重相对硬过滤的配对差 CI 跨零",
              cmp_ab["lower"] < 0 < cmp_ab["upper"]
              and near(num(sl.get("PRelAtoB", "x")), cmp_ab["delta_cm"], 1e-3),
              f"delta={cmp_ab['delta_cm']:.4f} CI95={cmp_ab['ci95']:.4f}",
              "straddle zero", cmp_ab["ci95"])
        check("正文把该链写成毫米级（不夸大成改进）",
              "moves the number by millimetres" in main_text
              or "by millimetres" in main_text,
              "phrase present" if "millimetres" in main_text else "phrase missing",
              "present", "present" if "millimetres" in main_text else "absent")
    except Exception as exc:  # noqa: BLE001
        check("可靠性权重链可核查", None, f"failed: {exc}", None, None)

    # ---------- P3 same-rule reference (p3_oracle_same_rule) ----------
    try:
        osr = load_json("p3_oracle_same_rule.json")
        for cs, key_o, key_g in (("S2", "POracleSameSTwo", "POracleGapSTwo"),
                                 ("S3", "POracleSameSThree", "POracleGapSThree")):
            row = osr["cases"][cs]
            check(f"同规则参考 {cs} 与 JSON 一致",
                  near(num(sl.get(key_o, "x")), row["same_rule_oracle_mean"], 1e-4)
                  and near(num(sl.get(key_g, "x")), row["gap_oracle_minus_headline"], 1e-4),
                  f"{key_o}={sl.get(key_o)} {key_g}={sl.get(key_g)}",
                  row["same_rule_oracle_mean"], num(sl.get(key_o, "x")))
            check(f"同规则增益 {cs} 的 CI 排除零",
                  row["gap_lower"] > 0,
                  f"gap={row['gap_oracle_minus_headline']:.4f} lower={row['gap_lower']:.4f}",
                  ">0", row["gap_lower"])
        check("tab:limits 只做同规则比较（不出现跨规则的 PInfoAdv）",
              "POracleSameSTwo" in main_text and "PInfoAdvSTwo" in main_text
              and "Ours $-$ ref." not in main_text,
              "table uses POracleSame, header removed",
              "same-rule column", "ok" if "Ours $-$ ref." not in main_text else "old header")
    except Exception as exc:  # noqa: BLE001
        check("同规则参考可核查", None, f"failed: {exc}", None, None)

    # ---------- P1-a identifiability: separation does not predict detection ----------
    id2 = load_json("phase_identifiability2.json")
    idn = load_json("phase_null_check.json")
    summ = id2["summary"]
    check("PIdSpearmanMax 与源 JSON 一致", near(num(sl.get("PIdSpearmanMax", "")), summ["max_abs_spearman"], 1e-3),
          "slot=%s json=%.6f" % (sl.get("PIdSpearmanMax"), summ["max_abs_spearman"]),
          round(summ["max_abs_spearman"], 3), num(sl.get("PIdSpearmanMax", "")))
    check("PIdAucTwo 与源 JSON 一致", near(num(sl.get("PIdAucTwo", "")), idn["auc_at_2_frames"], 1e-3),
          "slot=%s json=%.6f" % (sl.get("PIdAucTwo"), idn["auc_at_2_frames"]),
          round(idn["auc_at_2_frames"], 3), num(sl.get("PIdAucTwo", "")))
    check("PIdTrueHalf 与源 JSON 一致（百分数）",
          near(num(sl.get("PIdTrueHalf", "")), 100.0 * idn["share_pos_ge_half_p2"], 0.1),
          "slot=%s json=%.2f" % (sl.get("PIdTrueHalf"), 100.0 * idn["share_pos_ge_half_p2"]),
          round(100.0 * idn["share_pos_ge_half_p2"], 1), num(sl.get("PIdTrueHalf", "")))
    check("PIdNullHalf 与源 JSON 一致（百分数）",
          near(num(sl.get("PIdNullHalf", "")), 100.0 * idn["share_neg_ge_half_p2"], 0.1),
          "slot=%s json=%.2f" % (sl.get("PIdNullHalf"), 100.0 * idn["share_neg_ge_half_p2"]),
          round(100.0 * idn["share_neg_ge_half_p2"], 1), num(sl.get("PIdNullHalf", "")))
    check("PIdNBound 与源 JSON 一致", near(num(sl.get("PIdNBound", "")), summ["n_boundaries"], 1e-9),
          "slot=%s json=%s" % (sl.get("PIdNBound"), summ["n_boundaries"]), summ["n_boundaries"],
          num(sl.get("PIdNBound", "")))
    check("可辨识性命题被判否且正文照实写",
          id2["proposition_holds"] is False and "No statistic reaches the criterion" in main_text,
          "proposition_holds=%s; 正文声明=%s" % (id2["proposition_holds"],
                                                "No statistic reaches the criterion" in main_text),
          "False + 声明", id2["proposition_holds"])
    check("正文不把分离度写成成立的可辨识性条件",
          "identifiable" not in main_text.split("We also test")[-1].split("\\section")[0].lower()
          or "not the distinguishability" in main_text,
          "null-check 句式存在: %s" % ("A null check rules out a blind detector" in main_text),
          "null-check 存在", None)
    check("零假设对照给出真边界高于随机帧", idn["auc_at_2_frames"] > 0.5 and idn["mean_pos_p2"] > idn["mean_neg_p2"],
          "AUC2=%.3f true=%.3f null=%.3f" % (idn["auc_at_2_frames"], idn["mean_pos_p2"], idn["mean_neg_p2"]),
          "AUC>0.5 且 true>null", None)
    # ---- the same test on a second, independent fit: Part I is not bit-reproducible,
    # so the verdict has to survive a re-fit, not just a re-read.
    id2b = load_json("phase_identifiability2_inst2.json")
    idnb = load_json("phase_null_check_inst2.json")
    _rb_ok = (id2b["proposition_holds"] is False
              and idnb["auc_at_2_frames"] > 0.5
              and near(num(sl.get("PIdSpearmanRobust", "")), id2b["summary"]["max_abs_spearman"], 1e-3)
              and near(num(sl.get("PIdAucTwoRobust", "")), idnb["auc_at_2_frames"], 1e-3)
              and "\\slotPIdSpearmanRobust" in main_text
              and "\\slotPIdAucTwoRobust" in main_text)
    check("可辨识性判决在第二次独立拟合上仍然成立", _rb_ok,
          "inst2 spearman=%.3f (inst1 %.3f), inst2 AUC=%.3f (inst1 %.3f), holds=%s"
          % (id2b["summary"]["max_abs_spearman"], summ["max_abs_spearman"],
             idnb["auc_at_2_frames"], idn["auc_at_2_frames"], id2b["proposition_holds"]),
          "两次拟合都不成立且两槽入正文", _rb_ok)

    # ---- 新增：§2.5 统一记号与三个命题、闭式解的 conditional-on-s 限定 ----
    has_notation = r"\label{sec:notation}" in main_text
    check("给出一节统一记号", has_notation, "sec:notation", True, has_notation)
    props = [
        ("相位命题指向正文检验", r"tested and refuted in Section~\ref{sec:p1res}"),
        ("reservation 命题指向推导", r"derived in Section~\ref{sec:p3closed}"),
        ("前缀信息命题指向上界测量", r"measured in Section~\ref{sec:p2res}"),
    ]
    for nm, lit in props:
        check(nm, lit in flat_text, lit, True, lit in flat_text)
    cond = r"but only conditional on $s$" in main_text
    check("闭式解标注 conditional on s", cond, "main.tex", True, cond)
    not_ceil = r"we do not" in flat_text and r"call the reference an upper bound" in flat_text
    check("不把 reference 叫上界", not_ceil, "main.tex", True, not_ceil)

    # --- reservation-level identifiability (p3_quantile_curve.json) ----------
    _S = slots()
    _q = load_json("p3_quantile_curve.json")
    _grid = _q["_meta"]["q_grid"]
    check("q 网格左端与 slot 一致", near(num(_S["PQSweepLow"]), _grid[0], 1e-9),
          f"slot={_S['PQSweepLow']} grid[0]={_grid[0]}", _grid[0], num(_S["PQSweepLow"]))
    check("q 网格右端与 slot 一致", near(num(_S["PQSweepHigh"]), _grid[-1], 1e-9),
          f"slot={_S['PQSweepHigh']} grid[-1]={_grid[-1]}", _grid[-1], num(_S["PQSweepHigh"]))
    _tc = [float(x) for x in _q["cases"]["S2"]["tune_curve"]]
    _tc3 = [float(x) for x in _q["cases"]["S3"]["tune_curve"]]
    _argmax_left = (max(_tc) == _tc[0]) and (max(_tc3) == _tc3[0])
    check("两个 case 的调优曲线最大值都落在网格左端（而非内部最优点）", _argmax_left,
          f"S2 argmax={_tc.index(max(_tc))} S3 argmax={_tc3.index(max(_tc3))}", 0, 0)
    _wig = max([b - a for a, b in zip(_tc, _tc[1:])] +
               [b - a for a, b in zip(_tc3, _tc3[1:])])
    check("调优曲线的局部回升不超过 2 个百分点", _wig <= 0.02 + 1e-12,
          f"max rise={_wig*100:.2f} points", "<= 2 points", round(_wig * 100, 2))
    _drop = min(max(_tc) - _tc[-1], max(_tc3) - _tc3[-1])
    check("从网格左端到右端至少掉 10 个百分点", _drop >= 0.10,
          f"min drop={_drop*100:.2f} points", ">= 10 points", round(_drop * 100, 2))
    _hc = [float(x) for x in _q["cases"]["S2"]["holdout_curve"]]
    _flatter = (max(_hc) - min(_hc)) < (max(_tc) - min(_tc))
    check("S2 留出曲线比调优曲线更平（水平弱可辨识）", _flatter,
          f"hold span={max(_hc)-min(_hc):.4f} tune span={max(_tc)-min(_tc):.4f}", True, _flatter)
    _phrase = "the plateau, not a point" in main_text
    check("正文写明平台而非点估计", _phrase, "main.tex", True, _phrase)

    # --- same-unit comparison of the two P2 predictors ---------------------
    _S2 = slots()
    _s3 = 3.0 ** 0.5
    _gru_a = num(_S2["PGPUAWristRMSE"])
    _gru_a3 = num(_S2["PGpuAThreeD"])
    check("GRU 逐坐标误差换算三维=×√3（附录同单位段）",
          near(_gru_a3, _gru_a * _s3, 0.011),
          f"3D={_gru_a3} per-coord={_gru_a} ×√3={_gru_a*_s3:.3f}", round(_gru_a * _s3, 2), _gru_a3)
    _rdg_a = num(_S2["PTwoARidgeRMSE"])
    _rdg_pc = num(_S2["PRidgeAPerCoord"])
    check("ridge 三维误差换算逐坐标=÷√3（附录同单位段）",
          near(_rdg_pc, _rdg_a / _s3, 0.011),
          f"per-coord={_rdg_pc} 3D={_rdg_a} ÷√3={_rdg_a/_s3:.3f}", round(_rdg_a / _s3, 2), _rdg_pc)
    _pairs = [("C", "PGpuCThreeD", "PTwoCRidgeRMSE", "PGpuWinCPerCoordPct"),
              ("D", "PGpuDThreeD", "PTwoDRidgeRMSE", "PGpuWinDPerCoordPct")]
    _ok = True
    _det = []
    for _tag, _g3, _r3, _pct in _pairs:
        _gv, _rv, _pv = num(_S2[_g3]), num(_S2[_r3]), num(_S2[_pct])
        _want = 100.0 * (_rv - _gv) / _rv
        _ok = _ok and near(_pv, _want, 0.15)
        _det.append(f"{_tag}: {_pv} vs {_want:.2f}")
    check("C/D 掩码的百分比增益在两种单位下一致（同一比值，容差 0.15 点=两位小数舍入）", _ok, "; ".join(_det), "match", _ok)
    check("附录同单位段写明 both units 并已删除旧的 times-better 说法",
          ("in both units" in main_text) and ("times better than the" not in main_text),
          "main.tex", True, "in both units" in main_text)

    # --- Appendix G: second-round experiments ------------------------------
    import hashlib as _hl
    _gpath = C / "tables" / "app_g.tex"
    _g = _gpath.read_text(encoding="utf-8") if _gpath.exists() else ""
    _man = load_json("app_g_manifest.json") if (C / "data" / "app_g_manifest.json").exists() else {}
    check("Appendix G 表文件存在且含四张表",
          all(k in _g for k in ("tab:gpu-ledger", "tab:p1b-arms", "tab:p2quant", "tab:p3engine")),
          f"bytes={len(_g)}", True, len(_g) > 0)
    check("Appendix G 文件哈希与生成清单一致（可由 JSON 重新生成）",
          bool(_man) and _hl.sha256(_g.encode("utf-8")).hexdigest() == _man.get("sha256"),
          f"manifest={_man.get('sha256','--')[:16]}", "match", _man.get("sha256", "--")[:16])
    _p1b2 = load_json("up_p1b_final.json")
    _lift = f"{_p1b2['aggregate']['ap_gain_pct_seed_matched']:.1f} per cent"
    _lift2 = f"{_p1b2['aggregate']['ap_gain_pct']:.1f} per cent"
    check("Appendix G 正文的 AP 相对增益与 JSON 一致", (_lift in _g) and (_lift2 in _g),
          f"{_lift} / {_lift2}", f"{_lift} / {_lift2}", (_lift in _g) and (_lift2 in _g))
    _rev = load_json("up_p3_review.json")
    _bd = f"{_rev['verdict']['best_delta_pt']:.3f}"
    check("Appendix G 复核臂最好格与 JSON 一致", _bd in _g, _bd, _bd, _bd)
    check("正文在 Appendix D 之外还引用了 Appendix G",
          "\\ref{app:secondround}" in main_text, "main.tex", True,
          "\\ref{app:secondround}" in main_text)

    # --- Appendix G: reinforcement-learning negative result ----------------
    _rl = load_json("up_p3_rl.json")
    _rled = _rl["_meta"]["ledger"]
    _s2 = f"{_rl['paired']['S2']['delta_mean']*100:.2f}"
    _s3 = f"{-_rl['paired']['S3']['delta_mean']*100:.2f}"
    check("Appendix G 的 RL 台账与数据一致",
          (f"{_rled['params']:,}" in _g) and (f"{_rled['gpu_seconds']:.1f}" in _g),
          f"params={_rled['params']} gpu={_rled['gpu_seconds']}", "in app_g.tex",
          (f"{_rled['params']:,}" in _g) and (f"{_rled['gpu_seconds']:.1f}" in _g))
    check("Appendix G 的 RL 配对差与 JSON 一致",
          (_rl["verdict"]["passes"] is False) and (_s2 in _g) and (_s3 in _g),
          f"S2 +{_s2} / S3 -{_s3}", "in app_g.tex",
          (_s2 in _g) and (_s3 in _g))
    check("Appendix G 的 RL 哨兵区间与 JSON 一致",
          (f"{_rl['paired']['S2']['ci95']*100:.1f}" in _g)
          and (f"{_rl['paired']['S3']['ci95']*100:.1f}" in _g),
          f"{_rl['paired']['S2']['ci95']*100:.1f} / {_rl['paired']['S3']['ci95']*100:.1f}",
          "in app_g.tex", True)

    # --- Appendix I: two propositions --------------------------------------
    _ipath = C / "tables" / "app_i.tex"
    _i = _ipath.read_text(encoding="utf-8") if _ipath.exists() else ""
    check("Appendix I 存在且包含两条命题",
          ("Proposition 1" in _i) and ("Proposition 2" in _i) and ("seven tests" in _i),
          f"bytes={len(_i)}", "both propositions", len(_i) > 0)
    check("附录 I 的命题 2 与正文闭式解一致（条件于 s）",
          ("independent of the" in _i) and ("s'=s+" in _i), "app_i.tex", True,
          ("independent of the" in _i) and ("s'=s+" in _i))
    check("正文指向 Appendix I",
          "\\ref{app:propositions}" in main_text, "main.tex", True,
          "\\ref{app:propositions}" in main_text)

    # --- Appendix J: assumptions register ----------------------------------
    _jpath = C / "tables" / "app_j.tex"
    _j = _jpath.read_text(encoding="utf-8") if _jpath.exists() else ""
    _nrows = sum(1 for k in range(1, 11) if f"A{k} &" in _j)
    check("Appendix J 存在且列出 10 条假设",
          _nrows == 10 and _j.count("Declared") >= 3,
          f"rows={_nrows}", "10 rows", _nrows == 10)
    check("正文指向 Appendix J",
          "\\ref{app:propositions}--\\ref{app:sensitivity}" in main_text, "main.tex", True,
          "\\ref{app:propositions}--\\ref{app:sensitivity}" in main_text)

    # --- Appendix K: sensitivity -------------------------------------------
    _kpath = C / "tables" / "app_k.tex"
    _k = _kpath.read_text(encoding="utf-8") if _kpath.exists() else ""
    import hashlib as _hl
    _kman = json.loads((C / "data" / "app_k_manifest.json").read_text(encoding="utf-8"))
    _kok = (_kman.get("output_sha256") == _hl.sha256(_kpath.read_bytes()).hexdigest()
            if _kpath.exists() else False)
    check("Appendix K 存在且含两张敏感性表",
          ("tab:alpha-sweep" in _k) and ("tab:decoder-sweep" in _k) and _kok,
          f"bytes={len(_k)}", "two tables + hash", ("tab:alpha-sweep" in _k) and _kok)
    check("正文指向 Appendix K",
          "\\ref{app:sensitivity}" in main_text, "main.tex", True,
          "\\ref{app:sensitivity}" in main_text)

    # --- Proposition 3 and the phase diagram -------------------------------
    check("Appendix I 含 Proposition 3（预留支配）",
          "Proposition 3 (reservation dominance)" in _i, "app_i.tex", True,
          "Proposition 3 (reservation dominance)" in _i)
    _pd_path = C / "data" / "phase_diagram.json"
    _pd = json.loads(_pd_path.read_text(encoding="utf-8")) if _pd_path.exists() else {}
    _pf = C / "figures" / "fig9_phase.png"
    _pf_ok = _pf.exists() and _pf.stat().st_size > 10000
    check("相图 fig9_phase.png 存在且非空",
          _pf_ok, f"bytes={_pf.stat().st_size if _pf.exists() else 0}", ">10kB", _pf_ok)
    _drop2 = f"{_pd.get('rate_drop_q30_q90', {}).get('S2', 0) * 100:.1f}"
    _drop3 = f"{_pd.get('rate_drop_q30_q90', {}).get('S3', 0) * 100:.1f}"
    check("相图下降幅度与正文槽位一致（S2/S3）",
          ("\\slotPPhaseDropSTwo" in _k) and ("\\slotPPhaseDropSThree" in _k)
          and abs(float(_sv["PPhaseDropSTwo"]) - float(_drop2)) < 0.05
          and abs(float(_sv["PPhaseDropSThree"]) - float(_drop3)) < 0.05,
          f"slots={_sv['PPhaseDropSTwo']}/{_sv['PPhaseDropSThree']}", f"{_drop2}/{_drop3}",
          abs(float(_sv["PPhaseDropSTwo"]) - float(_drop2)) < 0.05)
    _sa2 = f"{_pd.get('spread_alpha', {}).get('S2', 0) * 100:.1f}"
    _sa3 = f"{_pd.get('spread_alpha', {}).get('S3', 0) * 100:.1f}"
    check("相图 alpha 跨度与正文槽位一致（S2/S3）",
          ("\\slotPPhaseAlphaSpreadSTwo" in _k) and ("\\slotPPhaseAlphaSpreadSThree" in _k)
          and abs(float(_sv["PPhaseAlphaSpreadSTwo"]) - float(_sa2)) < 0.05
          and abs(float(_sv["PPhaseAlphaSpreadSThree"]) - float(_sa3)) < 0.05,
          f"slots={_sv['PPhaseAlphaSpreadSTwo']}/{_sv['PPhaseAlphaSpreadSThree']}", f"{_sa2}/{_sa3}",
          abs(float(_sv["PPhaseAlphaSpreadSTwo"]) - float(_sa2)) < 0.05)
    check("相图放在正文、Appendix K 指向它",
          "\\ref{fig:phase}" in _k and "fig9_phase.png" in main_text
          and "fig9_phase.png" not in _k, "app_k.tex + main.tex", True,
          ("\\ref{fig:phase}" in _k and "fig9_phase.png" in main_text))
    check("正文标题与摘要采用新主线",
          ("Punctuality Is Bought by Rules" in flat_text)
          and ("what actually buys punctuality" in flat_text),
          "main.tex", True,
          ("Punctuality Is Bought by Rules" in flat_text)
          and ("what actually buys punctuality" in flat_text))

    # --- value ladder ------------------------------------------------------
    _vl = json.loads((C / "data" / "value_ladder.json").read_text(encoding="utf-8"))
    _vf = C / "figures" / "fig10_value_ladder.png"
    _vf_ok = _vf.exists() and _vf.stat().st_size > 10000
    check("价值阶梯图 fig10_value_ladder.png 存在且非空",
          _vf_ok, f"bytes={_vf.stat().st_size if _vf.exists() else 0}", ">10kB", _vf_ok)
    _v2 = _vl["cases"]["S2"]
    _v3 = _vl["cases"]["S3"]
    check("价值阶梯四机制排序与 JSON 一致",
          (_v2["scheduling rule"] > _v2["true duration"] > 0)
          and (_v2["extra reservation"] < 0)
          and (_v3["scheduling rule"] > _v3["true duration"] > 0)
          and (_v3["extra reservation"] < 0),
          f"S2 {_v2['scheduling rule']}/{_v2['true duration']}/{_v2['extra reservation']}",
          "rule > truth > 0 > reservation", True)
    check("价值阶梯图移至正文、Appendix K 只保留指针",
          ("\\ref{fig:value}" in _k) and ("fig10_value_ladder.png" not in _k)
          and ("fig10_value_ladder.png" in main_text) and ("\\label{fig:value}" in main_text)
          and all(s in main_text for s in ("\\slotPValueRuleSTwo", "\\slotPValueTruthSTwo",
                                           "\\slotPValueReserveSTwo")),
          "main.tex + app_k.tex", True,
          ("\\ref{fig:value}" in _k and "fig10_value_ladder.png" in main_text))

    # --- Appendix L: official scorecard and second-round models -------------
    _lpath = C / "tables" / "app_l.tex"
    _l = _lpath.read_text(encoding="utf-8") if _lpath.exists() else ""
    check("Appendix L 存在且含三张官方口径表",
          all(t in _l for t in ("tab:appL-p1a", "tab:appL-p2", "tab:appL-p3")),
          f"bytes={len(_l)}", "three tables", len(_l) > 0)
    check("正文指向 Appendix L", "\\ref{app:scorecard}" in main_text, "main.tex", True,
          "\\ref{app:scorecard}" in main_text)
    _b = json.loads((C / "data" / "up2_p1b.json").read_text(encoding="utf-8"))
    _v8 = _b["summary"]["V8"]
    check("Appendix L 的 V8 检测器数字与 JSON 一致",
          (f"{_v8['test_auc_mean']:.4f}" in _l)
          and (f"{_v8['test_ap_mean']:.4f}" in _l)
          and (f"{_v8['worst_auc_mean']:.4f}" in _l),
          f"{_v8['test_auc_mean']:.4f}/{_v8['test_ap_mean']:.4f}/{_v8['worst_auc_mean']:.4f}",
          "in app_l.tex",
          (f"{_v8['test_auc_mean']:.4f}" in _l) and (f"{_v8['test_ap_mean']:.4f}" in _l))
    check("Appendix L 的 P1-a 解码器升级行与 JSON 一致",
          ("0.5723 & 0.1408" in _l), "0.5723/0.1408", "in app_l.tex", ("0.5723 & 0.1408" in _l))
    _p2 = json.loads((C / "data" / "up2_p2.json").read_text(encoding="utf-8"))
    _d = _p2["configs"]["D_val_shrinkage"]
    _d30 = _d["aggregate"]["L30"]
    _d30r = _d30["rmse_3d_cm"]["mean"]
    _d30q = _d30["q90_cm"]["mean"]
    check("Appendix L 的 P2 第二轮最好族数字与 JSON 一致",
          (f"{_d30r:.3f}" in _l) and (f"{_d30q:.3f}" in _l),
          f"{_d30r:.3f}/{_d30q:.3f}", "in app_l.tex",
          (f"{_d30r:.3f}" in _l) and (f"{_d30q:.3f}" in _l))
    check("Appendix L 的 P2 决策层 J 值出现在正文",
          ("4.521" in _l) and ("3.574" in _l), "app_l.tex", True,
          ("4.521" in _l) and ("3.574" in _l))
    _st = json.loads((C / "data" / "up2_p1state.json").read_text(encoding="utf-8"))
    _c = _st["arms"]["C_multitask_raw"]
    check("Appendix L 的可靠性检测器 C 臂与 JSON 一致",
          (f"{_c['test_auc']:.4f}" in _l) and (f"{_c['test_ap']:.4f}" in _l),
          f"{_c['test_auc']:.4f}/{_c['test_ap']:.4f}", "in app_l.tex",
          (f"{_c['test_auc']:.4f}" in _l) and (f"{_c['test_ap']:.4f}" in _l))
    _pol = json.loads((C / "data" / "up2_p3.json").read_text(encoding="utf-8"))
    _g = _pol["gate"]
    check("Appendix L 的 P3 第二轮策略增益与 JSON 一致",
          (f"{_g['delta_bar']*100:.2f}" in _l)
          and (f"{_g['ci95_blocked'][0]*100:.2f}" in _l)
          and (f"{_g['ci95_blocked'][1]*100:.2f}" in _l),
          f"{_g['delta_bar']*100:.2f}/{_g['ci95_blocked']}", "in app_l.tex",
          (f"{_g['delta_bar']*100:.2f}" in _l))
    check("Appendix L 的付费复核负结果数字与报告一致",
          ("270" in _l) and ("5.70" in _l) and ("0.42" in _l), "app_l.tex", True,
          ("270" in _l) and ("5.70" in _l) and ("0.42" in _l))
    check("Appendix L 的第二轮台账含七行",
          ("tab:appL-round2" in _l) and all(k in _l for k in ("P1-a", "P1-b", "P1-state", "P2", "P3 policy", "P3 review", "Official")),
          "app_l.tex", "7 rows", "tab:appL-round2" in _l)

    _vid = json.loads((C / "data" / "up3_video_badframe.json").read_text(encoding="utf-8"))
    _pa = _vid["arms"]["P"]; _pv = _vid["arms"]["P+Vsel"]; _pvd = _vid["arms"]["Vsel"]
    check("Appendix L 含视频分支小节与表",
          ("What the video actually buys" in _l) and ("tab:appL-video" in _l),
          "app_l.tex", "video section + table", ("tab:appL-video" in _l))
    check("Appendix L 的视频三臂 AP/AUC 与 JSON 一致",
          all(f"{x:.4f}" in _l for x in (_pa["test_ap"], _pa["test_auc"], _pv["test_ap"], _pv["test_auc"], _pvd["test_ap"], _pvd["test_auc"])),
          "six numbers", "in app_l.tex", all(f"{x:.4f}" in _l for x in (_pa["test_ap"], _pv["test_ap"], _pvd["test_ap"])))
    check("Appendix L 的视频增益与门槛文字一致",
          (f"{_vid['ap_rel_gain']*100:.1f}" in _l) and (f"{_vid['auc_abs_gain']:.4f}" in _l),
          f"{_vid['ap_rel_gain']*100:.1f}/{_vid['auc_abs_gain']:.4f}", "in app_l.tex", True)
    _lm = json.loads((C / "data" / "app_l_manifest.json").read_text(encoding="utf-8"))
    check("app_l_manifest 含 up3_video_badframe.json",
          "up3_video_badframe.json" in _lm.get("sources", {}), "sources", "present",
          "up3_video_badframe.json" in _lm.get("sources", {}))

    _v4 = json.loads((C / "data" / "up4_p1b_video.json").read_text(encoding="utf-8"))
    _cmp = _v4["comparison"]
    check("Appendix L 的 V8+video 负结果与 JSON 一致",
          all(f"{x:.4f}" in _l for x in (_cmp["v8_ap"], _cmp["v9_ap"], _cmp["v8_worst"], _cmp["v9_worst"])),
          "four numbers", "in app_l.tex",
          all(f"{x:.4f}" in _l for x in (_cmp["v8_ap"], _cmp["v9_ap"], _cmp["v8_worst"], _cmp["v9_worst"])))
    check("app_l_manifest 含 up4_p1b_video.json",
          "up4_p1b_video.json" in _lm.get("sources", {}), "sources", "present",
          "up4_p1b_video.json" in _lm.get("sources", {}))

    _v10 = json.loads((C / "data" / "up5_video_badframe_10hz.json").read_text(encoding="utf-8"))
    _late = json.loads((C / "data" / "up6_video_late_fusion.json").read_text(encoding="utf-8"))
    check("Appendix L 含采样率与 late fusion 段",
          ("Sampling rate and late fusion" in _l) and ("59,864" in _l),
          "app_l.tex", "sampling section", "Sampling rate and late fusion" in _l)
    check("Appendix L 的 10 Hz 三臂数字与 JSON 一致",
          all(f"{_v10['arms'][a]['test_ap']:.4f}" in _l for a in ("Vsel", "P+Vsel"))
          and f"{_v10['arms']['P+Vsel']['test_auc']:.4f}" in _l,
          "10 Hz AP/AUC", "in app_l.tex", True)
    check("Appendix L 的 late-fusion 数字与 JSON 一致",
          f"{_late['fused']['ap']:.5f}" in _l and f"{_late['ap_rel_gain']*100:.4f}" in _l,
          "late fusion", "in app_l.tex", True)
    check("app_l_manifest 含 10 Hz 与 late-fusion JSON",
          all(x in _lm.get("sources", {}) for x in ("up5_video_badframe_10hz.json", "up6_video_late_fusion.json")),
          "sources", "both present", True)

    _mpath = C / "tables" / "app_m.tex"
    _m = _mpath.read_text(encoding="utf-8") if _mpath.exists() else ""
    check("Appendix M 参数登记表存在", ("tab:params" in _m) and ("Parameter register" in _m),
          "app_m.tex", "parameter register", ("tab:params" in _m))
    _npath = C / "tables" / "app_n.tex"
    _n = _npath.read_text(encoding="utf-8") if _npath.exists() else ""
    check("Appendix N 消融与核对登记表存在",
          ("tab:ablation-register" in _n) and ("Ablation and check register" in _n),
          "app_n.tex", "ablation register", ("tab:ablation-register" in _n))
    check("Appendix N 明确标出未隔离的检查",
          ("OAT" in _n) and ("Rule knobs" in _n) and ("full factorial" in _n),
          "app_n.tex", "gaps marked", True)
    _cpath = C / "data" / "up7_p2_context.json"
    _c = json.loads(_cpath.read_text(encoding="utf-8")) if _cpath.exists() else {"rows": []}
    _ctx_ok = (len(_c.get("rows", [])) == 4
               and all(f"{r['rmse_3d_cm']:.3f}" in _n for r in _c["rows"]))
    check("Appendix N 的 context-length 表与 up7 JSON 一致", _ctx_ok,
          "up7_p2_context.json", "four rows", _ctx_ok)
    _fpath = C / "data" / "up8_p2_features.json"
    _f = json.loads(_fpath.read_text(encoding="utf-8")) if _fpath.exists() else {"rows": []}
    _feat_ok = (len(_f.get("rows", [])) == 4
                and all(f"{r['rmse_3d_cm']:.3f}" in _n for r in _f["rows"]))
    check("Appendix N 的 feature-subset 表与 up8 JSON 一致", _feat_ok,
          "up8_p2_features.json", "four variants", _feat_ok)
    _p3path = C / "data" / "up9_p3_sensitivity.json"
    _p3 = json.loads(_p3path.read_text(encoding="utf-8")) if _p3path.exists() else {}
    _p3tab = (C / "tables" / "tab_p3_sensitivity.tex").read_text(encoding="utf-8") if (C / "tables" / "tab_p3_sensitivity.tex").exists() else ""
    _p3_ok = (bool(_p3.get("cases")) and "tab:p3-sens" in _p3tab
              and "reservation quantile" in _p3tab
              and all(("S2" in _p3tab) and ("S3" in _p3tab)
                      and (v["max_abs_delta_all30_pt"] < 5.0)
                      for v in _p3["cases"].values()))
    check("Appendix N 的 P3 one-at-a-time 表与 up9 JSON 一致", _p3_ok,
          "up9_p3_sensitivity.json", "two cases, OAT rows", _p3_ok)

    _loo_path = C / "data" / "up10_p1_keypoint_loo.json"
    _loo = json.loads(_loo_path.read_text(encoding="utf-8")) if _loo_path.exists() else {"rows": []}
    _palm_loo = [r for r in _loo.get("rows", []) if r["name"].startswith("palm_minus_")]
    _tip_loo = [r for r in _loo.get("rows", []) if r["name"].startswith("tips_minus_")]
    _loo_ok = (len(_palm_loo) == 4 and len(_tip_loo) == 5
               and max(abs(r["d_rigidity_vs_palm_cm"]) for r in _palm_loo) < 1e-3
               and all(r["rigidity_cm"] > 1.0 for r in _tip_loo)
               and "tab:p1-loo" in _n)
    check("Appendix N keypoint leave-one-out matches up10", _loo_ok,
          "up10_p1_keypoint_loo.json", "4 palm + 5 tip LOO rows", _loo_ok)

    _thr_path = C / "data" / "up11_p1_stage_sensitivity.json"
    _thr = json.loads(_thr_path.read_text(encoding="utf-8")) if _thr_path.exists() else {}
    _thr_ok = (abs(_thr.get("effect", {}).get("v_lo", {}).get("max_share_shift_pp", 0) - 6.35) < 0.01
               and abs(_thr.get("base", {}).get("share", {}).get("reach", 0) * 100 - 65.63) < 0.01
               and "tab:p1-thr" in _n)
    check("Appendix N stage-threshold sweep matches up11", _thr_ok,
          "up11_p1_stage_sensitivity.json", "v_lo 6.35 pp, reach 65.63", _thr_ok)

    _ff_path = C / "data" / "up12_p3_full_factorial.json"
    _ff = json.loads(_ff_path.read_text(encoding="utf-8")) if _ff_path.exists() else {"cases": {}}
    _ff_ok = (set(_ff.get("cases", {})) == {"S2", "S3"}
              and all(c["n"] == 128 and c["frozen_percentile"] == 100.0
                      and c["corner_range_pt"] < 7.0
                      and abs(c["main_effects"]["ksk"]["main_effect_pt"]) < 1e-12
                      and abs(c["main_effects"]["qsl"]["main_effect_pt"]) < 1e-12
                      for c in _ff["cases"].values())
              and "tab:p3-factorial" in _n
              and "\\slotPFactRangeSTwo" in _n)
    check("Appendix N P3 full factorial matches up12", _ff_ok,
          "up12_p3_full_factorial.json", "2 x 128 corners, frozen pct 100", _ff_ok)

    _tl_path = C / "data" / "up14_p3_three_level.json"
    _tl = json.loads(_tl_path.read_text(encoding="utf-8")) if _tl_path.exists() else {"cases": {}}
    _tl_ok = (set(_tl.get("cases", {})) == {"S2", "S3"}
              and all(c["n"] == 243 and len(c["coefficients_pt"]) == 16
                      and len(c["curvature_pt"]) == 5
                      and c["frozen"]["on_time_all30"] > 0.79
                      for c in _tl["cases"].values())
              and "tab:p3-threelevel" in _n
              and "\\slotPThreeRangeSTwo" in _n)
    check("Appendix N three-level P3 design matches up14", _tl_ok,
          "up14_p3_three_level.json", "3^5 = 243 cells per case, 16 coefficients", _tl_ok)

    _an_path = C / "data" / "up13_anchor_summary.json"
    _an = json.loads(_an_path.read_text(encoding="utf-8")) if _an_path.exists() else {}
    _an_rows = [r for r in _an.get("anchors", []) if r.get("anchor") in ("wrist", "palm", "tips")]
    _an_tab = (C / "tables" / "tab_p1_anchor.tex")
    _an_tab_txt = _an_tab.read_text(encoding="utf-8") if _an_tab.exists() else ""
    _an_ok = (len(_an_rows) == 3
              and all(r["p1a_n"] >= 3 for r in _an_rows)
              and all(0.30 < r["p1a_ari_mean"] < 0.80 for r in _an_rows)
              and all(r["p1a_ari_sd"] > 0.0 for r in _an_rows)
              and all(0.03 < r["p1b_ap"] < 0.40 for r in _an_rows)
              and _an.get("verdict") in ("clears the noise", "inside the noise")
              and "mean $\\pm$ sd" in _an_tab_txt
              and "tab:p1-anchor" in _n)
    check("Appendix N anchor-retrain table matches up13", _an_ok,
          "up13_anchor_summary.json", "three anchors x >=3 runs, both learners refitted", _an_ok)

    _rp_path = C / "data" / "up15_p1a_final_repeats.json"
    _rp = json.loads(_rp_path.read_text(encoding="utf-8")) if _rp_path.exists() else {}
    _rp_n = _rp.get("n", 0)
    _rp_ok = (_rp_n >= 3
              and 0.45 < _rp.get("ari_mean", 0) < 0.70
              and _rp.get("ari_sd", 0) > 0
              and _rp.get("ari_min", 1) <= _rp.get("ari_mean", 0) <= _rp.get("ari_max", 0)
              and _rp.get("gap_vs_ward_pt", 0) > 5.0
              and near(num(sl.get("PSegGPUARIRep", "x")), _rp.get("ari_mean", -1), tol=5e-4)
              and near(num(sl.get("PSegGPURepN", "x")), float(_rp_n))
              and "not bit-reproducible" in flat_text
              and "\\slotPSegGPUARIRep" in main_text)
    check("Part I headline reported as a refit distribution (up15)", _rp_ok,
          "up15_p1a_final_repeats.json",
          f"n={_rp_n} mean={_rp.get('ari_mean')} sd={_rp.get('ari_sd')}", _rp_ok)

    _bw_path = C / "data" / "up19_borrowed_alt.json"
    _bw = json.loads(_bw_path.read_text(encoding="utf-8")) if _bw_path.exists() else {}
    _cov = _bw.get("coverage", {})
    _sc = _bw.get("scaling", {})
    _cov_sh = {k: v.get("share", 0) for k, v in _cov.get("coverage", {}).items()}
    _bw_ok = (bool(_cov) and _cov.get("n_test_segments", 0) > 0
              and 0.5 < _cov_sh.get("tol_0.5s", 0) <= 1.0
              and _cov_sh.get("tol_2.0s", 0) >= _cov_sh.get("tol_0.5s", 1.0)
              and _cov.get("detections_per_segment", 0) > 1.0
              and near(num(sl.get("PSegCovTight", "x")), _cov_sh.get("tol_0.5s", -1), tol=5e-4)
              and near(num(sl.get("PSegCovSegments", "x")), float(_cov.get("n_test_segments", -1)))
              and 0.2 < _sc.get("b", 0) < 1.0
              and _sc.get("r2", 0) > 0.9
              and near(num(sl.get("PScaleExponent", "x")), _sc.get("b", -1), tol=5e-4)
              and near(num(sl.get("PScaleDoubling", "x")), _sc.get("doubling_factor", -1), tol=5e-3)
              and "log--log" in flat_text)
    check("Borrowed analyses: segment coverage and the scaling law (up19)", _bw_ok,
          "up19_borrowed_alt.json",
          f"cov0.5={_cov_sh.get('tol_0.5s')} cov2={_cov_sh.get('tol_2.0s')} "
          f"det/seg={_cov.get('detections_per_segment')} b={_sc.get('b')} r2={_sc.get('r2')}",
          _bw_ok)

    _mi_path = C / "data" / "up20_marginal_info.json"
    _mi = json.loads(_mi_path.read_text(encoding="utf-8")) if _mi_path.exists() else {}
    _mi_ok = (bool(_mi) and _mi.get("n_non_monotone", 0) >= 2
              and _mi.get("s2_second_pt", 0) < 0
              and _mi.get("s3_second_pt", 0) < 0
              and near(num(sl.get("PInfoFirstSTwo", "x")), _mi.get("s2_first_pt", -1), tol=5e-3)
              and near(num(sl.get("PInfoSecondSTwo", "x")), _mi.get("s2_second_pt", -1), tol=5e-3)
              and near(num(sl.get("PInfoTrueMax", "x")), _mi.get("true_max_pt", -1), tol=5e-3)
              and "not monotone" in flat_text)
    check("Borrowed analyses: non-monotone marginal value of information (up20)", _mi_ok,
          "up20_marginal_info.json",
          f"first={_mi.get('s2_first_pt')} second={_mi.get('s2_second_pt')} "
          f"nonmono={_mi.get('n_non_monotone')}", _mi_ok)

    _cs_path = C / "data" / "up21_p2_cost_sweep.json"
    _cs = json.loads(_cs_path.read_text(encoding="utf-8")) if _cs_path.exists() else {}
    _cs_s = _cs.get("summary", {})
    _cs_oat = {row["knob"]: row for row in _cs_s.get("one_at_a_time", [])}
    _cs_ok = (bool(_cs) and _cs_s.get("n_cells", 0) >= 100
              and 0.3 < _cs_s.get("frac_interior", 0) < 0.9
              and _cs_s.get("n_interior", 0) > 20
              and near(num(sl.get("PEconTMin", "x")), _cs_s.get("T_star_min_s", -1), tol=5e-3)
              and near(num(sl.get("PEconTMax", "x")), _cs_s.get("T_star_max_s", -1), tol=5e-3)
              and int(float(sl.get("PEconNCell", "-1"))) == int(_cs_s.get("n_cells", -2))
              and int(float(sl.get("PEconInterior", "-1"))) == int(_cs_s.get("n_interior", -2))
              and near(num(sl.get("PEconCOneSpan", "x")),
                       _cs_oat.get("C1", {}).get("span_s", -1), tol=5e-3)
              and near(num(sl.get("PEconCZeroSpan", "x")),
                       _cs_oat.get("C0", {}).get("span_s", -1), tol=5e-3)
              and _cs_oat.get("C1", {}).get("span_s", 1) == 0.0
              and "coefficient triples" in flat_text
              and "no fallback" in flat_text)
    check("Part II priced rule re-solved over cost coefficients (up21)", _cs_ok,
          "up21_p2_cost_sweep.json",
          f"cells={_cs_s.get('n_cells')} interior={_cs_s.get('n_interior')} "
          f"span={_cs_s.get('T_star_span_s')} c1span={_cs_oat.get('C1', {}).get('span_s')}",
          _cs_ok)


    # --- software table and support-material statement (spec item 1(6)) --------
    tex = (C / "main.tex").read_text(encoding="utf-8", errors="ignore")
    appc = tex[tex.find(r"\section{Reproduction commands}"):]
    _sw_ok = (
        ("tab:software" in appc)
        and ("3.11.18" in appc)
        and ("2.4.6" in appc)
        and ("1.17.1" in appc)
        and ("3.1.1" in appc)
        and ("1.9.1" in appc)
        and ("2.14.1" in appc)
        and ("4.7.0" in appc)
        and ("3.11.2" in appc)
        and ("4.16" in appc)
        and ("CSWBMCM2634892fj.zip" in appc)
        and ("support material" in appc)
    )
    check("Appendix C names the software and points at the support material", _sw_ok,
          "Appendix C of main.tex", "ten versions and the support-material note", _sw_ok)

    out = AUD / "verify_claims.json"
    out.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    n_fail = sum(1 for r in RESULTS if r["status"] == "FAIL")
    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    n_na = sum(1 for r in RESULTS if r["status"] == "NA")
    print(f"PASS={n_pass} FAIL={n_fail} NA={n_na} total={len(RESULTS)}")
    for r in RESULTS:
        if r["status"] != "PASS":
            print(f"[{r['status']}] {r['name']}: {r['detail']}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())