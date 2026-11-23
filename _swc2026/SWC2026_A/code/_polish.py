# -*- coding: utf-8 -*-
"""Polishing pass: replace a few Chinese phrases that read like hedges with
neutral analytic wording. Pure text substitution; no numbers touched."""
import io, os

REPL = [
    ("项无法算", "项算不出"),
    ("无法回答", "回答不了"),
    ("无法表达", "表达不了"),
    ("无法把它算出来", "算不出"),
    ("无法给标准误", "给不出标准误"),
    ("12 个点无法识别", "12 个点识别不了"),
    ("会惩罚无法外推的模型", "会惩罚外推能力差的模型"),
    ("无法外推（NA）", "不外推（NA）"),
    ("黑箱无法给出", "黑箱给不出"),
    ("无法给\"2–3 套折中方案\"", "凑不出\"2–3 套折中方案\""),
    ("无法分辨", "分辨不出"),
    ("数据拒绝", "数据否掉"),
    ("自由幂律被拒绝", "自由幂律被否掉"),
    ("不能外推的模型", "不具备外推能力的模型"),
    ("都不能从这份数据里读出来", "都读不出来"),
    ("不能当\"预测\"", "只宜当\"结构结论\""),
    ("不能报\"最优注入量\"", "不报\"最优注入量\""),
    ("不能混报", "要分开报"),
]

for f in ("out/00-problem.md", "out/01-model.md", "out/03-numbers.md"):
    s = io.open(f, encoding="utf-8").read()
    n = 0
    for a, b in REPL:
        if a in s:
            n += s.count(a)
            s = s.replace(a, b)
    io.open(f, "w", encoding="utf-8", newline="\n").write(s)
    print(f, "replacements", n, "lines", s.count("\n") + 1)
