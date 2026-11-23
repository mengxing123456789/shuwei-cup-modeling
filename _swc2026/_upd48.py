# -*- coding: utf-8 -*-
"""Rewrite 48-report sections 5.3-5.5 from the measured benchmark json."""
import io, json, os

ROOT = r"E:\数学建模\_swc2026"
P = os.path.join(ROOT, "48-官网通知逐条核对与AIGC风险.md")
B = json.loads(io.open(os.path.join(ROOT, "_aigc_bench.json"), encoding="utf-8").read())
ORD = json.loads(io.open(os.path.join(ROOT, "_ord_split.json"), encoding="utf-8").read())

ours = B["ours"]
humans = [v for k, v in B.items() if k != "ours"]

KEYS = [
    ("em dash", "破折号"),
    ("semicolon", "分号 `;`"),
    ("rather than", "`rather than`"),
    ("not X but Y", "`not X but Y`"),
    ("the fact that", "`the fact that`"),
    ("it is worth noting", "`it is worth noting`"),
    ("crucially/importantly", "`crucially/importantly`"),
    ("therefore/thus/hence", "`therefore/thus/hence`"),
    ("however/moreover/furthermore", "`however/moreover/furthermore`"),
    ("first/second/third", "`first/second/third`"),
    ("triple comma list", "三项并列"),
    ("sent_cv", "句长变异系数 CV"),
    ("sent_mean", "平均句长（词）"),
]

lines = []
lines.append("### 5.3 代理指标：与 5 篇同赛 C 题获奖论文同口径对照（改写后实测）")
lines.append("")
lines.append(
    "方法：把本稿 LaTeX 剥成纯散文（**%d 词**），与 `AsterLink\\2025年数维杯秋季赛优秀论文.zip` "
    "中 5 篇 C 题获奖稿（%s 词）用同一组正则统计，单位「每千词」。"
    % (ours["words"], "–".join(str(int(h["words"])) for h in sorted(humans, key=lambda x: x["words"])))
)
lines.append("")
lines.append("| 文风标记 | 本稿 | 获奖均值 | 获奖最大 | 判定 |")
lines.append("|---|---:|---:|---:|---|")
for key, name in KEYS:
    o = ours[key]
    vals = [h[key] for h in humans]
    mean = sum(vals) / len(vals)
    mx = max(vals)
    if key in ("sent_cv", "sent_mean"):
        verdict = "within" if mx * 0.25 <= o <= mx else ("偏均匀" if o < mean else "above mean")
    elif key == "em dash":
        verdict = "within" if o <= mx else "超上限"
    elif o <= mx:
        verdict = "**within**" if key in ("semicolon", "rather than", "not X but Y", "therefore/thus/hence", "first/second/third") else "within"
    else:
        verdict = "**超上限 %.2f 倍**" % (o / mx if mx else float("inf"))
    lines.append("| %s | %.3f | %.3f | %.3f | %s |" % (name, o, mean, mx, verdict))
lines.append("")
lines.append(
    "`first/second/third` 的 %.3f 是**原始计数**，其中时间单位占 %.3f/千词、名词序数占 %.3f/千词、"
    "**话语序数（First,/Second,/Third,）为 %.3f**（已清零）。原始数据：`_aigc_bench.json`、`code/_ord_split.json`。"
    % (ours["first/second/third"], ORD["time-unit"]["per_1k"], ORD["ordinal-noun"]["per_1k"], ORD["discourse"]["per_1k"])
)
lines.append("")
lines.append("### 5.4 判断")
lines.append("")
lines.append(
    "- 改写前 `rather than` 为 4.076/千词（超人类上限 45 倍），是**唯一真正像 AI 的一条**；"
    "现已清零（41 处全部改为 `, not` / `instead of` / 正面陈述 / 拆句）。"
)
lines.append(
    "- 分号由 4.381 降到 %.3f（%d 处），落在人类均值与上限之间；`not X but Y` 与 "
    "`therefore/thus/hence` 双双清零。"
    % (ours["semicolon"], round(ours["semicolon"] * ours["words"] / 1000))
)
lines.append(
    "- `the fact that` / `it is worth noting` / `crucially` 一次都没用，这是加分项；破折号 %.3f 仍高于均值但在上限内。"
    % ours["em dash"]
)
lines.append(
    "- 句长 CV %.3f（人类 1.197–2.161）：本稿句子明显更均匀，但按该技能规定**不为节奏人为造参差**，只报告不动手。"
    % ours["sent_cv"]
)
lines.append("- **本地任何数字都不是组委会的 AIGC 百分比**，它只能说明「在可测的文风指纹上已回到人类区间」。")
lines.append("")
lines.append("### 5.5 处置结果（A/B/C 已执行，D 不动，E 待你操作）")
lines.append("")
lines.append("| 优先级 | 动作 | 结果 |")
lines.append("|---|---|---|")
lines.append("| A | 41 处 `rather than` 改写 | **4.076 → 0.000**，全部清除 |")
lines.append("| B | 句内分号拆句（69 → 16 处） | **4.381 → %.3f**，回到人类上限内 |" % ours["semicolon"])
lines.append("| C | 话语序数 `First,/Second,/Third,` 清零、名词序数减量 | 话语序数 **0**；原始计数 %.3f（时间单位占大头） |" % ours["first/second/third"])
lines.append("| D | 句长 CV | **不动**（人为参差比不改更糟） |")
lines.append("| E | 提交前用组委会认可渠道自测 | **需你操作**，这是拿到真实百分比的唯一途径 |")
lines.append("")
lines.append(
    "副作用与代价：三处改写曾把正文推到 26 页，已通过压缩两处句子（`so we fix one convention`、"
    "`prefix of the source recording: \\slotPrefixFree{} s are free`）与一处语义去重"
    "（`That flatness is what empties the information channel.`）把正文压回 **25 页**。"
)
lines.append("")

new53 = "\n".join(lines)
text = io.open(P, encoding="utf-8").read()
i = text.find("### 5.3")
j = text.find("## 6.")
assert i > 0 and j > i, (i, j)
out = text[:i] + new53 + "\n---\n\n" + text[j:]
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("rewrote 5.3-5.5:", len(text), "->", len(out))
