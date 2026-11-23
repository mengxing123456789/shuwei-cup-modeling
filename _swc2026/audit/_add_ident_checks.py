# AI 辅助：DeepSeek Harness 助手生成的一次性补丁：给 verify_claims 加可辨识性那一段的断言。
# -*- coding: utf-8 -*-
import pathlib

F = pathlib.Path(r"E:\数学建模\_swc2026\audit\verify_claims.py")
src = F.read_text(encoding="utf-8")
anchor = '    out = AUD / "verify_claims.json"'
assert src.count(anchor) == 1, "anchor missing"

block = '''    # ---------- P1-a identifiability: separation does not predict detection ----------
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
          "identifiable" not in main_text.split("We also test")[-1].split("\\\\section")[0].lower()
          or "not the distinguishability" in main_text,
          "null-check 句式存在: %s" % ("A null check rules out a blind detector" in main_text),
          "null-check 存在", None)
    check("零假设对照给出真边界高于随机帧", idn["auc_at_2_frames"] > 0.5 and idn["mean_pos_p2"] > idn["mean_neg_p2"],
          "AUC2=%.3f true=%.3f null=%.3f" % (idn["auc_at_2_frames"], idn["mean_pos_p2"], idn["mean_neg_p2"]),
          "AUC>0.5 且 true>null", None)

'''
src = src.replace(anchor, block + anchor, 1)
F.write_text(src, encoding="utf-8", newline="\n")
print("appended identifiability checks (8)")