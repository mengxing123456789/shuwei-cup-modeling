# AI 辅助：DeepSeek Harness 助手生成的一次性排版补丁：把 pass-marks 表从正文移到附录。
# -*- coding: utf-8 -*-
"""正文顶到 25 页上限，附录不限。tab:pass（预注册判据与实测判定）是评分辅助表，
不是结果，移到 Appendix D 之后既保住 §7 的论证，又释放正文约 12 行。"""
import pathlib

F = pathlib.Path(__file__).resolve().parent.parent / "main.tex"
src = F.read_text(encoding="utf-8")

start = src.index("\\begin{table}[htbp]\n\\centering\n\\caption{Pre-declared pass marks")
end = src.index("\\end{table}", start) + len("\\end{table}\n")
block = src[start:end]
assert "\\label{tab:pass}" in block and block.count("\\begin{table}") == 1, "unexpected block"

src2 = src[:start] + src[end:]
assert src2.count("\\label{tab:pass}") == 0, "label still in body"

anchor = "\\section*{Appendix D: Closed-form calibration}"
assert src2.count(anchor) == 1, "appendix D anchor"
i = src2.index(anchor) + len(anchor)
# 插到 Appendix D 标题之后、其正文之前
src2 = src2[:i] + "\n\n" + block.rstrip("\n") + "\n" + src2[i:]

F.write_text(src2, encoding="utf-8", newline="\n")
print("moved tab:pass (%d chars) from body to Appendix D" % len(block))
print("body label present:", "\\label{tab:pass}" in src2)