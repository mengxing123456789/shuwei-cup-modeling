# AI 辅助：DeepSeek Harness 助手生成的一次性补丁，给 verify_claims.py 追加本轮新结论的断言。
# -*- coding: utf-8 -*-
"""把前置检查插到写 JSON 之前；插不进去就整体放弃，避免半截文件。"""
import pathlib
import sys

P = pathlib.Path(r"E:\数学建模\_swc2026\audit\verify_claims.py")
t = P.read_text(encoding="utf-8", errors="strict")

ANCHOR = '    out = AUD / "verify_claims.json"'
if t.count(ANCHOR) != 1:
    print("ANCHOR not unique", file=sys.stderr)
    raise SystemExit(1)

BLOCK = r'''    # ---------- P2 in the official action set (p2_frontier) ----------
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

'''

t = t.replace(ANCHOR, BLOCK + ANCHOR)
P.write_text(t, encoding="utf-8", newline="\n")
print("verify_claims.py extended with 4 blocks")