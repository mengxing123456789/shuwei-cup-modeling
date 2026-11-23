# AI 辅助：DeepSeek Harness 助手生成的补丁模板改写；每条替换断言命中一次。
# -*- coding: utf-8 -*-
"""Align verify_claims.py with the corrected claims.

Four of the old assertions encoded claims that were false (a "two units" count,
"above nominal" coverage, "three actions wait/review/execute", and an oracle
identity that conflated two different objects).  The paper now states the true
version; these checks are rewritten to test the true version, so they still fail
if the wording drifts back.
"""
from pathlib import Path

F = Path(r"E:\数学建模\_swc2026\audit\verify_claims.py")

OLD_ORACLE = '''    oracle2 = p3ad["upper_bound"]["S2"]["oracle"]
    oracle3 = p3ad["upper_bound"]["S3"]["oracle"]
    check(
        "P3 S2 oracle 口径统一",
        near(num(sl.get("PStochSTwoOracleETA", "x")), oracle2),
        f"slot={sl.get('PStochSTwoOracleETA')} p3_adaptive={oracle2:.6f}",
        oracle2,
        num(sl.get("PStochSTwoOracleETA", "x")),
    )
    check(
        "P3 S3 oracle 口径统一",
        near(num(sl.get("PStochSThreeOracleETA", "x")), oracle3),
        f"slot={sl.get('PStochSThreeOracleETA')} p3_adaptive={oracle3:.6f}",
        oracle3,
        num(sl.get("PStochSThreeOracleETA", "x")),
    )
'''

NEW_ORACLE = '''    # The paper's reference is "the same rule run with p known", so it must match the
    # simulator that produced every other Part III number -- not p3_adaptive's oracle,
    # which is a different rule with p known and therefore a different object.
    try:
        import numpy as np

        sys.path.insert(0, str(C / "code"))
        import p3_stochastic_schedule as p3sim_ref  # type: ignore

        ref_seeds = p3st["_meta"]["seeds"]
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
'''

OLD_ADV = '''    adv2_abs = num(sl.get("PInfoAdvSTwoAbs", "x"))
    adv3_abs = num(sl.get("PInfoAdvSThreeAbs", "x"))
    check(
        "PInfoAdvSTwoAbs 为正（正文说 ahead by）",
        adv2_abs is not None and adv2_abs > 0,
        f"slot={adv2_abs}; 若为负，正文 ahead by 负值语义反转",
        ">0",
        adv2_abs,
    )
    check(
        "PInfoAdvSThreeAbs 为正",
        adv3_abs is not None and adv3_abs > 0,
        f"slot={adv3_abs}",
        ">0",
        adv3_abs,
    )
'''

NEW_ADV = '''    # One definition only: PInfoAdvS* = adaptive - reference, positive when the
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
'''

OLD_COV = '''    cov = num(sl.get("PConMeanCoverage", "x"))
    check(
        "平均覆盖率实际 >= 0.90（论文称 slightly above nominal）",
        cov is not None and cov >= 0.90,
        f"slot={cov}; empirical mean={p2i['summary']['mean_coverage']:.4f}",
        0.90,
        cov,
    )
'''

NEW_COV = '''    cov = num(sl.get("PConMeanCoverage", "x"))
    _emp = p2i["summary"]["mean_coverage"]
    check(
        "平均覆盖率 slot 与 p2_interval 一致",
        cov is not None and near(cov, _emp, 1e-6),
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
'''

OLD_EQ = '''    check(
        "恰好 1.2 s 的单元数（论文说 two）",
        eq12 == 2,
        f"exact={eq12}, truly<1.2={lt12}, truly>1.2={gt12}, non-strict eligible={elig}",
        2,
        eq12,
    )
'''

NEW_EQ = '''    check(
        "恰好 1.2 s 的单元数（论文说 three）",
        eq12 == 3 and "three of them" in main_text,
        f"exact={eq12}, truly<1.2={lt12}, truly>1.2={gt12}, non-strict eligible={elig}",
        3,
        eq12,
    )
'''

OLD_ACT = '''    act = "three actions" in main_text
    check(
        "P3 动作集声明与代码一致（代码含 drop）",
        not act,
        "正文仍写 three actions wait/review/execute；best_p3_sens 有 drop",
        "absent",
        "present" if act else "absent",
    )
'''

NEW_ACT = '''    _act_ok = "wait, execute and drop" in main_text
    _act_bad = "wait, review, execute" in main_text
    check(
        "P3 动作集声明与代码一致（wait/execute/drop）",
        _act_ok and not _act_bad,
        f"correct_list={_act_ok} wrong_list={_act_bad}; best_p3_sens 有 drop",
        "wait, execute and drop",
        "ok" if (_act_ok and not _act_bad) else "mismatch",
    )
'''

OLD_CI = '''            check(
                f"P3 {case} adaptive-reference 配对差 CI 排除 0（正文称 ahead）",
                diff.mean() - half > 0,
                f"diff={diff.mean():+.4f} CI95=±{half:.4f} lower={diff.mean()-half:+.4f}",
                ">0",
                diff.mean(),
            )
'''

NEW_CI = '''            _lower = diff.mean() - half
            _claims = "ahead of the reference" in main_text or "goes past" in main_text
            check(
                f"P3 {case} adaptive-reference 表述与配对区间一致",
                not (_lower <= 0 and _claims) and (_lower > 0 or "includes zero" in main_text),
                f"diff={diff.mean():+.4f} CI95=±{half:.4f} lower={_lower:+.4f} "
                f"text_claims_ahead={_claims}",
                "consistent",
                "inconsistent" if (_lower <= 0 and _claims) else "consistent",
            )
'''

OLD_ID = '''        headline2 = num(sl.get("PImpSTwoAllCand", "x"))
        check(
            "headline adaptive 与 p3_adaptive_decomp final 是同一个策略",
            near(headline2, final_cells["S2"]["final_bayes"]),
            f"headline={headline2} decomp_final_S2={final_cells['S2']['final_bayes']:.4f}",
            final_cells["S2"]["final_bayes"],
            headline2,
        )
'''

NEW_ID = '''        headline2 = num(sl.get("PImpSTwoAllCand", "x"))
        sel2 = p3iv["cases"]["S2"]["selected"]["on_time_mean"]
        check(
            "headline adaptive 就是 p3_improved_verify 的选定策略",
            near(headline2, sel2, 1e-6),
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
'''

EDITS = [
    (OLD_ORACLE, NEW_ORACLE),
    (OLD_ADV, NEW_ADV),
    (OLD_COV, NEW_COV),
    (OLD_EQ, NEW_EQ),
    (OLD_ACT, NEW_ACT),
    (OLD_CI, NEW_CI),
    (OLD_ID, NEW_ID),
]


def main():
    t = F.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(EDITS, 1):
        n = t.count(old)
        assert n == 1, f"edit {i}: matched {n}, expected 1\n---\n{old[:160]}"
        t = t.replace(old, new, 1)
    assert "import sys" in t.split("def main")[0] or "import sys" in t, "needs sys import"
    F.write_text(t, encoding="utf-8", newline="\n")
    print(f"verify_claims.py: {len(EDITS)} blocks rewritten")


main()